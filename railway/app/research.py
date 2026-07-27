import json

from openai import AsyncOpenAI

from .models import (
    AssessmentBundle,
    ContestInput,
    ModelAssessment,
    PageEvidence,
    UserProfile,
)
from .settings import Settings


SYSTEM_PROMPT = """
Role: contest intelligence analyst for one adult user in Berlin, Germany.

Goal: verify whether each contest is currently enterable and estimate a
defensible range for the number of valid entries it will receive.

Success criteria:
- prefer the organizer's current contest page and official rules
- use web search when page evidence is incomplete or stale
- distinguish a rules page from a working entry mechanism
- correct the deadline and winner count when evidence supports it
- estimate entrants_low, entrants_likely, and entrants_high from organizer
  reach, geographic restriction, prize appeal, entry friction, number of
  winners, account/newsletter requirements, and likely promotion channels
- return sources supporting factual claims
- label uncertainty honestly; never imply the entrant estimate is known

Constraints:
- legal, free-entry contests only
- no evasion, multiple accounts, fake identities, automated submission, or
  rule-breaking tactics
- do not invent exact participant counts
- if no live entry mechanism can be found, mark active=false or
  entry_mechanism_found=false and explain the blocker
- keep summary concise and reasons concrete

The deterministic application, not you, calculates probability and Loki Score.
Your job is evidence gathering and calibrated inputs.
""".strip()


class OpenAIContestAnalyst:
    def __init__(self, settings: Settings):
        if not settings.OPENAI_API_KEY:
            raise RuntimeError("OPENAI_API_KEY is not configured")
        self.settings = settings
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

    async def analyze(
        self,
        contests: list[ContestInput],
        pages: list[PageEvidence],
        profile: UserProfile,
    ) -> list[ModelAssessment]:
        compact_pages = [
            {
                "contest_id": page.contest_id,
                "final_url": page.final_url,
                "status_code": page.status_code,
                "reachable": page.reachable,
                "title": page.title,
                "entry_signals": page.entry_signals,
                "registration_signals": page.registration_signals,
                "excerpt": page.excerpt,
            }
            for page in pages
        ]
        payload = {
            "user_profile": profile.model_dump(mode="json"),
            "contests": [
                contest.model_dump(mode="json") for contest in contests
            ],
            "direct_page_evidence": compact_pages,
        }

        response = await self.client.responses.create(
            model=self.settings.OPENAI_MODEL,
            reasoning={"effort": self.settings.OPENAI_REASONING_EFFORT},
            tools=[{"type": "web_search"}],
            input=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": (
                        "Analyze every contest in this JSON payload. Return one "
                        "assessment per contest_id.\n\n"
                        + json.dumps(payload, ensure_ascii=False)
                    ),
                },
            ],
            text={
                "format": {
                    "type": "json_schema",
                    "name": "contest_recon",
                    "schema": AssessmentBundle.model_json_schema(),
                    "strict": True,
                },
                "verbosity": "low",
            },
            store=False,
        )

        bundle = AssessmentBundle.model_validate_json(response.output_text)
        by_id = {assessment.contest_id: assessment for assessment in bundle.assessments}
        missing = [contest.id for contest in contests if contest.id not in by_id]
        if missing:
            raise RuntimeError(f"Model omitted contest ids: {missing}")
        return [by_id[contest.id] for contest in contests]
