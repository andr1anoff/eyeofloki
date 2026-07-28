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
                            "prize_delivery": "location_bound",
                            "prize_value_eur": 60,
                    "prize_delivery": "location_bound",
                    "prize_value_eur": 60,
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
        excerpt=(
            "Gewinnspiel: free entry form, ten cinema ticket pairs to win, deadline 2099-08-01. Teilnahme ist kostenlos und ohne Kauf moeglich. Der Rechtsweg ist ausgeschlossen. Teilnahmeberechtigt sind volljaehrige Personen mit Wohnsitz in Deutschland. Die Gewinner werden per E-Mail benachrichtigt."
        ),
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


def test_rejections_name_the_host_and_the_reason() -> None:
    search = FakeDiscoverySearch()
    models = FakeDiscoveryModels()
    gemini = SimpleNamespace(aio=SimpleNamespace(models=models))
    engine = ContestDiscovery(
        Settings(GEMINI_API_KEY="test", TAVILY_API_KEY="test",
                 DISCOVERY_QUERIES_PER_RUN=1,
                 DISCOVERY_MIN_SCORE=99),
        genai_client=gemini,
        search_client=search,
        page_fetcher=fake_page_fetcher,
    )
    result = asyncio.run(engine.discover(DiscoveryRequest(round=0)))

    assert result.discoveries == []
    assert result.rejected_candidates == 1
    assert len(result.rejections) == 1
    note = result.rejections[0]
    assert note.host == "known.example"
    assert note.reason.startswith("score ")


def _listing_html(count: int = 8) -> str:
    items = "".join(
        f'<a href="/gewinnspiel/{i}">Gewinnspiel {i}</a>'
        f"<p>Verlosung. Einsendeschluss ist der 0{i}.08.2026.</p>"
        for i in range(1, count + 1)
    )
    return f"<html><head><title>Alle Gewinnspiele</title></head><body>{items}</body></html>"


def test_listing_pages_are_flagged_as_hubs() -> None:
    from bs4 import BeautifulSoup

    from railway.app.fetcher import _hub_signals

    html = _listing_html()
    signals, score, _links = _hub_signals(html, BeautifulSoup(html, "html.parser"))
    assert score > 45
    assert signals


def test_single_contest_page_is_not_flagged() -> None:
    from bs4 import BeautifulSoup

    from railway.app.fetcher import _hub_signals

    html = (
        "<html><head><title>Wir verlosen 2x2 Tickets</title></head><body>"
        "<p>Gewinnspiel: Einsendeschluss ist der 09.08.2026.</p>"
        '<form><input name="email"><button type="submit">Absenden</button>'
        "</form></body></html>"
    )
    signals, score, _links = _hub_signals(html, BeautifulSoup(html, "html.parser"))
    assert score == 0
    assert signals == []


def test_hub_score_is_passed_to_the_model_as_evidence() -> None:
    """Structure alone cannot separate a contest portal hosting one real
    giveaway from a pure directory, so the model gets the signal and the
    final say."""

    async def hub_page_fetcher(contest, _settings):
        return PageEvidence(
            contest_id=contest.id,
            final_url=str(contest.url),
            status_code=200,
            reachable=True,
            title=contest.title,
            excerpt=("Alle Gewinnspiele auf einen Blick. " * 12),
            entry_signals=[],
            registration_signals=[],
            hub_signals=["12 links to other contests"],
            hub_score=90,
            contest_links=[],
        )

    search = FakeDiscoverySearch()
    models = FakeDiscoveryModels()
    gemini = SimpleNamespace(aio=SimpleNamespace(models=models))
    engine = ContestDiscovery(
        Settings(GEMINI_API_KEY="test", TAVILY_API_KEY="test",
                 DISCOVERY_QUERIES_PER_RUN=1),
        genai_client=gemini,
        search_client=search,
        page_fetcher=hub_page_fetcher,
    )
    asyncio.run(engine.discover(DiscoveryRequest(round=0)))

    assert models.calls, "hub pages must still be assessed"
    sent = str(models.calls[0])
    assert "hub_score" in sent
    assert "12 links to other contests" in sent


def test_long_odds_are_dropped_by_the_floor() -> None:
    search = FakeDiscoverySearch()
    models = FakeDiscoveryModels()
    gemini = SimpleNamespace(aio=SimpleNamespace(models=models))
    engine = ContestDiscovery(
        Settings(GEMINI_API_KEY="test", TAVILY_API_KEY="test",
                 DISCOVERY_QUERIES_PER_RUN=1,
                 DISCOVERY_MIN_SCORE=0,
                 DISCOVERY_MIN_CHANCE_PPM=999_999),
        genai_client=gemini,
        search_client=search,
        page_fetcher=fake_page_fetcher,
    )
    result = asyncio.run(engine.discover(DiscoveryRequest(round=0)))

    assert result.discoveries == []
    assert "ppm below floor" in result.rejections[0].reason


def test_event_index_without_its_own_form_is_a_hub() -> None:
    from bs4 import BeautifulSoup

    from railway.app.fetcher import _hub_signals

    links = "".join(
        f'<a href="/event/{i}">Konzert {i}</a>' for i in range(200)
    )
    html = (
        "<html><head><title>Alle Partys</title></head><body>"
        "<p>Verlosung Verlosung Verlosung Verlosung Verlosung Verlosung</p>"
        f"<form></form>{links}</body></html>"
    )
    _signals, score, _links = _hub_signals(html, BeautifulSoup(html, "html.parser"))
    assert score > 45


def test_listing_links_are_followed_instead_of_binned() -> None:
    """The whole point: a hub is a directory of the pages we want."""

    async def fetcher(contest, _settings):
        url = str(contest.url)
        if "listing" in url:
            return PageEvidence(
                contest_id=contest.id, final_url=url, status_code=200,
                reachable=True, title="Alle Gewinnspiele",
                excerpt=("Gewinnspiel Uebersicht aller Verlosungen. " * 12),
                entry_signals=[],
                registration_signals=[],
                hub_signals=["20 links to other contests"], hub_score=90,
                contest_links=[
                    "https://brand.example/gewinnspiel/kopfhoerer",
                    "https://brand.example/gewinnspiel/tablet",
                ],
            )
        return PageEvidence(
            contest_id=contest.id, final_url=url, status_code=200,
            reachable=True, title="Wir verlosen Kopfhoerer",
            excerpt=("Gewinnspiel Teilnahmeschluss 30.09.2026. " * 12),
            entry_signals=["form"],
            registration_signals=[], hub_signals=[], hub_score=0,
            contest_links=[],
        )

    class ListingSearch:
        async def search(self, **_kw):
            return {
                "results": [
                    {
                        "url": "https://portal.example/listing",
                        "title": "Alle Gewinnspiele im Ueberblick",
                        "content": "Gewinnspiel Verlosung teilnehmen",
                    }
                ]
            }

    models = FakeDiscoveryModels()
    gemini = SimpleNamespace(aio=SimpleNamespace(models=models))
    engine = ContestDiscovery(
        Settings(GEMINI_API_KEY="test", TAVILY_API_KEY="test",
                 DISCOVERY_QUERIES_PER_RUN=1),
        genai_client=gemini,
        search_client=ListingSearch(),
        page_fetcher=fetcher,
    )
    result = asyncio.run(engine.discover(DiscoveryRequest(round=0)))

    # The listing supplies two candidates the search never surfaced.
    # one from search, two followed off the listing
    assert result.novel_candidates == 3
    assert models.calls, "harvested candidates must reach the model"
    sent = str(models.calls[0])
    assert "gewinnspiel/kopfhoerer" in sent
    assert "gewinnspiel/tablet" in sent


def test_delivery_and_value_survive_the_trip_to_scoring() -> None:
    """Regression: these fields were dropped in the conversion from the
    discovery assessment to the scoring model, so every prize came back
    location_bound and worth nothing."""
    search = FakeDiscoverySearch()
    models = FakeDiscoveryModels()
    gemini = SimpleNamespace(aio=SimpleNamespace(models=models))
    engine = ContestDiscovery(
        Settings(GEMINI_API_KEY="test", TAVILY_API_KEY="test",
                 DISCOVERY_QUERIES_PER_RUN=1, DISCOVERY_MIN_SCORE=0,
                 DISCOVERY_MIN_CHANCE_PPM=0),
        genai_client=gemini,
        search_client=search,
        page_fetcher=fake_page_fetcher,
    )
    result = asyncio.run(engine.discover(DiscoveryRequest(round=0)))

    analysis = result.discoveries[0].analysis
    assert analysis.prize_value_eur == 60
    assert analysis.prize_delivery == "location_bound"
    assert analysis.ev_cents_per_minute > 0
