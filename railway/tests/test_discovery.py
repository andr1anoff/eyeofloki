import asyncio
import json
from types import SimpleNamespace

from railway.app.discovery import (
    ContestDiscovery,
    discovery_queries,
    normalize_url,
)
from railway.app.models import (
    ContestInput,
    DiscoveryRequest,
    PageEvidence,
)
from railway.app.settings import Settings


class FakeDiscoverySearch:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    async def search(self, **kwargs):
        self.calls.append(kwargs)
        return {
            "results": [
                {
                    "title": "Already known giveaway",
                    "url": "https://known.example/contest?utm_source=test",
                    "content": "Gewinnspiel: jetzt teilnehmen.",
                },
                {
                    "title": "Berlin cinema night giveaway",
                    "url": "https://cinema.example/berlin-night",
                    "content": "Verlosung von zehn Freikarten bis 2099-08-01.",
                },
            ]
        }


class FakeDiscoveryModels:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    async def generate_content(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(
            text=json.dumps(
                {
                    "assessments": [
                        {
                            "candidate_id": 1,
                            "title": "Berlin cinema night",
                            "organizer": "Cinema Berlin",
                            "prize": "10 × two cinema tickets",
                            "locality": "Berlin",
                            "eligibility": "18+ · resident of Germany",
                            "entry_method": "Short form",
                            "active": True,
                            "free_entry": True,
                            "germany_eligible": True,
                            "entry_mechanism_found": True,
                            "registration_required": False,
                            "newsletter_required": False,
                            "corrected_deadline": "2099-08-01",
                            "corrected_winners": 10,
                            "entrants_low": 200,
                            "entrants_likely": 500,
                            "entrants_high": 1200,
                            "competition": "Low",
                            "confidence": "High",
                            "prize_utility": 80,
                            "legitimacy": 95,
                            "locality_fit": 100,
                            "friction_minutes": 1,
                            "summary": "A local free-entry ticket giveaway.",
                            "reasons": [
                                "Ten winners",
                                "Berlin-local audience",
                            ],
                            "evidence_urls": [
                                "https://cinema.example/berlin-night"
                            ],
                            "blocking_reason": "",
                        }
                    ]
                }
            )
        )


async def fake_page_fetcher(
    contest: ContestInput,
    _settings: Settings,
) -> PageEvidence:
    return PageEvidence(
        contest_id=contest.id,
        final_url=str(contest.url),
        status_code=200,
        reachable=True,
        title=contest.title,
        excerpt="Free entry form. Ten cinema ticket pairs. Deadline 2099-08-01.",
        entry_signals=["form", "participation copy"],
        registration_signals=[],
    )


def test_discovery_excludes_known_urls_and_deduplicates_search_results() -> None:
    search = FakeDiscoverySearch()
    models = FakeDiscoveryModels()
    gemini = SimpleNamespace(aio=SimpleNamespace(models=models))
    engine = ContestDiscovery(
        Settings(
            GEMINI_API_KEY="test",
            TAVILY_API_KEY="test",
            DISCOVERY_QUERIES_PER_RUN=3,
            DISCOVERY_RESULTS_PER_QUERY=8,
            MAX_DISCOVERY_CANDIDATES=10,
            DISCOVERY_MIN_SCORE=45,
        ),
        genai_client=gemini,
        search_client=search,
        page_fetcher=fake_page_fetcher,
    )

    result = asyncio.run(
        engine.discover(
            DiscoveryRequest(
                known_urls=["https://known.example/contest"],
                known_titles=["Already known giveaway"],
                round=0,
            )
        )
    )

    assert len(search.calls) == 3
    assert all(call["search_depth"] == "basic" for call in search.calls)
    assert result.raw_candidates == 6
    assert result.novel_candidates == 1
    assert len(result.discoveries) == 1
    assert result.discoveries[0].title == "Berlin cinema night"
    assert result.discoveries[0].analysis.status == "READY"
    assert result.discoveries[0].analysis.analysis_method.endswith(
        "deterministic-score-v5"
    )


def test_discovery_query_rounds_rotate() -> None:
    first = discovery_queries(0, 8)
    second = discovery_queries(1, 8)
    fifth = discovery_queries(4, 8)
    assert first != second
    assert not set(first).intersection(second)
    assert first != fifth


def test_url_normalization_removes_tracking_and_www() -> None:
    assert normalize_url(
        "https://www.example.com/contest/?utm_source=x#entry"
    ) == "https://example.com/contest"


def test_deprecated_sampling_parameters_are_not_sent() -> None:
    search = FakeDiscoverySearch()
    models = FakeDiscoveryModels()
    gemini = SimpleNamespace(aio=SimpleNamespace(models=models))
    engine = ContestDiscovery(
        Settings(GEMINI_API_KEY="test", TAVILY_API_KEY="test",
                 DISCOVERY_QUERIES_PER_RUN=1),
        genai_client=gemini,
        search_client=search,
        page_fetcher=fake_page_fetcher,
    )
    asyncio.run(engine.discover(DiscoveryRequest(round=0)))

    config = models.calls[0]["config"]
    assert "temperature" not in config
    assert "top_p" not in config
    assert "top_k" not in config
    assert config["thinking_config"]["thinking_level"] == "medium"


def test_blocked_hosts_are_dropped_before_the_model_is_billed() -> None:
    search = FakeDiscoverySearch()
    models = FakeDiscoveryModels()
    gemini = SimpleNamespace(aio=SimpleNamespace(models=models))
    engine = ContestDiscovery(
        Settings(GEMINI_API_KEY="test", TAVILY_API_KEY="test",
                 DISCOVERY_QUERIES_PER_RUN=1,
                 DISCOVERY_BLOCKED_HOSTS="cinema.example, known.example"),
        genai_client=gemini,
        search_client=search,
        page_fetcher=fake_page_fetcher,
    )
    result = asyncio.run(engine.discover(DiscoveryRequest(round=0)))

    assert result.novel_candidates == 0
    assert result.discoveries == []
    assert models.calls == []


def test_truncation_is_not_counted_as_rejection() -> None:
    search = FakeDiscoverySearch()
    models = FakeDiscoveryModels()
    gemini = SimpleNamespace(aio=SimpleNamespace(models=models))
    engine = ContestDiscovery(
        Settings(GEMINI_API_KEY="test", TAVILY_API_KEY="test",
                 DISCOVERY_QUERIES_PER_RUN=1),
        genai_client=gemini,
        search_client=search,
        page_fetcher=fake_page_fetcher,
    )
    result = asyncio.run(
        engine.discover(DiscoveryRequest(round=0, limit=1))
    )
    assert result.rejected_candidates == 0
    assert result.truncated_candidates == 0
    assert len(result.discoveries) == 1
