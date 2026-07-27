import asyncio
import json
from types import SimpleNamespace

from railway.app.models import ContestInput, PageEvidence, UserProfile
from railway.app.research import GeminiContestAnalyst
from railway.app.settings import Settings


class FakeSearchClient:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    async def search(self, **kwargs):
        self.calls.append(kwargs)
        return {
            "results": [
                {
                    "title": "Official rules",
                    "url": "https://example.com/rules",
                    "content": "Ends 2026-08-01. One winner.",
                    "score": 0.94,
                }
            ]
        }


class FakeModels:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    async def generate_content(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(
            text=json.dumps(
                {
                    "assessments": [
                        {
                            "contest_id": 1,
                            "active": True,
                            "entry_mechanism_found": True,
                            "registration_required": False,
                            "newsletter_required": False,
                            "corrected_deadline": "2026-08-01",
                            "corrected_winners": 1,
                            "entrants_low": 500,
                            "entrants_likely": 1000,
                            "entrants_high": 2500,
                            "competition": "Medium",
                            "confidence": "Medium",
                            "prize_utility": 70,
                            "legitimacy": 90,
                            "locality_fit": 80,
                            "friction_minutes": 2,
                            "summary": "A legitimate short-form contest.",
                            "reasons": ["Official rules found", "No account"],
                            "evidence_urls": [
                                "https://example.com/contest",
                                "https://example.com/rules",
                            ],
                            "blocking_reason": "",
                        }
                    ]
                }
            )
        )


def test_gemini_analysis_uses_basic_search_and_json_schema() -> None:
    search = FakeSearchClient()
    models = FakeModels()
    gemini = SimpleNamespace(aio=SimpleNamespace(models=models))
    analyst = GeminiContestAnalyst(
        Settings(
            GEMINI_API_KEY="test",
            TAVILY_API_KEY="test",
            SEARCH_RESULTS_PER_CONTEST=4,
        ),
        genai_client=gemini,
        search_client=search,
    )
    contests = [
        ContestInput(
            id=1,
            slug="example",
            title="Example contest",
            organizer="Example",
            prize="Tickets",
            url="https://example.com/contest",
            deadline="2026-08-01",
        )
    ]
    pages = [
        PageEvidence(
            contest_id=1,
            final_url="https://example.com/contest",
            status_code=200,
            reachable=True,
            title="Example contest",
            excerpt="Enter now.",
            entry_signals=["form"],
            registration_signals=[],
        )
    ]

    assessments = asyncio.run(
        analyst.analyze(contests, pages, UserProfile())
    )

    assert assessments[0].entrants_likely == 1000
    assert search.calls[0]["search_depth"] == "basic"
    assert search.calls[0]["max_results"] == 4
    assert models.calls[0]["model"] == "gemini-3.5-flash-lite"
    config = models.calls[0]["config"]
    assert config["response_mime_type"] == "application/json"
    assert "properties" in config["response_json_schema"]
