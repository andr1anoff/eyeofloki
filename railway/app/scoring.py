import math
from datetime import date, datetime, timezone

from .models import ContestAnalysis, ModelAssessment, ScoreBreakdown


def probability_ppm(winners: int, entrants: int) -> int:
    if winners <= 0 or entrants <= 0:
        return 0
    return round(min(1.0, winners / entrants) * 1_000_000)


def _chance_score(chance_likely_ppm: int) -> int:
    probability = max(chance_likely_ppm / 1_000_000, 0.000001)
    # Log scale: 0.001% ≈ 0, 0.1% ≈ 40, 1% ≈ 60, 10% ≈ 80.
    return round(max(0.0, min(100.0, (math.log10(probability) + 5) * 20)))


def _friction_score(
    minutes: float,
    registration_required: bool,
    newsletter_required: bool,
) -> int:
    score = 100 - min(minutes, 30) * 8
    if registration_required:
        score -= 18
    if newsletter_required:
        score -= 12
    return round(max(0, min(100, score)))


def crowd_label(chance_likely_ppm: int) -> str:
    """Coarse crowd bucket. Deliberately not a number: entrant counts are
    model estimates with no ground truth, so ppm precision is spurious."""
    if chance_likely_ppm >= 50_000:
        return "Few entrants"
    if chance_likely_ppm >= 10_000:
        return "Moderate crowd"
    if chance_likely_ppm >= 1_000:
        return "Crowded"
    return "Very crowded"


def _urgency_score(deadline: str) -> int:
    try:
        remaining = (date.fromisoformat(deadline) - date.today()).days
    except ValueError:
        return 20
    if remaining < 0:
        return 0
    if remaining <= 1:
        return 100
    if remaining <= 3:
        return 82
    if remaining <= 7:
        return 64
    if remaining <= 21:
        return 45
    return 28


def score_assessment(assessment: ModelAssessment) -> ContestAnalysis:
    analyzed_at = datetime.now(timezone.utc).isoformat()
    winners = max(1, assessment.corrected_winners)
    chance_low_ppm = probability_ppm(winners, assessment.entrants_high)
    chance_likely_ppm = probability_ppm(winners, assessment.entrants_likely)
    chance_high_ppm = probability_ppm(winners, assessment.entrants_low)

    breakdown = ScoreBreakdown(
        chance=_chance_score(chance_likely_ppm),
        prize=assessment.prize_utility,
        friction=_friction_score(
            assessment.friction_minutes,
            assessment.registration_required,
            assessment.newsletter_required,
        ),
        legitimacy=assessment.legitimacy,
        locality=assessment.locality_fit,
        urgency=_urgency_score(assessment.corrected_deadline),
    )

    # Chance is derived from an LLM entrant estimate that can never be
    # verified against an outcome, so it carries less weight than the
    # observable factors (prize, friction, legitimacy).
    weighted = round(
        breakdown.chance * 0.18
        + breakdown.prize * 0.28
        + breakdown.friction * 0.20
        + breakdown.legitimacy * 0.16
        + breakdown.locality * 0.10
        + breakdown.urgency * 0.08
    )

    blocked = not assessment.active or not assessment.entry_mechanism_found
    score = 0 if blocked else max(0, min(100, weighted))
    status = "BLOCKED" if blocked else "READY" if score >= 60 else "NEW"
    if blocked:
        verdict = assessment.blocking_reason or "No working entry path found"
    elif score >= 80:
        verdict = "Strong entry"
    elif score >= 60:
        verdict = "Worth entering"
    elif score >= 40:
        verdict = "Only if the prize matters"
    else:
        verdict = "Skip unless personally compelling"

    verification = (
        f"LLM web research + deterministic scoring. "
        f"Entrant count is an unverifiable model estimate "
        f"({assessment.entrants_low:,}–{assessment.entrants_high:,}, "
        f"confidence {assessment.confidence.lower()}); treat the odds as a "
        f"rough bucket, not a measurement."
    )

    return ContestAnalysis(
        contest_id=assessment.contest_id,
        score=score,
        status=status,
        verdict=verdict,
        competition=assessment.competition,
        confidence=assessment.confidence,
        entrants_low=assessment.entrants_low,
        entrants_likely=assessment.entrants_likely,
        entrants_high=assessment.entrants_high,
        chance_low_ppm=chance_low_ppm,
        chance_likely_ppm=chance_likely_ppm,
        chance_high_ppm=chance_high_ppm,
        crowd=crowd_label(chance_likely_ppm),
        friction_minutes=assessment.friction_minutes,
        registration_required=assessment.registration_required,
        newsletter_required=assessment.newsletter_required,
        deadline=assessment.corrected_deadline,
        winners=winners,
        summary=assessment.summary,
        reasons=assessment.reasons,
        evidence_urls=assessment.evidence_urls,
        verification=verification,
        score_breakdown=breakdown,
        analyzed_at=analyzed_at,
    )
