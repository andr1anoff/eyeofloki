export type ContestStatus =
  | "NEW"
  | "READY"
  | "ENTERED"
  | "BLOCKED"
  | "SKIPPED";

export type CompetitionLevel = "Low" | "Medium" | "High" | "Very high";
export type ConfidenceLevel = "Low" | "Medium" | "High";

export type ScoreBreakdown = {
  chance: number;
  prize: number;
  friction: number;
  legitimacy: number;
  locality: number;
  urgency: number;
};

export type Contest = {
  id: number;
  slug: string;
  title: string;
  organizer: string;
  prize: string;
  description: string;
  score: number;
  status: ContestStatus;
  competition: CompetitionLevel;
  deadline: string;
  eligibility: string;
  entryMethod: string;
  friction: string;
  winners: number;
  locality: string;
  url: string;
  musicUrl: string | null;
  verdict: string;
  reasons: string;
  verification: string;
  registrationRequired: boolean;
  newsletterRequired: boolean;
  entrantsLow: number;
  entrantsLikely: number;
  entrantsHigh: number;
  chanceLowPpm: number;
  chanceLikelyPpm: number;
  chanceHighPpm: number;
  confidence: ConfidenceLevel;
  frictionMinutes: number;
  scoreBreakdown: string;
  evidenceUrls: string;
  analysisMethod: string;
  enteredAt: string | null;
  lastCheckedAt: string | null;
  createdAt?: string;
};

export type SeedContest = Omit<Contest, "id" | "createdAt">;

function chancePpm(winners: number, entrants: number) {
  return Math.round(Math.min(1, winners / Math.max(1, entrants)) * 1_000_000);
}

function seedIntel(
  winners: number,
  entrantsLow: number,
  entrantsLikely: number,
  entrantsHigh: number,
  confidence: ConfidenceLevel,
  scoreBreakdown: ScoreBreakdown,
  evidenceUrls: string[],
) {
  return {
    newsletterRequired: false,
    entrantsLow,
    entrantsLikely,
    entrantsHigh,
    chanceLowPpm: chancePpm(winners, entrantsHigh),
    chanceLikelyPpm: chancePpm(winners, entrantsLikely),
    chanceHighPpm: chancePpm(winners, entrantsLow),
    confidence,
    frictionMinutes: 1,
    scoreBreakdown: JSON.stringify(scoreBreakdown),
    evidenceUrls: JSON.stringify(evidenceUrls),
    analysisMethod: "heuristic-v1",
  };
}

export const seedContests: SeedContest[] = [
  {
    slug: "berliner-kindl-tierpark",
    title: "Midnight with the elephants",
    organizer: "Berliner Kindl × Tierpark Berlin",
    prize: "20 × two places on an exclusive after-hours elephant tour",
    description:
      "A genuinely local prize with twenty winners and a very short entry path. Newsletter opt-in is optional and doubles the stated chance.",
    score: 91,
    status: "READY",
    competition: "Low",
    deadline: "2026-08-09",
    eligibility: "18+ · Berlin or Brandenburg",
    entryMethod: "Short form + one elephant question",
    friction: "≈ 45 sec",
    winners: 20,
    locality: "Berlin",
    url: "https://www.berliner-kindl.de/gewinnspiel/tierpark/",
    musicUrl: null,
    verdict: "Enter now",
    reasons: JSON.stringify([
      "Local eligibility sharply reduces the field",
      "Twenty winning pairs instead of one grand prize",
      "No purchase and no account required",
    ]),
    verification: "Entry form and eligibility were found on the live page.",
    registrationRequired: false,
    ...seedIntel(
      20,
      800,
      1800,
      4000,
      "Medium",
      {
        chance: 61,
        prize: 82,
        friction: 94,
        legitimacy: 96,
        locality: 100,
        urgency: 45,
      },
      ["https://www.berliner-kindl.de/gewinnspiel/tierpark/"],
    ),
    enteredAt: null,
    lastCheckedAt: null,
  },
  {
    slug: "musikfest-berlin-2026",
    title: "A night at Musikfest Berlin",
    organizer: "Berliner Festspiele",
    prize: "2 × 2 tickets for a Musikfest Berlin concert",
    description:
      "A reputable Berlin institution, a city-sized audience, and multiple ticket pairs. Better odds than a national electronics giveaway.",
    score: 84,
    status: "READY",
    competition: "Medium",
    deadline: "2026-08-14",
    eligibility: "18+ · resident of Germany",
    entryMethod: "Festival entry form",
    friction: "≈ 1 min",
    winners: 2,
    locality: "Berlin",
    url: "https://www.berlinerfestspiele.de/en/musikfest-berlin/programm/2026/gewinnspiel",
    musicUrl: null,
    verdict: "Worth the minute",
    reasons: JSON.stringify([
      "Berlin-local cultural audience",
      "Two winning pairs",
      "Trusted organizer and straightforward prize",
    ]),
    verification: "Contest page names the prize, deadline and entry route.",
    registrationRequired: false,
    ...seedIntel(
      2,
      600,
      1400,
      3000,
      "Low",
      {
        chance: 43,
        prize: 76,
        friction: 92,
        legitimacy: 98,
        locality: 100,
        urgency: 45,
      },
      [
        "https://www.berlinerfestspiele.de/en/musikfest-berlin/programm/2026/gewinnspiel",
      ],
    ),
    enteredAt: null,
    lastCheckedAt: null,
  },
  {
    slug: "moviebreak-spider-man",
    title: "Spider-Man: Brand New Day fan pack",
    organizer: "Moviebreak × Sony Pictures Germany",
    prize: "2 × fan packs with two tickets, laptop sleeve, tote and A1 poster",
    description:
      "Email entry is valid, so no site account is needed. A slightly thoughtful answer is enough; your final draft is already prepared.",
    score: 81,
    status: "ENTERED",
    competition: "Medium",
    deadline: "2026-07-29",
    eligibility: "Adult resident of Germany",
    entryMethod: "Email with three favorite Spider-Man films",
    friction: "Done",
    winners: 2,
    locality: "Germany",
    url: "https://www.moviebreak.de/gewinnspiele/spider-man-brand-new-day-startet-in-kuerze-in-unseren-kinos-wir-verlosen-passende-fanpakete-inklusive-freikarten",
    musicUrl: null,
    verdict: "Entered",
    reasons: JSON.stringify([
      "Email path avoids registration",
      "Two complete prize packs",
      "Personal answer improves answer quality without gaming the rules",
    ]),
    verification: "Email entry and the 29 July deadline were visible.",
    registrationRequired: false,
    ...seedIntel(
      2,
      1000,
      2500,
      7000,
      "Low",
      {
        chance: 38,
        prize: 74,
        friction: 100,
        legitimacy: 82,
        locality: 55,
        urgency: 100,
      },
      [
        "https://www.moviebreak.de/gewinnspiele/spider-man-brand-new-day-startet-in-kuerze-in-unseren-kinos-wir-verlosen-passende-fanpakete-inklusive-freikarten",
      ],
    ),
    enteredAt: "2026-07-27T16:10:00.000Z",
    lastCheckedAt: null,
  },
  {
    slug: "atu-spider-man-new-york",
    title: "Spider-Man trip to New York",
    organizer: "ATU × Sony Pictures Germany",
    prize: "Six-day New York trip for two + 200 cinema vouchers",
    description:
      "The grand prize attracts a national crowd, but two hundred consolation prizes rescue the expected value. The form is quick.",
    score: 68,
    status: "READY",
    competition: "Very high",
    deadline: "2026-07-31",
    eligibility: "18+ · resident of Germany",
    entryMethod: "Free form · newsletter optional",
    friction: "≈ 1 min",
    winners: 201,
    locality: "Germany",
    url: "https://www.atu.de/pages/gewinnspiel/spiderman-gewinnspiel.html",
    musicUrl: null,
    verdict: "Enter for the prize depth",
    reasons: JSON.stringify([
      "Two hundred cinema-voucher winners",
      "No purchase required",
      "High competition, but almost no time cost",
    ]),
    verification: "Live entry form found; newsletter is not mandatory.",
    registrationRequired: false,
    ...seedIntel(
      201,
      50_000,
      180_000,
      450_000,
      "Medium",
      {
        chance: 41,
        prize: 96,
        friction: 92,
        legitimacy: 96,
        locality: 55,
        urgency: 82,
      },
      ["https://www.atu.de/pages/gewinnspiel/spiderman-gewinnspiel.html"],
    ),
    enteredAt: null,
    lastCheckedAt: null,
  },
  {
    slug: "fluxfm-angus-julia-stone",
    title: "Angus & Julia Stone on a Berlin rooftop",
    organizer: "FluxFM",
    prize: "Guest-list places for two · live set, interview and Q&A",
    description:
      "A niche, local experience with plausible odds. The account wall costs points, but the prize is distinctive enough to keep in the queue.",
    score: 56,
    status: "NEW",
    competition: "Low",
    deadline: "2026-08-03",
    eligibility: "18+ · able to attend in Berlin",
    entryMethod: "FluxFM account + favorite song",
    friction: "≈ 4 min",
    winners: 1,
    locality: "Berlin",
    url: "https://www.fluxfm.de/p/Angus-and-Julia-Stone-LIVE-bei-Flux-On-Top-3-am-4-August-2026-2E7UIF5AgVx3958JWApqmn",
    musicUrl: "https://open.spotify.com/track/5BPCB94pliDESq5PdqFYc7",
    verdict: "Listen, then decide",
    reasons: JSON.stringify([
      "Tiny Berlin-specific audience",
      "Unusual experience, not a commodity prize",
      "Registration penalty: −18 Loki points",
    ]),
    verification: "Form exists, but submission requires a FluxFM login.",
    registrationRequired: true,
    ...seedIntel(
      1,
      120,
      350,
      900,
      "Low",
      {
        chance: 49,
        prize: 70,
        friction: 42,
        legitimacy: 94,
        locality: 100,
        urgency: 64,
      },
      [
        "https://www.fluxfm.de/p/Angus-and-Julia-Stone-LIVE-bei-Flux-On-Top-3-am-4-August-2026-2E7UIF5AgVx3958JWApqmn",
      ],
    ),
    frictionMinutes: 4,
    enteredAt: null,
    lastCheckedAt: null,
  },
  {
    slug: "disneycentral-spider-man",
    title: "Spider-Man cinema package",
    organizer: "DisneyCentral Fan-HQ",
    prize: "Cinema tickets and Spider-Man merchandise",
    description:
      "Legitimate, but the Fan-HQ account and newsletter make it a mediocre use of time unless the prize is especially attractive to you.",
    score: 43,
    status: "NEW",
    competition: "High",
    deadline: "2026-08-02",
    eligibility: "Adult resident of Germany",
    entryMethod: "Fan-HQ account + newsletter + quiz",
    friction: "≈ 5 min",
    winners: 1,
    locality: "Germany",
    url: "https://www.disneycentral.de/marvel/filme/spider-man-brand-new-day-gewinnspiel/",
    musicUrl: null,
    verdict: "Low priority",
    reasons: JSON.stringify([
      "Account and newsletter required",
      "National fandom audience",
      "Single prize package",
    ]),
    verification: "Contest is live; registration and newsletter are mandatory.",
    registrationRequired: true,
    ...seedIntel(
      1,
      1500,
      6000,
      20_000,
      "Low",
      {
        chance: 25,
        prize: 58,
        friction: 30,
        legitimacy: 72,
        locality: 55,
        urgency: 64,
      },
      [
        "https://www.disneycentral.de/marvel/filme/spider-man-brand-new-day-gewinnspiel/",
      ],
    ),
    newsletterRequired: true,
    frictionMinutes: 5,
    enteredAt: null,
    lastCheckedAt: null,
  },
  {
    slug: "lollapalooza-terms-only",
    title: "Lollapalooza Berlin ticket quiz",
    organizer: "Lollapalooza Berlin",
    prize: "Festival tickets",
    description:
      "The rules mention a quiz, but the current page exposes no usable entry mechanism. Eye of Loki refuses to send you into a dead end.",
    score: 0,
    status: "BLOCKED",
    competition: "Very high",
    deadline: "2026-07-28",
    eligibility: "Unclear",
    entryMethod: "Missing",
    friction: "Impossible",
    winners: 1,
    locality: "Berlin",
    url: "https://www.lollapaloozade.com/en/gewinnspiele",
    musicUrl: null,
    verdict: "Blocked: terms are not an entry form",
    reasons: JSON.stringify([
      "No quiz or submission control found",
      "Page has already moved toward the 2027 edition",
      "Rules alone do not prove a contest is enterable",
    ]),
    verification: "Blocked after manual review: entry mechanism is absent.",
    registrationRequired: false,
    newsletterRequired: false,
    entrantsLow: 0,
    entrantsLikely: 0,
    entrantsHigh: 0,
    chanceLowPpm: 0,
    chanceLikelyPpm: 0,
    chanceHighPpm: 0,
    confidence: "High",
    frictionMinutes: 0,
    scoreBreakdown: JSON.stringify({
      chance: 0,
      prize: 0,
      friction: 0,
      legitimacy: 0,
      locality: 0,
      urgency: 0,
    }),
    evidenceUrls: JSON.stringify([
      "https://www.lollapaloozade.com/en/gewinnspiele",
    ]),
    analysisMethod: "manual-block-v1",
    enteredAt: null,
    lastCheckedAt: null,
  },
];

export function parseReasons(reasons: string): string[] {
  try {
    const parsed = JSON.parse(reasons);
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

export function parseEvidence(evidence: string): string[] {
  return parseReasons(evidence);
}

export function parseBreakdown(value: string): ScoreBreakdown {
  const fallback: ScoreBreakdown = {
    chance: 0,
    prize: 0,
    friction: 0,
    legitimacy: 0,
    locality: 0,
    urgency: 0,
  };
  try {
    const parsed = JSON.parse(value) as Partial<ScoreBreakdown>;
    return { ...fallback, ...parsed };
  } catch {
    return fallback;
  }
}
