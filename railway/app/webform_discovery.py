"""High-recall discovery for contests entered through ordinary website forms.

Query planning is deterministic because generating search phrases does not need an
LLM. This removes one Gemini call from every discovery run, makes coverage
predictable, and reserves model tokens for verifying real candidate pages.
"""

from __future__ import annotations

from datetime import date

from .adaptive_discovery import AdaptiveContestDiscovery, _clean_queries
from .discovery import ContestDiscovery, GERMAN_MONTHS
from .models import DiscoveryRequest
from .policy import configure_prompts
from .settings import Settings

configure_prompts()


def _rotated(values: list[str], round_number: int, width: int) -> list[str]:
    if not values:
        return []
    width = max(1, min(width, len(values)))
    start = (round_number * width) % len(values)
    return [values[(start + index) % len(values)] for index in range(width)]


def website_form_waves(request: DiscoveryRequest, width: int = 8) -> list[list[str]]:
    """Return broad, non-social search lanes that rotate between runs."""

    today = date.today()
    month = GERMAN_MONTHS[today.month - 1]
    year = today.year

    berlin = [
        f'Berlin Gewinnspiel Teilnahmeformular Tickets {month} {year}',
        'Berlin Verlosung Online-Formular Freikarten',
        'Berlin Konzert Gewinnspielformular Einsendeschluss',
        'Berlin Kino Vorpremiere Gewinnspiel Formular',
        'Berlin Museum Ausstellung Gewinnspiel Teilnahmeformular',
        'Berlin Theater Comedy Verlosung Online Formular',
        'Berlin Festival Gästeliste Formular Teilnahmeschluss',
        'Berlin Buch Lesung Gewinnspiel Formular',
        'site:radioeins.de Gewinnspiel Teilnahmeformular',
        'site:fluxfm.de Gewinnspiel Formular Tickets',
        'site:tip-berlin.de Verlosung Teilnahmeformular',
        'site:yorck.de Gewinnspiel Online Formular',
        'site:berlinerfestspiele.de Gewinnspiel Formular',
        'site:visitberlin.de Gewinnspiel Teilnahme',
        'site:tagesspiegel.de Gewinnspiel Formular Berlin',
        'site:berliner-zeitung.de Gewinnspiel Teilnahmeformular',
    ]

    germany = [
        f'Deutschland Gewinnspiel Teilnahmeformular ohne Kauf {month} {year}',
        'Deutschland Technik Gewinnspiel Online Formular Einsendeschluss',
        'Deutschland Kopfhörer Konsole Gewinnspiel Teilnahmeformular',
        'Deutschland Reise Städtereise Gewinnspiel Formular',
        'Deutschland Bücher Spiele Fanpaket Verlosung Formular',
        'Deutschland Gutschein Gewinnspiel Online teilnehmen ohne Kauf',
        'Deutschland Kinotickets Konzerttickets Gewinnspiel Formular',
        'Deutschland mehrere Gewinner Gewinnspiel Teilnahmeformular',
        'Deutschland täglich teilnehmen Gewinnspiel Online Formular',
        'Gewinnspielfrage beantworten Online Formular Deutschland',
        '"Teilnahmeformular" "Einsendeschluss" Gewinnspiel Deutschland',
        '"Gewinnspielformular" Verlosung Deutschland',
        '"jetzt teilnehmen" Gewinnspiel Formular Deutschland',
        '"unter allen Einsendungen" Gewinnspiel Formular Deutschland',
        'site:arte.tv Gewinnspiel Teilnahmeformular Deutschland',
        'site:deutschlandfunkkultur.de Gewinnspiel Formular',
    ]

    europe = [
        'giveaway entry form open to Germany free entry',
        'EU residents giveaway online form no purchase',
        'Europe electronics giveaway form ships to Germany',
        'headphones keyboard giveaway entry form Germany eligible',
        'games console giveaway form open to EU residents',
        'book board game giveaway entry form Europe',
        'digital voucher giveaway form open to Germany',
        'travel giveaway online entry form Germany eligible',
        'multiple winners giveaway form open to EU',
        'daily giveaway entry form Europe no purchase',
        'international giveaway form ships to Germany',
        'camera tech giveaway online form EU residents',
        'festival tickets giveaway form Berlin Germany',
        'cinema tickets giveaway entry form Germany',
        'publisher giveaway entry form open to Germany',
        'brand giveaway official entry form EU residents',
    ]

    return [
        _clean_queries(_rotated(berlin, request.round, width)),
        _clean_queries(_rotated(germany, request.round + 1, width)),
        _clean_queries(_rotated(europe, request.round + 2, width)),
    ]


class WebsiteFormDiscovery(AdaptiveContestDiscovery):
    """Adaptive validator with deterministic form-focused query coverage."""

    def __init__(
        self,
        settings: Settings,
        *,
        discovery_factory=ContestDiscovery,
    ) -> None:
        # A sentinel prevents the parent from constructing a planner client. The
        # overridden _plan never calls it.
        super().__init__(
            settings,
            planner_client=object(),
            discovery_factory=discovery_factory,
        )

    async def _plan(self, request: DiscoveryRequest) -> list[list[str]]:
        if request.queries:
            clean = _clean_queries(request.queries)
            width = max(3, min(self.settings.ADAPTIVE_QUERIES_PER_PASS, 8))
            return [
                clean[index : index + width]
                for index in range(0, len(clean), width)
                if clean[index : index + width]
            ]
        return website_form_waves(
            request,
            width=max(6, min(self.settings.ADAPTIVE_QUERIES_PER_PASS, 8)),
        )
