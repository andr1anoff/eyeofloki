"""Free-text hunting.

The user types what they actually want ("mechanical keyboard, something
that arrives by post"). Gemini turns that into search queries in the right
languages, and the existing discovery pipeline verifies whatever comes back.

Two passes: the literal reading first, then adjacent categories only if the
literal one came up short. Adjacent queries are not a consolation prize --
for shipped goods the category boundary is arbitrary, and a giveaway for
headphones is a fine answer to someone who asked for a keyboard.
"""

import json
from typing import Any

from google import genai

from .discovery import ContestDiscovery
from .models import (
    DiscoveryRequest,
    DiscoveryResponse,
    HuntPlan,
    HuntRequest,
)
from .settings import Settings


HUNT_PROMPT = """
Turn the user's brief into web search queries that find individual prize
competition pages, not listings.

Rules:
- Write queries a search engine will match against the contest page itself.
  Use the wording those pages use: German "Gewinnspiel", "Verlosung",
  "Einsendeschluss", "Teilnahmeschluss", "ohne Kauf"; English "giveaway",
  "free entry", "no purchase", "enter to win", "deadline".
- Mix German and English, weighted by prize type. For anything that arrives
  by post or download, most of the supply is English-language and EU- or
  worldwide-open, so lead with English and include the phrasings those pages
  use: "open to EU residents", "ships worldwide", "international giveaway",
  "no purchase necessary". Keep German for prizes tied to a German-speaking
  venue or audience.
- Do not translate a query into other EU languages. National contests in
  French, Dutch, Polish or Spanish almost always restrict entry to their own
  residents, so they cost a verification call and return nothing.
- direct_queries: the literal reading of the brief.
- adjacent_queries: neighbouring prize categories the user would plausibly
  still be happy to win, and broader phrasings of the same want. These run
  only if the literal search comes up short.
- If the brief implies a prize that arrives by post, do not add a city or
  country to the query beyond a shipping constraint. Geography only belongs
  in queries for prizes the winner must attend in person.
- No site: operators unless the user named a site. No quotes around whole
  sentences. Three to eight words per query.
- interpretation: one plain sentence on how you read the brief.

Return nothing but the JSON object.
""".strip()


class ContestHunter:
    def __init__(
        self,
        settings: Settings,
        genai_client: Any | None = None,
        discovery: ContestDiscovery | None = None,
    ) -> None:
        self.settings = settings
        self.client = genai_client or genai.Client(
            api_key=settings.GEMINI_API_KEY
        )
        self.discovery = discovery or ContestDiscovery(settings)

    async def plan(self, brief: str, profile: Any) -> HuntPlan:
        payload = {
            "brief": brief,
            "ships_to": profile.ships_to,
            "reachable_for_events": profile.reachable_for_events,
            "avoid_prizes": profile.avoid_prizes,
        }
        response = await self.client.aio.models.generate_content(
            model=self.settings.GEMINI_MODEL,
            contents=json.dumps(payload, ensure_ascii=False),
            config={
                "system_instruction": HUNT_PROMPT,
                "thinking_config": {
                    "thinking_level": self.settings.GEMINI_THINKING_LEVEL
                },
                "response_mime_type": "application/json",
                "response_json_schema": HuntPlan.model_json_schema(),
            },
        )
        return HuntPlan.model_validate_json(response.text)

    async def hunt(self, request: HuntRequest) -> tuple[DiscoveryResponse, HuntPlan]:
        plan = await self.plan(request.brief, request.profile)

        def run(queries: list[str]) -> DiscoveryRequest:
            return DiscoveryRequest(
                known_urls=request.known_urls,
                known_titles=request.known_titles,
                limit=request.limit,
                queries=queries[: self.settings.DISCOVERY_QUERIES_PER_RUN],
                profile=request.profile,
            )

        result = await self.discovery.discover(run(plan.direct_queries))

        # Widen only when the literal reading did not fill the queue.
        if len(result.discoveries) < max(1, request.limit // 3):
            seen = {str(item.url) for item in result.discoveries}
            widened = await self.discovery.discover(
                run(plan.adjacent_queries)
            )
            merged = result.discoveries + [
                item
                for item in widened.discoveries
                if str(item.url) not in seen
            ]
            merged.sort(key=lambda item: item.analysis.score, reverse=True)
            result = result.model_copy(
                update={
                    "discoveries": merged[: request.limit],
                    "searched_queries": result.searched_queries
                    + widened.searched_queries,
                    "raw_candidates": result.raw_candidates
                    + widened.raw_candidates,
                    "analyzed_candidates": result.analyzed_candidates
                    + widened.analyzed_candidates,
                    "rejected_candidates": result.rejected_candidates
                    + widened.rejected_candidates,
                    "rejections": result.rejections + widened.rejections,
                    "search_errors": result.search_errors
                    + widened.search_errors,
                }
            )
        return result, plan
