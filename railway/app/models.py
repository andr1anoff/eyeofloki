from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, model_validator


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


class PageEvidence(StrictModel):
    contest_id: int
    final_url: str
    status_code: int
    reachable: bool
    title: str
    excerpt: str
    entry_signals: list[str]
    registration_signals: list[str]


class ModelAssessment(StrictModel):
    contest_id: int
    active: bool
    entry_mechanism_found: bool
    registration_required: bool
    newsletter_required: bool
    corrected_deadline: str
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

    @model_validator(mode="after")
    def entrants_are_ordered(self) -> "ModelAssessment":
        ordered = sorted(
            [self.entrants_low, self.entrants_likely, self.entrants_high]
        )
        self.entrants_low, self.entrants_likely, self.entrants_high = ordered
        return self


class AssessmentBundle(StrictModel):
    assessments: list[ModelAssessment]


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
    analysis_method: str = "llm-estimate+deterministic-score-v2"
    analyzed_at: str


class ReconResponse(StrictModel):
    analyses: list[ContestAnalysis]
    model: str
    analyzed_at: str
