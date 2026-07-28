"""The fetcher swallows every exception into an unreachable PageEvidence,
so a plain TypeError in here looks exactly like a dead website. These tests
exercise the real parsing path against local HTML."""

import asyncio

from railway.app.fetcher import _page_text
from railway.app.models import ContestInput
from railway.app.settings import Settings


SINGLE = """
<html><head><title>Wir verlosen 2x2 Tickets</title></head>
<body><p>Gewinnspiel. Einsendeschluss ist der 09.08.2026.</p>
<form><input name="email"><button type="submit">Absenden</button></form>
</body></html>
"""

LISTING = "<html><head><title>Alle Gewinnspiele</title></head><body>" + "".join(
    f'<a href="/gewinnspiel/{i}">Verlosung {i}</a>'
    f"<p>Einsendeschluss ist der 0{i % 9 + 1}.09.2026.</p>"
    for i in range(12)
) + "</body></html>"


def test_page_text_returns_five_values_and_real_content():
    title, text, signals, score, outbound = _page_text(SINGLE, "example.de")
    assert title.startswith("Wir verlosen")
    assert "Einsendeschluss" in text
    assert score == 0
    assert signals == []
    assert outbound == []


def test_page_text_flags_a_listing_and_keeps_its_links():
    _title, _text, signals, score, outbound = _page_text(LISTING, "portal.de")
    assert score > 45
    assert signals
    assert len(outbound) >= 10


def test_social_hosts_are_exempt_from_hub_scoring():
    _t, _x, signals, score, outbound = _page_text(LISTING, "www.instagram.com")
    assert (signals, score, outbound) == ([], 0, [])


def test_unreachable_host_yields_an_unreachable_page_not_a_crash():
    settings = Settings(GEMINI_API_KEY="x", TAVILY_API_KEY="x")
    contest = ContestInput(
        id=1, slug="t", title="t", organizer="t", prize="t",
        url="https://nonexistent.invalid/contest", deadline="2026-09-01",
    )
    from railway.app.fetcher import fetch_contest_page

    page = asyncio.run(fetch_contest_page(contest, settings))
    assert page.reachable is False
    assert page.hub_score == 0
    assert page.contest_links == []
