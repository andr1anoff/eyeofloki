import pytest
from pydantic import ValidationError

from railway.app.models import ModelAssessment
from railway.app.scoring import probability_ppm, score_assessment


def assessment(**overrides):
    values = {
        "contest_id": 1,
        "active": True,
        "entry_mechanism_found": True,
        "registration_required": False,
        "newsletter_required": False,
        "corrected_deadline": "2099-08-09",
        "corrected_winners": 20,
        "entrants_low": 800,
        "entrants_likely": 1800,
        "entrants_high": 4000,
        "competition": "Low",
        "confidence": "Medium",
        "prize_utility": 80,
        "legitimacy": 95,
        "locality_fit": 100,
        "prize_delivery": "location_bound",
        "prize_value_eur": 60,
        "friction_minutes": 1,
        "summary": "Local contest with several winners.",
        "reasons": ["Local", "Twenty winners"],
        "evidence_urls": ["https://example.com/contest"],
        "blocking_reason": "",
    }
    values.update(overrides)
    return ModelAssessment(**values)


def test_probability_uses_winner_depth():
    assert probability_ppm(20, 2000) == 10_000
    assert probability_ppm(1, 2000) == 500


def test_score_returns_probability_range():
    result = score_assessment(assessment())
    assert result.chance_low_ppm == 5_000
    assert result.chance_likely_ppm == 11_111
    assert result.chance_high_ppm == 25_000
    assert result.status == "READY"
    assert result.score >= 60


def test_missing_entry_path_is_blocked():
    result = score_assessment(
        assessment(
            active=False,
            entry_mechanism_found=False,
            blocking_reason="Rules only; no form",
        )
    )
    assert result.score == 0
    assert result.status == "BLOCKED"
    assert result.verdict == "Rules only; no form"


def test_registration_reduces_score():
    clean = score_assessment(assessment())
    gated = score_assessment(
        assessment(registration_required=True, newsletter_required=True)
    )
    assert gated.score < clean.score


def test_deadline_normalizes_full_iso_timestamp():
    parsed = assessment(corrected_deadline="2026-08-09T00:00:00Z")
    assert parsed.corrected_deadline == "2026-08-09"


def test_impossible_deadline_is_rejected():
    with pytest.raises(ValidationError):
        assessment(corrected_deadline="2026-02-31")


def test_crowd_label_replaces_spurious_precision():
    crowded = score_assessment(
        assessment(corrected_winners=1, entrants_low=40_000,
                   entrants_likely=60_000, entrants_high=90_000)
    )
    roomy = score_assessment(
        assessment(corrected_winners=50, entrants_low=200,
                   entrants_likely=400, entrants_high=800)
    )
    assert crowded.crowd == "Very crowded"
    assert roomy.crowd == "Few entrants"


def test_prize_outweighs_chance_in_the_new_weighting():
    great_prize_long_odds = score_assessment(
        assessment(prize_utility=100, corrected_winners=1,
                   entrants_low=5_000, entrants_likely=9_000,
                   entrants_high=20_000)
    )
    poor_prize_short_odds = score_assessment(
        assessment(prize_utility=10, corrected_winners=200,
                   entrants_low=300, entrants_likely=500,
                   entrants_high=900)
    )
    assert great_prize_long_odds.score > poor_prize_short_odds.score
