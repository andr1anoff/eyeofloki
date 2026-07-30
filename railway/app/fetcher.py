import asyncio
import ipaddress
import socket
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

from .models import ContestInput, PageEvidence
from .settings import Settings


ENTRY_SIGNALS = {
    "<form": "form",
    "teilnehmen": "participation copy",
    "jetzt mitmachen": "join call-to-action",
    "absenden": "submit copy",
    "gewinnspielfrage": "contest question",
    "gewinnspiele@": "email entry",
    "type=\"submit\"": "submit control",
}

REGISTRATION_SIGNALS = {
    "registrieren": "registration",
    "konto erstellen": "account creation",
    "account erstellen": "account creation",
    "login": "login",
    "anmelden": "sign-in",
}


# A page that lists many contests is an aggregator, not an entry point.
SOCIAL_HOSTS = {
    "instagram.com",
    "facebook.com",
    "tiktok.com",
    "x.com",
    "twitter.com",
    "threads.net",
    "youtube.com",
}


EVIDENCE_TERMS = (
    "teilnahmeformular",
    "gewinnspielformular",
    "online-formular",
    "einsendeschluss",
    "teilnahmeschluss",
    "teilnahmeberechtigt",
    "wohn­sitz",
    "wohnsitz",
    "gewinnspiel",
    "verlosung",
    "gewinner",
    "preis",
    "formular",
    "deadline",
    "eligible",
    "eligibility",
    "entry form",
    "winner",
    "prize",
    "no purchase",
)


def _evidence_excerpt(text: str, limit: int = 3_600) -> str:
    """Keep high-value rules/form passages instead of the first 16k characters.

    Most contest pages spend thousands of characters on navigation and marketing.
    Small windows around deadlines, eligibility and form terms carry more evidence
    per token and leave room to inspect more candidates in one model request.
    """

    compact = " ".join(text.split())
    if len(compact) <= limit:
        return compact

    lowered = compact.casefold()
    spans: list[tuple[int, int]] = [(0, min(250, len(compact)))]
    for term in EVIDENCE_TERMS:
        start = lowered.find(term.casefold())
        if start < 0:
            continue
        spans.append((max(0, start - 120), min(len(compact), start + 620)))

    spans.sort()
    merged: list[list[int]] = []
    for start, end in spans:
        if merged and start <= merged[-1][1] + 80:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])

    chunks: list[str] = []
    used = 0
    for start, end in merged:
        chunk = compact[start:end].strip()
        if not chunk:
            continue
        remaining = limit - used - (3 if chunks else 0)
        if remaining <= 0:
            break
        chunks.append(chunk[:remaining])
        used += min(len(chunk), remaining) + (3 if len(chunks) > 1 else 0)
    return " … ".join(chunks)[:limit]


def _hub_signals(
    html: str, soup, host: str = ""
) -> tuple[list[str], int, list[str]]:
    # Social pages are filtered before fetching by default. Keep this exception
    # for backwards-compatible parser tests and manually supplied pages.
    if host.removeprefix("www.") in SOCIAL_HOSTS:
        return [], 0, []
    lowered = html.lower()
    signals: list[str] = []
    mentions = lowered.count("gewinnspiel") + lowered.count("verlosung")
    forms = lowered.count("<form")
    links = len(soup.find_all("a", href=True))
    outbound = [
        anchor["href"]
        for anchor in soup.find_all("a", href=True)
        if any(
            token in (anchor.get("href") or "").lower()
            for token in ("gewinnspiel", "verlosung", "wettbewerb", "giveaway")
        )
    ]
    contest_links = len(outbound)
    deadlines = lowered.count("einsendeschluss") + lowered.count(
        "teilnahmeschluss"
    )

    score = 0
    if contest_links >= 4:
        signals.append(f"{contest_links} links to other contests")
        score += 45
    if mentions >= 12:
        signals.append(f"the word appears {mentions} times")
        score += 25
    if deadlines >= 3:
        signals.append(f"{deadlines} separate deadlines on one page")
        score += 25
    if forms == 0 and contest_links >= 2:
        signals.append("no form of its own")
        score += 20
    if mentions >= 6 and links >= 150 and forms <= 1:
        signals.append("event index with no entry form of its own")
        score += 50
    if links >= 120 and forms <= 1:
        signals.append("link-heavy index layout")
        score += 10
    return signals, min(100, score), outbound[:40]


async def _assert_public_host(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("Only public http(s) URLs are supported")

    infos = await asyncio.to_thread(
        socket.getaddrinfo,
        parsed.hostname,
        parsed.port or (443 if parsed.scheme == "https" else 80),
        type=socket.SOCK_STREAM,
    )
    for info in infos:
        address = ipaddress.ip_address(info[4][0])
        if (
            address.is_private
            or address.is_loopback
            or address.is_link_local
            or address.is_multicast
            or address.is_reserved
            or address.is_unspecified
        ):
            raise ValueError("Private or reserved network targets are blocked")


def _page_text(
    html: str, host: str = ""
) -> tuple[str, str, list[str], int, list[str]]:
    soup = BeautifulSoup(html, "html.parser")
    title = soup.title.get_text(" ", strip=True) if soup.title else ""
    hub_signals, hub_score, outbound = _hub_signals(html, soup, host)
    for node in soup(["script", "style", "noscript", "svg"]):
        node.decompose()
    text = soup.get_text(" ", strip=True)
    return (
        title[:240],
        _evidence_excerpt(text),
        hub_signals,
        hub_score,
        outbound,
    )


async def fetch_contest_page(
    contest: ContestInput,
    settings: Settings,
) -> PageEvidence:
    current_url = str(contest.url)
    headers = {
        "user-agent": (
            "Mozilla/5.0 (compatible; EyeOfLoki/2.0; "
            "+personal contest verifier)"
        ),
        "accept-language": "de-DE,de;q=0.9,en;q=0.7",
    }

    try:
        async with httpx.AsyncClient(
            timeout=settings.PAGE_FETCH_TIMEOUT_SECONDS,
            headers=headers,
            follow_redirects=False,
        ) as client:
            response: httpx.Response | None = None
            for _ in range(5):
                await _assert_public_host(current_url)
                response = await client.get(current_url)
                if response.status_code not in {301, 302, 303, 307, 308}:
                    break
                location = response.headers.get("location")
                if not location:
                    break
                current_url = urljoin(current_url, location)

            if response is None:
                raise RuntimeError("No response")

            html = response.text[:750_000]
            lowered = html.lower()
            (
                title,
                excerpt,
                hub_signals,
                hub_score,
                outbound,
            ) = _page_text(html, urlparse(str(response.url)).hostname or "")
            return PageEvidence(
                contest_id=contest.id,
                final_url=current_url,
                status_code=response.status_code,
                reachable=response.is_success,
                title=title,
                excerpt=excerpt,
                entry_signals=[
                    label
                    for token, label in ENTRY_SIGNALS.items()
                    if token in lowered
                ],
                registration_signals=[
                    label
                    for token, label in REGISTRATION_SIGNALS.items()
                    if token in lowered
                ],
                hub_signals=hub_signals,
                hub_score=hub_score,
                contest_links=[
                    urljoin(str(response.url), href) for href in outbound
                ],
            )
    except Exception as exc:
        return PageEvidence(
            contest_id=contest.id,
            final_url=current_url,
            status_code=0,
            reachable=False,
            title="",
            excerpt=f"Fetch failed: {type(exc).__name__}",
            entry_signals=[],
            registration_signals=[],
            hub_signals=[],
            hub_score=0,
            contest_links=[],
        )
