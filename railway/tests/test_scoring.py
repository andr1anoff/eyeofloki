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
