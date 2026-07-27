import {
  type CompetitionLevel,
  type ConfidenceLevel,
  type Contest,
  type ContestStatus,
} from "./contests";

const CONTEST_STATUSES = new Set<ContestStatus>([
  "NEW",
  "READY",
  "ENTERED",
  "BLOCKED",
  "SKIPPED",
]);
const COMPETITION_LEVELS = new Set<CompetitionLevel>([
  "Low",
  "Medium",
  "High",
  "Very high",
]);
const CONFIDENCE_LEVELS = new Set<ConfidenceLevel>([
  "Low",
  "Medium",
  "High",
]);

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function text(value: unknown, fallback: string) {
  return typeof value === "string" && value.trim() ? value.trim() : fallback;
}

function nullableText(value: unknown, fallback: string | null) {
  return value === null
    ? null
    : typeof value === "string"
      ? value
      : fallback;
}

function numberInRange(
  value: unknown,
  fallback: number,
  minimum: number,
  maximum: number,
) {
  const numeric = typeof value === "number" ? value : Number(value);
  if (!Number.isFinite(numeric)) return fallback;
  return Math.min(maximum, Math.max(minimum, numeric));
}

function boolean(value: unknown, fallback: boolean) {
  return typeof value === "boolean" ? value : fallback;
}

function jsonString(value: unknown, fallback: string) {
  if (typeof value === "string") {
    try {
      JSON.parse(value);
      return value;
    } catch {
      return fallback;
    }
  }
  if (Array.isArray(value) || isRecord(value)) {
    try {
      return JSON.stringify(value);
    } catch {
      return fallback;
    }
  }
  return fallback;
}

export function normalizeIsoDate(value: unknown): string | null {
  if (typeof value !== "string") return null;
  const match = value.trim().match(/^(\d{4})-(\d{2})-(\d{2})/);
  if (!match) return null;

  const year = Number(match[1]);
  const month = Number(match[2]);
  const day = Number(match[3]);
  const candidate = new Date(Date.UTC(year, month - 1, day));
  if (
    candidate.getUTCFullYear() !== year ||
    candidate.getUTCMonth() !== month - 1 ||
    candidate.getUTCDate() !== day
  ) {
    return null;
  }
  return `${match[1]}-${match[2]}-${match[3]}`;
}

export function safeTimestamp(value: unknown) {
  if (typeof value !== "string") return 0;
  const timestamp = Date.parse(value);
  return Number.isFinite(timestamp) ? timestamp : 0;
}

export function sanitizeContest(
  value: unknown,
  fallback?: Contest,
): Contest | null {
  if (!isRecord(value)) return fallback ?? null;

  const id = Math.trunc(numberInRange(value.id, fallback?.id ?? 0, -9e15, 9e15));
  const slug = text(value.slug, fallback?.slug ?? `recovered-${Math.abs(id)}`);
  if (!id || !slug) return fallback ?? null;

  const status = CONTEST_STATUSES.has(value.status as ContestStatus)
    ? (value.status as ContestStatus)
    : (fallback?.status ?? "NEW");
  const competition = COMPETITION_LEVELS.has(
    value.competition as CompetitionLevel,
  )
    ? (value.competition as CompetitionLevel)
    : (fallback?.competition ?? "High");
  const confidence = CONFIDENCE_LEVELS.has(
    value.confidence as ConfidenceLevel,
  )
    ? (value.confidence as ConfidenceLevel)
    : (fallback?.confidence ?? "Low");

  return {
    id,
    slug,
    title: text(value.title, fallback?.title ?? "Recovered contest"),
    organizer: text(value.organizer, fallback?.organizer ?? "Unknown organizer"),
    prize: text(value.prize, fallback?.prize ?? "Prize needs review"),
    description: text(
      value.description,
      fallback?.description ?? "Recon data needs review.",
    ),
    score: Math.round(numberInRange(value.score, fallback?.score ?? 0, 0, 100)),
    status,
    competition,
    deadline:
      normalizeIsoDate(value.deadline) ??
      normalizeIsoDate(fallback?.deadline) ??
      "2099-12-31",
    eligibility: text(
      value.eligibility,
      fallback?.eligibility ?? "Needs review",
    ),
    entryMethod: text(
      value.entryMethod,
      fallback?.entryMethod ?? "Needs review",
    ),
    friction: text(value.friction, fallback?.friction ?? "Unknown"),
    winners: Math.round(
      numberInRange(value.winners, fallback?.winners ?? 1, 1, 100_000),
    ),
    locality: text(value.locality, fallback?.locality ?? "Germany"),
    url: text(value.url, fallback?.url ?? "https://example.com"),
    musicUrl: nullableText(value.musicUrl, fallback?.musicUrl ?? null),
    verdict: text(
      value.verdict,
      fallback?.verdict ?? "Needs reconnaissance",
    ),
    reasons: jsonString(value.reasons, fallback?.reasons ?? "[]"),
    verification: text(
      value.verification,
      fallback?.verification ?? "Recovered from incomplete recon data.",
    ),
    registrationRequired: boolean(
      value.registrationRequired,
      fallback?.registrationRequired ?? false,
    ),
    newsletterRequired: boolean(
      value.newsletterRequired,
      fallback?.newsletterRequired ?? false,
    ),
    entrantsLow: Math.round(
      numberInRange(value.entrantsLow, fallback?.entrantsLow ?? 0, 0, 100_000_000),
    ),
    entrantsLikely: Math.round(
      numberInRange(
        value.entrantsLikely,
        fallback?.entrantsLikely ?? 0,
        0,
        100_000_000,
      ),
    ),
    entrantsHigh: Math.round(
      numberInRange(
        value.entrantsHigh,
        fallback?.entrantsHigh ?? 0,
        0,
        100_000_000,
      ),
    ),
    chanceLowPpm: Math.round(
      numberInRange(
        value.chanceLowPpm,
        fallback?.chanceLowPpm ?? 0,
        0,
        1_000_000,
      ),
    ),
    chanceLikelyPpm: Math.round(
      numberInRange(
        value.chanceLikelyPpm,
        fallback?.chanceLikelyPpm ?? 0,
        0,
        1_000_000,
      ),
    ),
    chanceHighPpm: Math.round(
      numberInRange(
        value.chanceHighPpm,
        fallback?.chanceHighPpm ?? 0,
        0,
        1_000_000,
      ),
    ),
    confidence,
    frictionMinutes: numberInRange(
      value.frictionMinutes,
      fallback?.frictionMinutes ?? 0,
      0,
      240,
    ),
    scoreBreakdown: jsonString(
      value.scoreBreakdown,
      fallback?.scoreBreakdown ?? "{}",
    ),
    evidenceUrls: jsonString(
      value.evidenceUrls,
      fallback?.evidenceUrls ?? "[]",
    ),
    analysisMethod: text(
      value.analysisMethod,
      fallback?.analysisMethod ?? "recovered",
    ),
    enteredAt: nullableText(value.enteredAt, fallback?.enteredAt ?? null),
    lastCheckedAt: nullableText(
      value.lastCheckedAt,
      fallback?.lastCheckedAt ?? null,
    ),
    createdAt:
      typeof value.createdAt === "string"
        ? value.createdAt
        : fallback?.createdAt,
  };
}

export function sanitizeContestList(
  value: unknown,
  fallbacks: Contest[],
): Contest[] {
  if (!Array.isArray(value)) return [];
  const fallbackBySlug = new Map(
    fallbacks.map((contest) => [contest.slug, contest]),
  );
  return value
    .map((candidate) => {
      const slug =
        isRecord(candidate) && typeof candidate.slug === "string"
          ? candidate.slug
          : "";
      return sanitizeContest(candidate, fallbackBySlug.get(slug));
    })
    .filter((contest): contest is Contest => Boolean(contest));
}
