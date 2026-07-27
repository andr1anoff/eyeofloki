from datetime import date
from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    HttpUrl,
    field_validator,
    model_validator,
)


CompetitionLevel = Literal["Low", "Medium", "High", "Very high"]
ConfidenceLevel = Literal["Low", "Medium", "High"]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ContestInput(StrictModel):
    id: int
    slug: str
    title: str
    organizer: str
    prize: str
    url: HttpUrl
    deadline: str
    winners: int = Field(default=1, ge=1, le=100_000)
    locality: str = "Germany"
    eligibility: str = "Needs review"
    entry_method: str = "Needs review"
    known_registration_required: bool = False


class UserProfile(StrictModel):
    home_city: str = "Berlin"
    country: str = "Germany"
    adult: bool = True
    preferred_prizes: list[str] = Field(
        default_factory=lambda: [
            "cinema tickets",
            "concerts",
            "Berlin experiences",
            "travel",
            "useful technology",
        ],
        max_length=20,
    )
    avoid_prizes: list[str] = Field(
        default_factory=lambda: [
            "gardening and garden furniture",
            "cruises and coach tours",
            "spa, wellness and beauty",
            "kitchen and household appliances",
            "craft, knitting and hobby kits",
            "health supplements and medical devices",
            "children's and baby products",
            "insurance, banking and utility signups",
        ],
        max_length=20,
    )
    friction_penalties: list[str] = Field(
        default_factory=lambda: [
            "mandatory account",
            "mandatory newsletter",
            "purchase requirement",
            "social sharing",
        ],
        max_length=20,
    )
    max_entry_minutes: int = Field(default=5, ge=1, le=60)


class ReconRequest(StrictModel):
    contests: list[ContestInput] = Field(min_length=1, max_length=12)
    profile: UserProfile = Field(default_factory=UserProfile)


class DiscoveryRequest(StrictModel):
    known_urls: list[HttpUrl] = Field(default_factory=list, max_length=1_000)
    known_titles: list[str] = Field(default_factory=list, max_length=1_000)
    round: int = Field(default=0, ge=0, le=1_000_000)
    limit: int = Field(default=12, ge=1, le=20)
    profile: UserProfile = Field(default_factory=UserProfile)


class PageEvidence(StrictModel):
    contest_id: int
    final_url: str
    status_code: int
    reachable: bool
    title: str
    excerpt: str
    entry_signals: list[str]
    registration_signals: list[str]
    hub_signals: list[str] = Field(default_factory=list)
    hub_score: int = Field(default=0, ge=0, le=100)


class ModelAssessment(StrictModel):
    contest_id: int
    active: bool
    entry_mechanism_found: bool
    registration_required: bool
    newsletter_required: bool
    corrected_deadline: str = Field(
        description="Exact calendar date in YYYY-MM-DD format"
    )
    corrected_winners: int = Field(ge=1, le=100_000)
    entrants_low: int = Field(ge=1, le=100_000_000)
    entrants_likely: int = Field(ge=1, le=100_000_000)
    entrants_high: int = Field(ge=1, le=100_000_000)
    competition: CompetitionLevel
    confidence: ConfidenceLevel
    prize_utility: int = Field(ge=0, le=100)
    legitimacy: int = Field(ge=0, le=100)
    locality_fit: int = Field(ge=0, le=100)
    friction_minutes: float = Field(ge=0, le=240)
    summary: str = Field(min_length=1, max_length=420)
    reasons: list[str] = Field(min_length=2, max_length=4)
    evidence_urls: list[str] = Field(min_length=1, max_length=6)
    blocking_reason: str

    @field_validator("corrected_deadline", mode="before")
    @classmethod
    def deadline_is_iso_date(cls, value: object) -> str:
        if not isinstance(value, str):
            raise ValueError("deadline must be an ISO date")
        candidate = value.strip()[:10]
        date.fromisoformat(candidate)
        return candidate

    @model_validator(mode="after")
    def entrants_are_ordered(self) -> "ModelAssessment":
        ordered = sorted(
            [self.entrants_low, self.entrants_likely, self.entrants_high]
        )
        self.entrants_low, self.entrants_likely, self.entrants_high = ordered
        return self


class AssessmentBundle(StrictModel):
    assessments: list[ModelAssessment]


class DiscoveryAssessment(StrictModel):
    candidate_id: int
    is_aggregator: bool = False
    title: str = Field(min_length=3, max_length=240)
    organizer: str = Field(min_length=2, max_length=180)
    prize: str = Field(min_length=2, max_length=320)
    locality: str = Field(min_length=2, max_length=120)
    eligibility: str = Field(min_length=2, max_length=420)
    entry_method: str = Field(min_length=2, max_length=420)
    active: bool
    free_entry: bool
    germany_eligible: bool
    entry_mechanism_found: bool
    registration_required: bool
    newsletter_required: bool
    corrected_deadline: str = Field(
        description="Exact calendar date in YYYY-MM-DD format"
    )
    corrected_winners: int = Field(ge=1, le=100_000)
    entrants_low: int = Field(ge=1, le=100_000_000)
    entrants_likely: int = Field(ge=1, le=100_000_000)
    entrants_high: int = Field(ge=1, le=100_000_000)
    competition: CompetitionLevel
    confidence: ConfidenceLevel
    prize_utility: int = Field(ge=0, le=100)
    legitimacy: int = Field(ge=0, le=100)
    locality_fit: int = Field(ge=0, le=100)
    friction_minutes: float = Field(ge=0, le=240)
    summary: str = Field(min_length=1, max_length=420)
    reasons: list[str] = Field(min_length=2, max_length=4)
    evidence_urls: list[str] = Field(min_length=1, max_length=6)
    blocking_reason: str

    @field_validator("corrected_deadline", mode="before")
    @classmethod
    def deadline_is_iso_date(cls, value: object) -> str:
        if not isinstance(value, str):
            raise ValueError("deadline must be an ISO date")
        candidate = value.strip()[:10]
        date.fromisoformat(candidate)
        return candidate

    @model_validator(mode="after")
    def entrants_are_ordered(self) -> "DiscoveryAssessment":
        ordered = sorted(
            [self.entrants_low, self.entrants_likely, self.entrants_high]
        )
        self.entrants_low, self.entrants_likely, self.entrants_high = ordered
        return self


class DiscoveryAssessmentBundle(StrictModel):
    assessments: list[DiscoveryAssessment]


class ScoreBreakdown(StrictModel):
    chance: int
    prize: int
    friction: int
    legitimacy: int
    locality: int
    urgency: int


class ContestAnalysis(StrictModel):
    contest_id: int
    score: int = Field(ge=0, le=100)
    status: Literal["NEW", "READY", "BLOCKED"]
    verdict: str
    competition: CompetitionLevel
    confidence: ConfidenceLevel
    entrants_low: int
    entrants_likely: int
    entrants_high: int
    chance_low_ppm: int
    chance_likely_ppm: int
    chance_high_ppm: int
    crowd: str = "Unknown"
    friction_minutes: float
    registration_required: bool
    newsletter_required: bool
    deadline: str
    winners: int
    summary: str
    reasons: list[str]
    evidence_urls: list[str]
    verification: str
    score_breakdown: ScoreBreakdown
    analysis_method: str = "llm-estimate+deterministic-score-v5"
    analyzed_at: str


class ReconResponse(StrictModel):
    analyses: list[ContestAnalysis]
    model: str
    analyzed_at: str


class DiscoveryItem(StrictModel):
    slug: str
    title: str
    organizer: str
    prize: str
    url: str
    locality: str
    eligibility: str
    entry_method: str
    analysis: ContestAnalysis


class RejectionNote(StrictModel):
    """Why one candidate that already cost a Gemini call was dropped.
    Feeds DISCOVERY_BLOCKED_HOSTS: hosts that never convert."""

    host: str
    url: str
    title: str
    reason: str


class DiscoveryResponse(StrictModel):
    discoveries: list[DiscoveryItem]
    searched_queries: int
    raw_candidates: int
    novel_candidates: int
    analyzed_candidates: int
    rejected_candidates: int
    truncated_candidates: int = 0
    rejections: list[RejectionNote] = Field(default_factory=list)
    search_errors: int
    round: int
    model: str
    analyzed_at: str
