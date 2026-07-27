import math
from datetime import date, datetime, timezone

from .models import (
    ContestAnalysis,
    EntryCadence,
    ModelAssessment,
    PortfolioEntry,
    PrizeDelivery,
    ScoreBreakdown,
)


CADENCE_DAYS: dict[str, int] = {
    "once": 0,
    "daily": 1,
    "weekly": 7,
    "monthly": 30,
}


def entries_before_deadline(
    cadence: EntryCadence,
    deadline: str,
    cap: int = 60,
) -> int:
    """How many separate entries a repeatable contest allows before it
    closes. A daily contest running for three weeks is 21 lottery tickets,
    not one."""
    period = CADENCE_DAYS.get(cadence, 0)
    if period == 0:
        return 1
    try:
        remaining = (date.fromisoformat(deadline) - date.today()).days
    except ValueError:
        return 1
    if remaining < 0:
        return 0
    return max(1, min(cap, remaining // period + 1))


def combine_ppm(chance_ppm: int, attempts: int) -> int:
    """Probability of at least one win across independent attempts."""
    if chance_ppm <= 0 or attempts <= 0:
        return 0
    p = min(1.0, chance_ppm / 1_000_000)
    return round((1 - (1 - p) ** attempts) * 1_000_000)


def locality_score(
    delivery: PrizeDelivery,
    ships_to_germany: bool,
    model_locality_fit: int,
) -> int:
    """A parcel is worth the same from Lisbon as from Berlin. A ticket is
    not. Geography only constrains prizes you have to show up for."""
    if delivery == "digital":
        return 100
    if delivery == "shipped":
        return 100 if ships_to_germany else 0
    return model_locality_fit


def portfolio_ppm(chances: list[int]) -> int:
    """P(win at least one) across the whole portfolio."""
    miss = 1.0
    for ppm in chances:
        miss *= 1 - min(1.0, max(0, ppm) / 1_000_000)
    return round((1 - miss) * 1_000_000)


def select_for_budget(
    entries: list[PortfolioEntry],
    minutes_available: float,
) -> tuple[list[int], float, list[int]]:
    """Greedy by expected value per minute. With a time budget and
    independent draws this is the right objective: every minute should buy
    the most expected value it can."""
    ranked = sorted(
        entries,
        key=lambda e: (
            (e.chance_ppm / 1_000_000) * e.prize_value_eur
            / max(0.5, e.friction_minutes)
        ),
        reverse=True,
    )
    chosen: list[int] = []
    chances: list[int] = []
    marginal: list[int] = []
    spent = 0.0
    running = 0
    for entry in ranked:
        cost = max(0.5, entry.friction_minutes)
        if spent + cost > minutes_available:
            continue
        spent += cost
        chosen.append(entry.contest_id)
        chances.append(entry.chance_ppm)
        updated = portfolio_ppm(chances)
        marginal.append(updated - running)
        running = updated
    return chosen, round(spent, 1), marginal


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
        locality=locality_score(
            assessment.prize_delivery,
            assessment.ships_to_germany,
            assessment.locality_fit,
        ),
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

    attempts = entries_before_deadline(
        assessment.entry_cadence, assessment.corrected_deadline
    )
    effective_chance_ppm = combine_ppm(chance_likely_ppm, attempts)
    # Repetition does not change the rate, only the volume you can buy at
    # that rate, so EV per minute stays a single-entry figure.
    ev_cents_per_minute = round(
        (chance_likely_ppm / 1_000_000)
        * assessment.prize_value_eur
        * 100
        / max(0.5, assessment.friction_minutes)
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
        prize_delivery=assessment.prize_delivery,
        prize_value_eur=assessment.prize_value_eur,
        entry_cadence=assessment.entry_cadence,
        entries_before_deadline=attempts,
        effective_chance_ppm=effective_chance_ppm,
        ev_cents_per_minute=ev_cents_per_minute,
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
