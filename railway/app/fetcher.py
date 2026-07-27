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


def _page_text(html: str) -> tuple[str, str]:
    soup = BeautifulSoup(html, "html.parser")
    title = soup.title.get_text(" ", strip=True) if soup.title else ""
    for node in soup(["script", "style", "noscript", "svg"]):
        node.decompose()
    text = " ".join(soup.get_text(" ", strip=True).split())
    return title[:240], text[:16_000]


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
            title, excerpt = _page_text(html)
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
        )
