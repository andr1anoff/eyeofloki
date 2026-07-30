from railway.app.fetcher import _evidence_excerpt
from railway.app.models import DiscoveryRequest, ModelAssessment
from railway.app.policy import DISCOVERY_PROMPT, HUNT_PROMPT, RECON_PROMPT
from railway.app.scoring import score_assessment
from railway.app.settings import Settings
from railway.app.webform_discovery import website_form_waves


def test_form_search_waves_are_broad_unique_and_non_social() -> None:
    waves = website_form_waves(DiscoveryRequest(round=0), width=8)
    queries = [query for wave in waves for query in wave]

    assert [len(wave) for wave in waves] == [8, 8, 8]
    assert len(queries) == len(set(query.casefold() for query in queries))
    assert all(
        any(
            token in query.casefold()
            for token in ("form", "formular", "teilnahme", "teilnehmen")
        )
        for query in queries
    )
    assert not any(
        social in query.casefold()
        for query in queries
        for social in ("instagram", "facebook", "tiktok", "twitter", "youtube")
    )


def test_prompts_are_compact_and_explicitly_reject_social_entry() -> None:
    combined = " ".join((DISCOVERY_PROMPT, RECON_PROMPT, HUNT_PROMPT)).casefold()
    assert len(DISCOVERY_PROMPT) < 2_000
    assert len(RECON_PROMPT) < 1_500
    assert "on-site web form" in combined or "form on the organiser" in combined
    assert "social-media" in combined
    assert "english" in combined


def test_social_hosts_are_blocked_by_default() -> None:
    blocked = Settings().blocked_hosts
    assert {"instagram.com", "facebook.com", "tiktok.com", "x.com"} <= blocked


def test_evidence_excerpt_keeps_late_rules_with_small_token_budget() -> None:
    noisy = "Navigation filler " * 600
    rules = (
        "Teilnahmeformular. Teilnahmeberechtigt sind Erwachsene mit Wohnsitz "
        "in Deutschland. Einsendeschluss ist der 30.09.2026."
    )
    excerpt = _evidence_excerpt(noisy + rules, limit=900)

    assert len(excerpt) <= 900
    assert "Einsendeschluss" in excerpt
    assert "Wohnsitz" in excerpt


def test_translated_conditions_survive_scoring() -> None:
    assessment = ModelAssessment(
        contest_id=1,
        active=True,
        entry_mechanism_found=True,
        registration_required=False,
        newsletter_required=False,
        eligibility="Adults aged 18+ who reside in Germany",
        entry_method="Complete the form and answer one question",
        corrected_deadline="2099-09-30",
        corrected_winners=2,
        entrants_low=200,
        entrants_likely=500,
        entrants_high=1200,
        competition="Medium",
        confidence="Medium",
        prize_utility=80,
        legitimacy=95,
        locality_fit=100,
        prize_delivery="location_bound",
        prize_value_eur=80,
        friction_minutes=1,
        summary="A direct website-form contest.",
        reasons=["Working form", "Free entry"],
        evidence_urls=["https://example.com/contest"],
        blocking_reason="",
    )

    result = score_assessment(assessment)
    assert result.eligibility.startswith("Adults")
    assert result.entry_method.startswith("Complete the form")
