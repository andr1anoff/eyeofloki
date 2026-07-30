"""Adaptive, multi-pass contest discovery.

The original discovery engine is deliberately conservative and works well as a
validator, but a single pass through eight queries and eighteen candidates is a
poor web crawler. This module keeps that validator and adds the missing search
strategy around it:

* Gemini plans several genuinely different search lanes from the user profile;
* the lanes run in waves, so a weak first page does not end the search;
* later waves widen recency and ranking thresholds while keeping the hard legal
  and eligibility checks in :mod:`app.discovery`;
* results are de-duplicated and ranked across all waves.

The endpoint remains stateless. The browser's known URL history is the frontier
memory, so deployments do not need a database just to stop rediscovering the
same competitions.
"""

from __future__ import annotations

import json
import re
from datetime import date, datetime, timezone
from typing import Any, Callable

from google import genai
from pydantic import Field

from .discovery import ContestDiscovery, discovery_queries, normalize_url
from .models import (
    DiscoveryItem,
    DiscoveryRequest,
    DiscoveryResponse,
    RejectionNote,
    StrictModel,
)
from .settings import Settings


QUERY_PLANNER_PROMPT = """
You are planning web searches for an intelligence system that finds active,
free prize competitions for one adult living in Berlin, Germany.

The validator is strict. Your job is recall: create search queries that expose
many different direct contest pages for the validator to inspect.

Build three waves:
1. precision: current direct-entry pages from Berlin venues, cinemas, radio,
   publishers, promoters and cultural institutions;
2. product: shipped or digital prizes open to Germany or the EU, where Berlin
   is irrelevant;
3. frontier: source-specific searches, fresh wording and less obvious niches
   that are unlikely to repeat the user's existing history.

Rules:
- Search for the page where the entry happens, not a giveaway directory.
- Mix German and English. Use page-language phrases such as Gewinnspiel,
  Verlosung, wir verlosen, Einsendeschluss, Teilnahmeschluss, Gästeliste,
  giveaway, enter to win, free entry, open to EU residents and ships to Germany.
- Use site: operators selectively for organisers likely to run their own draws.
- Diversify across music, cinema, museums, theatre, books, games, useful tech,
  travel and local experiences. Do not spend half the plan on one category.
- Add the current month or year where it helps freshness, but do not make every
  query date-dependent: an active page may have been indexed earlier.
- Do not use generic directory queries such as "best Gewinnspiele" or
  "Gewinnspiel Liste".
- Do not repeat a query with cosmetic wording changes.
- Each query should be concise enough for a search engine, normally 4-12 words.
- Return 3-6 queries per wave and nothing outside the JSON schema.
""".strip()


class PlannedWave(StrictModel):
    name: str = Field(min_length=2, max_length=40)
    queries: list[str] = Field(min_length=3, max_length=6)


class DiscoveryPlan(StrictModel):
    rationale: str = Field(min_length=3, max_length=280)
    waves: list[PlannedWave] = Field(min_length=2, max_length=3)


_GENERIC_TITLE_WORDS = {
    "berlin",
    "deutschland",
    "gewinnspiel",
    "gewinnspiele",
    "verlosung",
    "verlosen",
    "gewinnen",
    "giveaway",
    "contest",
    "competition",
    "tickets",
    "ticket",
    "freikarten",
    "preise",
    "preis",
    "win",
}


def _distinctive_known_titles(titles: list[str]) -> list[str]:
    """Keep title de-duplication useful without letting generic titles erase
    whole categories of search results.

    The legacy matcher intentionally uses substring matching. Passing it a title
    such as "Berlin Gewinnspiel Tickets" can therefore hide unrelated contests.
    URLs remain the primary duplicate key; only titles with at least two
    distinctive tokens are forwarded.
    """

    kept: list[str] = []
    for title in titles:
        tokens = re.findall(r"[a-z0-9]+", title.lower())
        distinctive = [token for token in tokens if token not in _GENERIC_TITLE_WORDS]
        if len(distinctive) >= 2 and len(title.strip()) >= 18:
            kept.append(title)
    return kept[-400:]


def _clean_queries(values: list[str]) -> list[str]:
    seen: set[str] = set()
    clean: list[str] = []
    for value in values:
        query = " ".join(str(value).replace("\n", " ").split()).strip()
        if not 3 <= len(query) <= 220:
            continue
        fingerprint = query.casefold()
        if fingerprint in seen:
            continue
        seen.add(fingerprint)
        clean.append(query)
    return clean


def _fallback_waves(request: DiscoveryRequest) -> list[list[str]]:
    """Deterministic plan used when the planning model is unavailable."""

    today = date.today()
    month = today.strftime("%B")
    year = today.year
    generated = discovery_queries(request.round, 10, today=today)
    precision = _clean_queries(
        [
            f'"wir verlosen" Berlin Tickets {year}',
            f'"Einsendeschluss" Berlin Verlosung {year}',
            "Berlin Kino Vorpremiere Freikarten Gewinnspielfrage",
            "Berlin Konzert Gästeliste Verlosung Teilnahme",
            "site:radioeins.de OR site:fluxfm.de Verlosung",
        ]
        + generated[:2]
    )
    product = _clean_queries(
        [
            "giveaway open to EU residents electronics free entry",
            "win headphones ships to Germany no purchase",
            "Germany Gewinnspiel Technik Versand Teilnahmeschluss",
            "Europe giveaway game key subscription free entry",
            "Deutschland Buch Spiele Fanpaket Verlosung ohne Kauf",
        ]
        + generated[2:5]
    )
    frontier = _clean_queries(
        [
            f'"unter allen Einsendungen" Berlin {month} {year}',
            "site:tip-berlin.de Verlosung Tickets",
            "site:yorck.de Gewinnspiel Freikarten",
            "Berlin Museum Ausstellung Eröffnung Verlosung",
            "Berlin Theater Comedy Lesung Karten gewinnen",
        ]
        + generated[5:]
    )
    return [precision[:6], product[:6], frontier[:6]]


def _rank_key(item: DiscoveryItem) -> tuple[int, int, int]:
    analysis = item.analysis
    return (
        int(analysis.ev_cents_per_minute),
        int(analysis.score),
        int(analysis.effective_chance_ppm or analysis.chance_likely_ppm),
    )


def _merge_discoveries(
    current: dict[str, DiscoveryItem], incoming: list[DiscoveryItem]
) -> None:
    for item in incoming:
        key = normalize_url(str(item.url))
        existing = current.get(key)
        if existing is None or _rank_key(item) > _rank_key(existing):
            current[key] = item


def _dedupe_rejections(values: list[RejectionNote]) -> list[RejectionNote]:
    seen: set[tuple[str, str]] = set()
    result: list[RejectionNote] = []
    for item in values:
        key = (normalize_url(item.url), item.reason)
        if key in seen:
            continue
        seen.add(key)
        result.append(item)
    return result[:200]


DiscoveryFactory = Callable[[Settings], ContestDiscovery]


class AdaptiveContestDiscovery:
    """Search planner and recall controller around :class:`ContestDiscovery`."""

    def __init__(
        self,
        settings: Settings,
        *,
        planner_client: Any | None = None,
        discovery_factory: DiscoveryFactory = ContestDiscovery,
    ) -> None:
        if not settings.GEMINI_API_KEY:
            raise RuntimeError("GEMINI_API_KEY is not configured")
        if not settings.TAVILY_API_KEY:
            raise RuntimeError("TAVILY_API_KEY is not configured")
        self.settings = settings
        self.client = planner_client or genai.Client(api_key=settings.GEMINI_API_KEY)
        self.discovery_factory = discovery_factory

    async def _plan(self, request: DiscoveryRequest) -> list[list[str]]:
        if request.queries:
            clean = _clean_queries(request.queries)
            width = max(3, min(self.settings.ADAPTIVE_QUERIES_PER_PASS, 8))
            return [clean[index : index + width] for index in range(0, len(clean), width)]

        payload = {
            "today": date.today().isoformat(),
            "round": request.round,
            "requested_results": request.limit,
            "profile": request.profile.model_dump(mode="json"),
            "recent_known_titles": request.known_titles[-35:],
            "seed_queries": discovery_queries(request.round, 10),
        }
        try:
            response = await self.client.aio.models.generate_content(
                model=self.settings.GEMINI_MODEL,
                contents=json.dumps(payload, ensure_ascii=False),
                config={
                    "system_instruction": QUERY_PLANNER_PROMPT,
                    "thinking_config": {
                        "thinking_level": self.settings.GEMINI_THINKING_LEVEL
                    },
                    "response_mime_type": "application/json",
                    "response_json_schema": DiscoveryPlan.model_json_schema(),
                },
            )
            if not response.text:
                raise RuntimeError("empty query plan")
            plan = DiscoveryPlan.model_validate_json(response.text)
            waves = [_clean_queries(wave.queries) for wave in plan.waves]
            waves = [wave for wave in waves if wave]
            if len(waves) < 2:
                raise RuntimeError("query plan did not contain enough waves")
            return waves
        except Exception:
            # Discovery should degrade to deterministic search, not fail because
            # the inexpensive planning call was malformed or rate-limited.
            return _fallback_waves(request)

    def _pass_settings(self, index: int) -> Settings:
        """Widen ranking thresholds and recency only after a precise pass.

        Hard requirements such as free entry, live mechanism, Germany eligibility,
        deadline and legitimacy stay enforced inside the validator in every pass.
        """

        profiles = (
            {
                "DISCOVERY_MIN_SCORE": self.settings.DISCOVERY_MIN_SCORE,
                "DISCOVERY_MIN_CHANCE_PPM": self.settings.DISCOVERY_MIN_CHANCE_PPM,
                "DISCOVERY_TIME_RANGE": self.settings.DISCOVERY_TIME_RANGE,
            },
            {
                "DISCOVERY_MIN_SCORE": min(self.settings.DISCOVERY_MIN_SCORE, 35),
                "DISCOVERY_MIN_CHANCE_PPM": min(
                    self.settings.DISCOVERY_MIN_CHANCE_PPM, 80
                ),
                "DISCOVERY_TIME_RANGE": "year",
            },
            {
                "DISCOVERY_MIN_SCORE": min(self.settings.DISCOVERY_MIN_SCORE, 25),
                "DISCOVERY_MIN_CHANCE_PPM": min(
                    self.settings.DISCOVERY_MIN_CHANCE_PPM, 10
                ),
                "DISCOVERY_TIME_RANGE": "",
            },
        )
        profile = profiles[min(index, len(profiles) - 1)]
        return self.settings.model_copy(
            update={
                **profile,
                "MAX_DISCOVERY_CANDIDATES": max(
                    self.settings.MAX_DISCOVERY_CANDIDATES, 24
                ),
            }
        )

    async def discover(self, request: DiscoveryRequest) -> DiscoveryResponse:
        waves = await self._plan(request)
        max_passes = max(1, min(self.settings.ADAPTIVE_MAX_PASSES, len(waves), 3))
        target = min(request.limit, max(1, self.settings.ADAPTIVE_TARGET_RESULTS))

        known_urls = [str(url) for url in request.known_urls]
        known_titles = _distinctive_known_titles(request.known_titles)
        merged: dict[str, DiscoveryItem] = {}
        rejections: list[RejectionNote] = []
        totals = {
            "searched_queries": 0,
            "raw_candidates": 0,
            "novel_candidates": 0,
            "analyzed_candidates": 0,
            "rejected_candidates": 0,
            "truncated_candidates": 0,
            "search_errors": 0,
        }
        completed = 0
        last_error: Exception | None = None
        analyzed_at = datetime.now(timezone.utc).isoformat()

        for index, queries in enumerate(waves[:max_passes]):
            if not queries:
                continue
            pass_request = request.model_copy(
                update={
                    "known_urls": known_urls,
                    "known_titles": known_titles,
                    "queries": queries[: self.settings.ADAPTIVE_QUERIES_PER_PASS],
                    "limit": request.limit,
                }
            )
            engine = self.discovery_factory(self._pass_settings(index))
            try:
                result = await engine.discover(pass_request)
            except Exception as exc:
                last_error = exc
                continue

            completed += 1
            analyzed_at = result.analyzed_at
            _merge_discoveries(merged, result.discoveries)
            known_urls.extend(str(item.url) for item in result.discoveries)
            known_titles.extend(item.title for item in result.discoveries)
            rejections.extend(result.rejections)
            for key in totals:
                totals[key] += int(getattr(result, key))

            if len(merged) >= target:
                break

        if completed == 0 and last_error is not None:
            raise last_error

        discoveries = sorted(merged.values(), key=_rank_key, reverse=True)
        extra = max(0, len(discoveries) - request.limit)
        discoveries = discoveries[: request.limit]
        totals["truncated_candidates"] += extra
        unique_rejections = _dedupe_rejections(rejections)

        return DiscoveryResponse(
            discoveries=discoveries,
            searched_queries=totals["searched_queries"],
            raw_candidates=totals["raw_candidates"],
            novel_candidates=totals["novel_candidates"],
            analyzed_candidates=totals["analyzed_candidates"],
            rejected_candidates=totals["rejected_candidates"],
            truncated_candidates=totals["truncated_candidates"],
            rejections=unique_rejections,
            search_errors=totals["search_errors"],
            round=request.round,
            model=self.settings.GEMINI_MODEL,
            analyzed_at=analyzed_at,
        )
