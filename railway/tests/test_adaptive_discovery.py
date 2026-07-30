from __future__ import annotations

import asyncio
from collections import deque
from datetime import datetime, timezone

from railway.app.adaptive_discovery import (
    AdaptiveContestDiscovery,
    _distinctive_known_titles,
)
from railway.app.models import (
    ContestAnalysis,
    DiscoveryItem,
    DiscoveryRequest,
    DiscoveryResponse,
    ScoreBreakdown,
)
from railway.app.settings import Settings


def _item(url: str, score: int, ev: int) -> DiscoveryItem:
    now = datetime.now(timezone.utc).isoformat()
    return DiscoveryItem(
        slug=url.rsplit("/", 1)[-1] or "contest",
        title=f"Contest {score}",
        organizer="Example",
        prize="Two tickets",
        url=url,
        locality="Berlin",
        eligibility="Adult residents of Germany",
        entry_method="Online form",
        analysis=ContestAnalysis(
            contest_id=score,
            score=score,
            status="READY",
            verdict="Enter",
            competition="Medium",
            confidence="Medium",
            entrants_low=100,
            entrants_likely=500,
            entrants_high=2000,
            chance_low_ppm=500,
            chance_likely_ppm=2000,
            chance_high_ppm=10_000,
            crowd="Medium",
            prize_delivery="location_bound",
            prize_value_eur=80,
            entry_cadence="once",
            entries_before_deadline=1,
            effective_chance_ppm=2000,
            ev_cents_per_minute=ev,
            friction_minutes=1,
            registration_required=False,
            newsletter_required=False,
            deadline="2026-09-01",
            winners=1,
            summary="Verified test contest",
            reasons=["Live form", "Free entry"],
            evidence_urls=[url],
            verification="Test fixture",
            score_breakdown=ScoreBreakdown(
                chance=50,
                prize=70,
                friction=90,
                legitimacy=90,
                locality=100,
                urgency=40,
            ),
            analyzed_at=now,
        ),
    )


def _response(items: list[DiscoveryItem], searched: int = 4) -> DiscoveryResponse:
    return DiscoveryResponse(
        discoveries=items,
        searched_queries=searched,
        raw_candidates=searched * 5,
        novel_candidates=searched * 2,
        analyzed_candidates=searched,
        rejected_candidates=searched,
        search_errors=0,
        round=0,
        model="fake",
        analyzed_at=datetime.now(timezone.utc).isoformat(),
    )


class FakeEngine:
    def __init__(self, settings: Settings, queue: deque[DiscoveryResponse], calls: list):
        self.settings = settings
        self.queue = queue
        self.calls = calls

    async def discover(self, request: DiscoveryRequest) -> DiscoveryResponse:
        self.calls.append((self.settings, request))
        return self.queue.popleft()


def _settings() -> Settings:
    return Settings(
        GEMINI_API_KEY="x",
        TAVILY_API_KEY="x",
        ADAPTIVE_TARGET_RESULTS=3,
        ADAPTIVE_MAX_PASSES=3,
        ADAPTIVE_QUERIES_PER_PASS=4,
    )


def test_adaptive_discovery_runs_more_than_one_wave_and_merges_by_best_value():
    calls: list = []
    queue = deque(
        [
            _response([_item("https://example.com/a", 60, 30)]),
            _response(
                [
                    _item("https://example.com/a", 75, 50),
                    _item("https://example.com/b", 65, 40),
                    _item("https://example.com/c", 55, 20),
                ]
            ),
        ]
    )

    def factory(settings: Settings):
        return FakeEngine(settings, queue, calls)

    engine = AdaptiveContestDiscovery(
        _settings(), planner_client=object(), discovery_factory=factory
    )
    request = DiscoveryRequest(
        queries=[
            "query one",
            "query two",
            "query three",
            "query four",
            "query five",
            "query six",
        ],
        limit=5,
    )
    result = asyncio.run(engine.discover(request))

    assert len(calls) == 2
    assert [str(item.url) for item in result.discoveries] == [
        "https://example.com/a",
        "https://example.com/b",
        "https://example.com/c",
    ]
    assert result.discoveries[0].analysis.score == 75
    assert result.searched_queries == 8
    assert calls[1][0].DISCOVERY_MIN_SCORE <= 35
    assert calls[1][0].DISCOVERY_TIME_RANGE == "year"


def test_adaptive_discovery_stops_when_target_is_filled():
    calls: list = []
    queue = deque(
        [
            _response(
                [
                    _item("https://example.com/a", 80, 80),
                    _item("https://example.com/b", 70, 70),
                    _item("https://example.com/c", 60, 60),
                ]
            ),
            _response([_item("https://example.com/d", 50, 50)]),
        ]
    )

    def factory(settings: Settings):
        return FakeEngine(settings, queue, calls)

    engine = AdaptiveContestDiscovery(
        _settings(), planner_client=object(), discovery_factory=factory
    )
    request = DiscoveryRequest(
        queries=[
            "query one",
            "query two",
            "query three",
            "query four",
            "query five",
            "query six",
            "query seven",
            "query eight",
        ],
        limit=10,
    )
    result = asyncio.run(engine.discover(request))

    assert len(result.discoveries) == 3
    assert len(calls) == 1


def test_generic_known_titles_do_not_poison_title_deduplication():
    kept = _distinctive_known_titles(
        [
            "Berlin Gewinnspiel Tickets",
            "Gewinnspiel",
            "Museum Island Night with FlixTrain",
            "Spider-Man Brand New Day fan pack",
        ]
    )
    assert "Berlin Gewinnspiel Tickets" not in kept
    assert "Gewinnspiel" not in kept
    assert "Museum Island Night with FlixTrain" in kept
    assert "Spider-Man Brand New Day fan pack" in kept
