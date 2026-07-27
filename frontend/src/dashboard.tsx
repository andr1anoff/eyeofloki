"use client";

import { useEffect, useMemo, useState } from "react";
import { EyeOfLokiLogo, LokiMark } from "./logo";
import {
  parseBreakdown,
  parseEvidence,
  parseReasons,
  seedContests,
  type Contest,
  type ContestStatus,
} from "./lib/contests";
import {
  normalizeIsoDate,
  sanitizeContest,
  sanitizeContestList,
} from "./lib/contest-safety";

type Filter = "TODAY" | "READY" | "ENTERED" | "BLOCKED" | "ALL";
type ConnectionState = "unknown" | "connected" | "offline";
type ReconNotice = {
  kind: "working" | "success" | "error";
  message: string;
};

type RailwayConfig = {
  url: string;
  secret: string;
};

type LokiBackup = {
  version: 1;
  exported_at: string;
  contests: Contest[];
  railway: RailwayConfig;
  discovery_round: number;
  recon_notice: ReconNotice | null;
};

type ReconAnalysis = {
  contest_id: number;
  score: number;
  status: "NEW" | "READY" | "BLOCKED";
  verdict: string;
  competition: Contest["competition"];
  confidence: Contest["confidence"];
  entrants_low: number;
  entrants_likely: number;
  entrants_high: number;
  chance_low_ppm: number;
  chance_likely_ppm: number;
  chance_high_ppm: number;
  friction_minutes: number;
  registration_required: boolean;
  newsletter_required: boolean;
  deadline: string;
  winners: number;
  summary: string;
  reasons: string[];
  evidence_urls: string[];
  verification: string;
  score_breakdown: Record<string, number>;
  analysis_method: string;
  analyzed_at: string;
};

type DiscoveryItem = {
  slug: string;
  title: string;
  organizer: string;
  prize: string;
  url: string;
  locality: string;
  eligibility: string;
  entry_method: string;
  analysis: ReconAnalysis;
};

type DiscoveryResponse = {
  discoveries?: DiscoveryItem[];
  searched_queries?: number;
  raw_candidates?: number;
  novel_candidates?: number;
  analyzed_candidates?: number;
  rejected_candidates?: number;
  search_errors?: number;
  round?: number;
  model?: string;
  analyzed_at?: string;
  detail?: string;
};

const FALLBACK_CONTESTS: Contest[] = seedContests.map((contest, index) => ({
  ...contest,
  id: index + 1,
}));

const PROFILE = {
  home_city: "Berlin",
  country: "Germany",
  adult: true,
  ships_to: "Germany",
  reachable_for_events: "Berlin and Brandenburg",
  preferred_prizes: [
    "cinema tickets",
    "concerts",
    "Berlin experiences",
    "travel",
    "useful technology",
  ],
  friction_penalties: [
    "mandatory account",
    "mandatory newsletter",
    "purchase requirement",
    "social sharing",
  ],
  max_entry_minutes: 5,
};

function Icon({
  name,
  size = 18,
}: {
  name:
    | "arrow"
    | "check"
    | "clock"
    | "download"
    | "external"
    | "link"
    | "menu"
    | "radar"
    | "server"
    | "settings"
    | "skip"
    | "spark"
    | "upload"
    | "x";
  size?: number;
}) {
  const paths = {
    arrow: <path d="m9 18 6-6-6-6" />,
    check: <path d="m5 12 4 4L19 6" />,
    clock: (
      <>
        <circle cx="12" cy="12" r="8" />
        <path d="M12 7v5l3 2" />
      </>
    ),
    download: (
      <>
        <path d="M12 4v11" />
        <path d="m8 11 4 4 4-4" />
        <path d="M5 19h14" />
      </>
    ),
    external: (
      <>
        <path d="M14 5h5v5" />
        <path d="m10 14 9-9" />
        <path d="M19 14v5H5V5h5" />
      </>
    ),
    link: (
      <>
        <path d="M10 13a5 5 0 0 0 7.5.5l2-2a5 5 0 0 0-7-7l-1 1" />
        <path d="M14 11a5 5 0 0 0-7.5-.5l-2 2a5 5 0 0 0 7 7l1-1" />
      </>
    ),
    menu: <path d="M5 7h14M5 12h14M5 17h14" />,
    radar: (
      <>
        <circle cx="12" cy="12" r="8" />
        <circle cx="12" cy="12" r="3" />
        <path d="m12 12 5-5" />
      </>
    ),
    server: (
      <>
        <rect x="4" y="4" width="16" height="6" rx="2" />
        <rect x="4" y="14" width="16" height="6" rx="2" />
        <path d="M8 7h.01M8 17h.01" />
      </>
    ),
    settings: (
      <>
        <circle cx="12" cy="12" r="3" />
        <path d="M19 12a7 7 0 0 0-.1-1l2-1.5-2-3.4-2.4 1a7 7 0 0 0-1.7-1L14.5 3h-5l-.4 3.1a7 7 0 0 0-1.7 1L5 6.1 3 9.5 5.1 11a7 7 0 0 0 0 2L3 14.5 5 18l2.4-1a7 7 0 0 0 1.7 1l.4 3h5l.4-3a7 7 0 0 0 1.7-1l2.4 1 2-3.5-2.1-1.5c.1-.3.1-.7.1-1Z" />
      </>
    ),
    skip: <path d="m5 8 7 4-7 4V8Zm9 0 5 4-5 4V8Z" />,
    spark: <path d="m12 3 1.5 5.5L19 10l-5.5 1.5L12 17l-1.5-5.5L5 10l5.5-1.5L12 3Z" />,
    upload: (
      <>
        <path d="M12 20V9" />
        <path d="m8 13 4-4 4 4" />
        <path d="M5 5h14" />
      </>
    ),
    x: <path d="m7 7 10 10M17 7 7 17" />,
  };
  return (
    <svg
      aria-hidden="true"
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      {paths[name]}
    </svg>
  );
}

function formatDeadline(date: string) {
  const normalized = normalizeIsoDate(date);
  if (!normalized) return "Needs review";
  return new Intl.DateTimeFormat("en-GB", {
    day: "numeric",
    month: "short",
    timeZone: "UTC",
  }).format(new Date(`${normalized}T12:00:00Z`));
}

function daysUntil(date: string) {
  const normalized = normalizeIsoDate(date);
  if (!normalized) return null;
  const now = new Date();
  const todayUtc = Date.UTC(
    now.getUTCFullYear(),
    now.getUTCMonth(),
    now.getUTCDate(),
  );
  const [year, month, day] = normalized.split("-").map(Number);
  const deadlineUtc = Date.UTC(year, month - 1, day);
  return Math.max(0, Math.round((deadlineUtc - todayUtc) / 86_400_000));
}

function deadlineCountdown(date: string) {
  const remaining = daysUntil(date);
  if (remaining === null) return "check date";
  return remaining === 0 ? "today" : `${remaining} days`;
}

function formatChance(ppm: number) {
  const percent = ppm / 10_000;
  if (percent === 0) return "—";
  if (percent < 0.01) return `${percent.toFixed(3)}%`;
  if (percent < 1) return `${percent.toFixed(2)}%`;
  return `${percent.toFixed(1)}%`;
}

function chanceRange(contest: Contest) {
  if (!contest.chanceHighPpm) return "Awaiting estimate";
  return `${formatChance(contest.chanceLowPpm)}–${formatChance(
    contest.chanceHighPpm,
  )}`;
}

// Entrant counts are model estimates that are never checked against an
// outcome, so headline odds are shown as a bucket. The exact ppm stays
// available in the detail view, labelled as an estimate.
function crowdLabel(contest: Contest) {
  const ppm = contest.chanceLikelyPpm;
  if (!ppm) return "Crowd unknown";
  if (ppm >= 50_000) return "Few entrants";
  if (ppm >= 10_000) return "Moderate crowd";
  if (ppm >= 1_000) return "Crowded";
  return "Very crowded";
}

function portfolioChance(
  contests: Contest[],
  field: "chanceLowPpm" | "chanceLikelyPpm" | "chanceHighPpm",
) {
  return (
    1 -
    contests.reduce(
      (none, contest) => none * (1 - Math.min(1, contest[field] / 1_000_000)),
      1,
    )
  );
}

function mapAnalysis(contest: Contest, analysis: ReconAnalysis): Contest {
  const mapped = {
    ...contest,
    score: analysis.score,
    status: contest.status === "ENTERED" ? "ENTERED" : analysis.status,
    verdict: analysis.verdict,
    competition: analysis.competition,
    confidence: analysis.confidence,
    entrantsLow: analysis.entrants_low,
    entrantsLikely: analysis.entrants_likely,
    entrantsHigh: analysis.entrants_high,
    chanceLowPpm: analysis.chance_low_ppm,
    chanceLikelyPpm: analysis.chance_likely_ppm,
    chanceHighPpm: analysis.chance_high_ppm,
    frictionMinutes: analysis.friction_minutes,
    friction: `≈ ${Math.max(1, Math.round(analysis.friction_minutes))} min`,
    registrationRequired: analysis.registration_required,
    newsletterRequired: analysis.newsletter_required,
    deadline: normalizeIsoDate(analysis.deadline) ?? contest.deadline,
    winners: analysis.winners,
    description: analysis.summary,
    reasons: JSON.stringify(analysis.reasons),
    evidenceUrls: JSON.stringify(analysis.evidence_urls),
    verification: analysis.verification,
    scoreBreakdown: JSON.stringify(analysis.score_breakdown),
    analysisMethod: analysis.analysis_method,
    lastCheckedAt: analysis.analyzed_at,
  };
  return sanitizeContest(mapped, contest) ?? contest;
}

function mapDiscovery(item: DiscoveryItem, id: number): Contest {
  const base: Contest = {
    id,
    slug: item.slug,
    title: item.title,
    organizer: item.organizer,
    prize: item.prize,
    description: item.analysis.summary,
    score: 0,
    status: "NEW",
    competition: "High",
    deadline: item.analysis.deadline,
    eligibility: item.eligibility,
    entryMethod: item.entry_method,
    friction: "Unknown",
    winners: Math.max(1, item.analysis.winners),
    locality: item.locality,
    url: item.url,
    musicUrl: null,
    verdict: "Needs review",
    reasons: "[]",
    verification: item.analysis.verification,
    registrationRequired: false,
    newsletterRequired: false,
    entrantsLow: 0,
    entrantsLikely: 0,
    entrantsHigh: 0,
    chanceLowPpm: 0,
    chanceLikelyPpm: 0,
    chanceHighPpm: 0,
    confidence: "Low",
    frictionMinutes: 0,
    scoreBreakdown: "{}",
    evidenceUrls: "[]",
    analysisMethod: "discovery-v4",
    enteredAt: null,
    lastCheckedAt: item.analysis.analyzed_at,
  };
  return mapAnalysis(base, item.analysis);
}

function normalizeContestUrl(value: string) {
  try {
    const url = new URL(value);
    url.hash = "";
    url.search = "";
    url.hostname = url.hostname.replace(/^www\./, "").toLowerCase();
    url.pathname = url.pathname.replace(/\/+$/, "") || "/";
    return url.toString().replace(/\/$/, "");
  } catch {
    return value.trim().toLowerCase();
  }
}

export function Dashboard({ displayName }: { displayName: string }) {
  const [contests, setContests] = useState<Contest[]>(FALLBACK_CONTESTS);
  const [filter, setFilter] = useState<Filter>("TODAY");
  const [selectedId, setSelectedId] = useState<number>(FALLBACK_CONTESTS[0].id);
  const [mobileNav, setMobileNav] = useState(false);
  const [detailOpen, setDetailOpen] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [scanning, setScanning] = useState(false);
  const [scanProgress, setScanProgress] = useState(0);
  const [toast, setToast] = useState<string | null>(null);
  const [leadUrl, setLeadUrl] = useState("");
  const [adding, setAdding] = useState(false);
  const [brief, setBrief] = useState("");
  const [hunting, setHunting] = useState(false);
  const [railway, setRailway] = useState<RailwayConfig>({
    url: "",
    secret: "",
  });
  const [connection, setConnection] = useState<ConnectionState>("unknown");
  const [testingConnection, setTestingConnection] = useState(false);
  const [reconNotice, setReconNotice] = useState<ReconNotice | null>(null);
  const [discoveryRound, setDiscoveryRound] = useState(0);

  const berlinNow = new Intl.DateTimeFormat("en-GB", {
    timeZone: "Europe/Berlin",
    weekday: "short",
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  })
    .format(new Date())
    .replace(",", " ·")
    .toUpperCase();

  useEffect(() => {
    let active = true;
    const storedContests = window.localStorage.getItem("eye-of-loki-contests");
    const parsedStored = (() => {
      if (!storedContests) return [] as Contest[];
      try {
        const parsed = sanitizeContestList(
          JSON.parse(storedContests) as unknown,
          FALLBACK_CONTESTS,
        );
        if (!parsed.length) {
          window.localStorage.removeItem("eye-of-loki-contests");
        }
        return parsed;
      } catch {
        window.localStorage.removeItem("eye-of-loki-contests");
        return [] as Contest[];
      }
    })();

    const storedRailway = window.localStorage.getItem("eye-of-loki-railway");
    if (storedRailway) {
      try {
        const parsed = JSON.parse(storedRailway) as RailwayConfig;
        Promise.resolve().then(() => {
          if (!active) return;
          setRailway(parsed);
          setConnection(parsed.url && parsed.secret ? "unknown" : "offline");
        });
      } catch {
        Promise.resolve().then(() => {
          if (active) setConnection("offline");
        });
      }
    } else {
      Promise.resolve().then(() => {
        if (active) setConnection("offline");
      });
    }

    const storedReconNotice = window.localStorage.getItem(
      "eye-of-loki-last-recon",
    );
    if (storedReconNotice) {
      try {
        const parsed = JSON.parse(storedReconNotice) as ReconNotice;
        if (
          ["working", "success", "error"].includes(parsed.kind) &&
          typeof parsed.message === "string"
        ) {
          Promise.resolve().then(() => {
            if (active) setReconNotice(parsed);
          });
        }
      } catch {
        window.localStorage.removeItem("eye-of-loki-last-recon");
      }
    }

    const storedRound = Number(
      window.localStorage.getItem("eye-of-loki-discovery-round"),
    );
    if (Number.isInteger(storedRound) && storedRound >= 0) {
      Promise.resolve().then(() => {
        if (active) setDiscoveryRound(storedRound);
      });
    }

    Promise.resolve().then(() => {
      if (active) {
        setContests(parsedStored.length ? parsedStored : FALLBACK_CONTESTS);
      }
    });

    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    if (!toast) return;
    const timer = window.setTimeout(() => setToast(null), 4800);
    return () => window.clearTimeout(timer);
  }, [toast]);

  useEffect(() => {
    if (!settingsOpen) return;
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") setSettingsOpen(false);
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [settingsOpen]);

  const visible = useMemo(() => {
    if (filter === "ALL") return contests;
    if (filter === "TODAY") {
      return contests.filter((contest) =>
        ["NEW", "READY"].includes(contest.status),
      );
    }
    return contests.filter((contest) => contest.status === filter);
  }, [contests, filter]);

  const selected =
    contests.find((contest) => contest.id === selectedId) ?? visible[0];
  const readyCount = contests.filter((contest) => contest.status === "READY").length;
  const entered = contests.filter((contest) => contest.status === "ENTERED");
  const portfolioLow = portfolioChance(entered, "chanceLowPpm");
  const portfolioLikely = portfolioChance(entered, "chanceLikelyPpm");
  const portfolioHigh = portfolioChance(entered, "chanceHighPpm");

  function persistLocal(next: Contest[]) {
    try {
      window.localStorage.setItem(
        "eye-of-loki-contests",
        JSON.stringify(sanitizeContestList(next, FALLBACK_CONTESTS)),
      );
    } catch {
      setToast("Results are visible, but Safari could not cache them locally.");
    }
  }

  function announceRecon(notice: ReconNotice) {
    setReconNotice(notice);
    try {
      window.localStorage.setItem(
        "eye-of-loki-last-recon",
        JSON.stringify(notice),
      );
    } catch {
      // The notice remains visible for this session.
    }
  }

  function setStatus(id: number, status: ContestStatus) {
    setContests((current) => {
      const updated = current.map((contest) =>
        contest.id === id
          ? {
              ...contest,
              status,
              verdict:
                status === "ENTERED"
                  ? "Entered"
                  : status === "SKIPPED"
                    ? "Skipped"
                    : contest.verdict,
            }
          : contest,
      );
      persistLocal(updated);
      return updated;
    });
    setToast(
      status === "ENTERED"
        ? "Marked as entered. The chance is now in your portfolio."
        : "Moved out of the active queue.",
    );
  }

  async function testRailway(config = railway) {
    if (!config.url) {
      setConnection("offline");
      setToast("Add the Railway service URL first.");
      return false;
    }
    setTestingConnection(true);
    try {
      const response = await fetch(`${config.url.replace(/\/$/, "")}/health`);
      const payload = (await response.json()) as {
        ok?: boolean;
        gemini_configured?: boolean;
        search_configured?: boolean;
        auth_configured?: boolean;
        capabilities?: string[];
      };
      const supportsDiscovery = payload.capabilities?.includes("discovery");
      const healthy =
        response.ok &&
        payload.ok &&
        payload.gemini_configured &&
        payload.search_configured &&
        payload.auth_configured &&
        supportsDiscovery;
      setConnection(healthy ? "connected" : "offline");
      setToast(
        healthy
          ? "Railway discovery, Gemini and Tavily are connected."
          : response.ok && payload.ok && !supportsDiscovery
            ? "Railway is online but needs the v4 discovery update."
            : "Service answered, but one or more secrets are missing.",
      );
      return Boolean(healthy);
    } catch {
      setConnection("offline");
      setToast("Could not reach the Railway service.");
      return false;
    } finally {
      setTestingConnection(false);
    }
  }

  function saveRailway() {
    const clean = {
      url: railway.url.trim().replace(/\/$/, ""),
      secret: railway.secret.trim(),
    };
    setRailway(clean);
    window.localStorage.setItem("eye-of-loki-railway", JSON.stringify(clean));
    setSettingsOpen(false);
    void testRailway(clean);
  }

  function exportBackup() {
    const backup: LokiBackup = {
      version: 1,
      exported_at: new Date().toISOString(),
      contests,
      railway,
      discovery_round: discoveryRound,
      recon_notice: reconNotice,
    };
    const blob = new Blob([JSON.stringify(backup, null, 2)], {
      type: "application/json",
    });
    const href = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = href;
    anchor.download = `eye-of-loki-backup-${new Date()
      .toISOString()
      .slice(0, 10)}.json`;
    document.body.append(anchor);
    anchor.click();
    anchor.remove();
    URL.revokeObjectURL(href);
    setToast("Backup exported. Keep it private: it contains your Railway secret.");
  }

  async function importBackup(file: File) {
    try {
      const parsed = JSON.parse(await file.text()) as Partial<LokiBackup>;
      const importedContests = sanitizeContestList(
        parsed.contests,
        FALLBACK_CONTESTS,
      );
      if (parsed.version !== 1 || !importedContests.length) {
        throw new Error("Unsupported backup");
      }
      const importedRailway: RailwayConfig = {
        url:
          typeof parsed.railway?.url === "string"
            ? parsed.railway.url.trim().replace(/\/$/, "")
            : "",
        secret:
          typeof parsed.railway?.secret === "string"
            ? parsed.railway.secret.trim()
            : "",
      };
      const importedRound =
        Number.isInteger(parsed.discovery_round) &&
        Number(parsed.discovery_round) >= 0
          ? Number(parsed.discovery_round)
          : 0;
      const importedNotice =
        parsed.recon_notice &&
        ["working", "success", "error"].includes(parsed.recon_notice.kind) &&
        typeof parsed.recon_notice.message === "string"
          ? parsed.recon_notice
          : null;

      setContests(importedContests);
      setSelectedId(importedContests[0].id);
      setRailway(importedRailway);
      setDiscoveryRound(importedRound);
      setReconNotice(importedNotice);
      persistLocal(importedContests);
      window.localStorage.setItem(
        "eye-of-loki-railway",
        JSON.stringify(importedRailway),
      );
      window.localStorage.setItem(
        "eye-of-loki-discovery-round",
        String(importedRound),
      );
      if (importedNotice) {
        window.localStorage.setItem(
          "eye-of-loki-last-recon",
          JSON.stringify(importedNotice),
        );
      } else {
        window.localStorage.removeItem("eye-of-loki-last-recon");
      }
      setConnection(
        importedRailway.url && importedRailway.secret ? "unknown" : "offline",
      );
      setSettingsOpen(false);
      setToast("Backup imported. Your contest history is now on this domain.");
    } catch {
      setToast("That file is not a valid Eye of Loki backup.");
    }
  }

  async function runScan() {
    if (scanning) return;
    if (!railway.url || !railway.secret) {
      setSettingsOpen(true);
      setToast("Connect the private Railway service before running recon.");
      return;
    }

    const pendingLeads = contests
      .filter(
        (contest) =>
          contest.analysisMethod === "unscored" ||
          contest.verdict === "Needs reconnaissance",
      )
      .slice(0, 4);
    setScanning(true);
    setScanProgress(8);
    announceRecon({
      kind: "working",
      message:
        "Searching eight fresh contest lanes, excluding everything already in your history.",
    });
    const interval = window.setInterval(
      () => setScanProgress((value) => Math.min(86, value + 4)),
      650,
    );

    let serviceReached = false;
    try {
      const response = await fetch(
        `${railway.url.replace(/\/$/, "")}/v1/discover`,
        {
          method: "POST",
          headers: {
            "content-type": "application/json",
            authorization: `Bearer ${railway.secret}`,
          },
          body: JSON.stringify({
            known_urls: contests.map((contest) => contest.url),
            known_titles: contests.map((contest) => contest.title),
            round: discoveryRound,
            limit: 12,
            profile: PROFILE,
          }),
        },
      );
      serviceReached = true;
      const payload = (await response.json()) as DiscoveryResponse;
      if (!response.ok || !payload.discoveries) {
        throw new Error(
          response.status === 404
            ? "Railway needs the v4 discovery backend. Upload the new railway package and redeploy."
            : payload.detail ?? `Discovery failed with HTTP ${response.status}`,
        );
      }

      const safeDiscoveries = payload.discoveries.filter(
        (item) =>
          item &&
          typeof item.url === "string" &&
          typeof item.title === "string" &&
          typeof item.analysis?.deadline === "string",
      );
      let workingContests = contests;
      let verifiedAnalyses: ReconAnalysis[] = [];
      if (pendingLeads.length) {
        try {
          const verificationResponse = await fetch(
            `${railway.url.replace(/\/$/, "")}/v1/recon`,
            {
              method: "POST",
              headers: {
                "content-type": "application/json",
                authorization: `Bearer ${railway.secret}`,
              },
              body: JSON.stringify({
                contests: pendingLeads.map((contest) => ({
                  id: contest.id,
                  slug: contest.slug,
                  title: contest.title,
                  organizer: contest.organizer,
                  prize: contest.prize,
                  url: contest.url,
                  deadline: contest.deadline,
                  winners: contest.winners,
                  locality: contest.locality,
                  eligibility: contest.eligibility,
                  entry_method: contest.entryMethod,
                  known_registration_required:
                    contest.registrationRequired,
                })),
                profile: PROFILE,
              }),
            },
          );
          const verificationPayload = (await verificationResponse.json()) as {
            analyses?: ReconAnalysis[];
          };
          if (verificationResponse.ok && verificationPayload.analyses) {
            verifiedAnalyses = verificationPayload.analyses.filter(
              (analysis) =>
                Number.isFinite(analysis.contest_id) &&
                typeof analysis.deadline === "string",
            );
            const byId = new Map(
              verifiedAnalyses.map((analysis) => [
                analysis.contest_id,
                analysis,
              ]),
            );
            workingContests = contests.map((contest) => {
              const analysis = byId.get(contest.id);
              return analysis ? mapAnalysis(contest, analysis) : contest;
            });
          }
        } catch {
          // Discovery can still succeed if an independently pasted lead fails.
        }
      }
      const imported = safeDiscoveries.map((item, index) =>
        mapDiscovery(item, -Date.now() - index),
      );

      const existingUrls = new Set(
        workingContests.map((contest) => normalizeContestUrl(contest.url)),
      );
      const novel = imported.filter(
        (contest) => !existingUrls.has(normalizeContestUrl(contest.url)),
      );
      const updated = [...novel, ...workingContests];
      if (novel.length || verifiedAnalyses.length) {
        setContests(updated);
        persistLocal(updated);
        if (novel.length) setSelectedId(novel[0].id);
        setFilter("TODAY");
      }

      const nextRound = discoveryRound + 1;
      setDiscoveryRound(nextRound);
      window.localStorage.setItem(
        "eye-of-loki-discovery-round",
        String(nextRound),
      );
      setConnection("connected");
      setScanProgress(100);
      const searched = payload.searched_queries ?? 0;
      const raw = payload.raw_candidates ?? 0;
      const checked = payload.novel_candidates ?? 0;
      const resultMessage = novel.length
        ? `${novel.length} new contest${novel.length === 1 ? "" : "s"} added from ${raw} search results${verifiedAnalyses.length ? `; ${verifiedAnalyses.length} pasted lead${verifiedAnalyses.length === 1 ? "" : "s"} verified` : ""}.`
        : `No new contests cleared the filters. ${searched} search lanes, ${raw} results and ${checked} novel candidates checked${verifiedAnalyses.length ? `; ${verifiedAnalyses.length} pasted lead${verifiedAnalyses.length === 1 ? "" : "s"} verified` : ""}.`;
      setToast(resultMessage);
      announceRecon({
        kind: "success",
        message: resultMessage,
      });
    } catch (error) {
      setConnection(serviceReached ? "connected" : "offline");
      setScanProgress(100);
      const message =
        error instanceof Error
          ? error.message
          : "Recon failed. Check the Railway connection.";
      setToast(message);
      announceRecon({ kind: "error", message });
    } finally {
      window.clearInterval(interval);
      window.setTimeout(() => {
        setScanning(false);
        setScanProgress(0);
      }, 500);
    }
  }

  async function runHunt(event: React.FormEvent) {
    event.preventDefault();
    const wanted = brief.trim();
    if (!wanted || hunting) return;
    if (!railway.url || !railway.secret) {
      setToast("Connect the Railway backend first.");
      return;
    }
    setHunting(true);
    try {
      const response = await fetch(
        `${railway.url.replace(/\/$/, "")}/v1/hunt`,
        {
          method: "POST",
          headers: {
            "content-type": "application/json",
            authorization: `Bearer ${railway.secret}`,
          },
          body: JSON.stringify({
            brief: wanted,
            known_urls: contests.map((contest) => contest.url),
            known_titles: contests.map((contest) => contest.title),
            limit: 12,
            profile: PROFILE,
          }),
        },
      );
      const payload = (await response.json()) as {
        interpretation?: string;
        adjacent_queries_used?: boolean;
        result?: DiscoveryResponse;
        detail?: string;
      };
      if (!response.ok) {
        throw new Error(payload.detail || "Hunt failed");
      }
      const found = Array.isArray(payload.result?.discoveries)
        ? payload.result.discoveries
        : [];
      const imported = found.map((item, index) =>
        mapDiscovery(item, -Date.now() - index),
      );
      const existing = new Set(
        contests.map((contest) => normalizeContestUrl(contest.url)),
      );
      const novel = imported.filter(
        (contest) => !existing.has(normalizeContestUrl(contest.url)),
      );
      if (novel.length) {
        const updated = [...novel, ...contests];
        setContests(updated);
        persistLocal(updated);
        setSelectedId(novel[0].id);
        setFilter("ALL");
      }
      const widened = payload.adjacent_queries_used
        ? " Nothing matched literally, so this widened to neighbouring categories."
        : "";
      setToast(
        novel.length
          ? `${novel.length} new from "${payload.interpretation ?? wanted}".${widened}`
          : `Nothing new for "${wanted}". Try a broader wording.${widened}`,
      );
      setBrief("");
    } catch (error) {
      setToast(
        error instanceof Error ? error.message : "Hunt failed",
      );
    } finally {
      setHunting(false);
    }
  }

  function addLead(event: React.FormEvent) {
    event.preventDefault();
    if (!leadUrl.trim() || adding) return;
    setAdding(true);
    try {
      const url = new URL(leadUrl);
      if (!["http:", "https:"].includes(url.protocol)) {
        throw new Error("Unsupported protocol");
      }
      const localLead: Contest = {
        id: -Date.now(),
        slug: `local-${Date.now()}`,
        title: `Investigate ${url.hostname.replace(/^www\./, "")}`,
        organizer: url.hostname.replace(/^www\./, ""),
        prize: "Prize not parsed yet",
        description: "Manually added lead waiting for research.",
        score: 0,
        status: "NEW",
        competition: "High",
        deadline: "2026-12-31",
        eligibility: "Needs review",
        entryMethod: "Needs review",
        friction: "Unknown",
        winners: 1,
        locality: "Germany",
        url: url.toString(),
        musicUrl: null,
        verdict: "Needs reconnaissance",
        reasons: JSON.stringify(["Added manually", "Facts need verification"]),
        verification: "Queued locally; live check pending.",
        registrationRequired: false,
        newsletterRequired: false,
        entrantsLow: 0,
        entrantsLikely: 0,
        entrantsHigh: 0,
        chanceLowPpm: 0,
        chanceLikelyPpm: 0,
        chanceHighPpm: 0,
        confidence: "Low",
        frictionMinutes: 0,
        scoreBreakdown: "{}",
        evidenceUrls: JSON.stringify([url.toString()]),
        analysisMethod: "unscored",
        enteredAt: null,
        lastCheckedAt: null,
      };
      setContests((current) => {
        const updated = [localLead, ...current];
        persistLocal(updated);
        return updated;
      });
      setSelectedId(localLead.id);
      setLeadUrl("");
      setFilter("TODAY");
      setToast("Lead stored locally. The next discovery run will verify it too.");
    } catch {
      setToast("Paste a valid http(s) contest URL.");
    } finally {
      setAdding(false);
    }
  }

  function jumpToQueue(nextFilter: Filter) {
    setFilter(nextFilter);
    setMobileNav(false);
    window.setTimeout(
      () =>
        document
          .getElementById("opportunity-queue")
          ?.scrollIntoView({ behavior: "smooth", block: "start" }),
      0,
    );
  }

  return (
    <main className="app-shell">
      <aside className={`side-rail ${mobileNav ? "is-open" : ""}`}>
        <div className="side-top">
          <EyeOfLokiLogo />
          <button
            className="icon-button close-nav"
            aria-label="Close navigation"
            onClick={() => setMobileNav(false)}
          >
            <Icon name="x" />
          </button>
        </div>

        <nav className="primary-nav" aria-label="Main navigation">
          <button
            className={`nav-item ${
              !["ALL", "ENTERED"].includes(filter) ? "is-active" : ""
            }`}
            onClick={() => jumpToQueue("TODAY")}
          >
            <Icon name="radar" />
            <span>Queue</span>
            <i>{readyCount}</i>
          </button>
          <button
            className={`nav-item ${filter === "ALL" ? "is-active" : ""}`}
            onClick={() => jumpToQueue("ALL")}
          >
            <Icon name="spark" />
            <span>All contests</span>
          </button>
          <button
            className={`nav-item ${filter === "ENTERED" ? "is-active" : ""}`}
            onClick={() => jumpToQueue("ENTERED")}
          >
            <Icon name="check" />
            <span>Entered</span>
            <i>{entered.length}</i>
          </button>
        </nav>

        <button
          className="connection-card"
          onClick={() => setSettingsOpen(true)}
        >
          <span className={`connection-light is-${connection}`} />
          <span>
            <b>
              {connection === "connected"
                ? "Railway connected"
                : "Connect Railway"}
            </b>
            <small>
                {connection === "connected"
                  ? "New-contest discovery ready"
                  : "Required for web discovery"}
            </small>
          </span>
          <Icon name="settings" size={16} />
        </button>

        <div className="operator-card">
          <span className="operator-avatar">
            {displayName.slice(0, 1).toUpperCase()}
          </span>
          <span>
            <b>{displayName}</b>
            <small>Private instance</small>
          </span>
        </div>
      </aside>

      {mobileNav && (
        <button
          className="nav-scrim"
          aria-label="Close navigation"
          onClick={() => setMobileNav(false)}
        />
      )}

      <section className="workspace">
        <header className="topbar">
          <button
            className="icon-button mobile-menu"
            aria-label="Open navigation"
            onClick={() => setMobileNav(true)}
          >
            <Icon name="menu" />
          </button>
          <div className="topbar-title">
            <span>BERLIN / GERMANY</span>
            <b suppressHydrationWarning>{berlinNow}</b>
          </div>
          <div className="topbar-actions">
            <button
              className="settings-button"
              onClick={() => setSettingsOpen(true)}
            >
              <Icon name="server" />
              <span>
                {connection === "connected" ? "Backend online" : "Backend setup"}
              </span>
            </button>
            <button
              className={`scan-button ${scanning ? "is-scanning" : ""}`}
              onClick={runScan}
              disabled={scanning}
            >
              <span className="scan-icon">
                <Icon name="radar" />
              </span>
              {scanning ? "Hunting…" : "Discover new"}
            </button>
          </div>
          {scanning && (
            <span
              className="scan-progress"
              style={{ "--scan-progress": `${scanProgress}%` } as React.CSSProperties}
            />
          )}
        </header>

        <div className="workspace-scroll">
          {reconNotice && (
            <div
              className={`recon-notice is-${reconNotice.kind}`}
              role={reconNotice.kind === "error" ? "alert" : "status"}
            >
              <span className="connection-light" />
              <b>
                {reconNotice.kind === "working"
                  ? "Discovery running"
                  : reconNotice.kind === "success"
                    ? "Last discovery complete"
                    : "Last discovery failed"}
              </b>
              <p>{reconNotice.message}</p>
              <button
                aria-label="Dismiss recon status"
                onClick={() => {
                  setReconNotice(null);
                  window.localStorage.removeItem("eye-of-loki-last-recon");
                }}
              >
                <Icon name="x" size={15} />
              </button>
            </div>
          )}
          <section className="page-intro">
            <div>
              <span className="kicker">
                <LokiMark /> Private contest intelligence
              </span>
              <h1>Opportunity queue</h1>
              <p>
                Current German competitions, ranked by estimated odds, prize
                value and the amount of nonsense required to enter.
              </p>
            </div>
            <div className="method-note">
              <b>How the estimate works</b>
              <span>
                Each run searches a new slice of the web, rejects known URLs,
                then verifies eligibility, deadline and entry route.
              </span>
            </div>
          </section>

          <section className="stat-strip" aria-label="Portfolio overview">
            <article>
              <span>Ready now</span>
              <strong>{readyCount}</strong>
              <small>working entry paths</small>
            </article>
            <article>
              <span>Entered</span>
              <strong>{entered.length}</strong>
              <small>active entries</small>
            </article>
            <article>
              <span>Portfolio chance</span>
              <strong>{formatChance(Math.round(portfolioLikely * 1_000_000))}</strong>
              <small>
                range {formatChance(Math.round(portfolioLow * 1_000_000))}–
                {formatChance(Math.round(portfolioHigh * 1_000_000))}
              </small>
            </article>
            <article>
              <span>Model</span>
              <strong className="model-stat">3.5</strong>
              <small>Gemini + Tavily search</small>
            </article>
          </section>

          <section className="queue-section" id="opportunity-queue">
            <div className="section-head">
              <div className="filter-row" role="tablist" aria-label="Queue filters">
                {(["TODAY", "READY", "ENTERED", "BLOCKED", "ALL"] as Filter[]).map(
                  (item) => (
                    <button
                      key={item}
                      role="tab"
                      aria-selected={filter === item}
                      className={filter === item ? "is-active" : ""}
                      onClick={() => setFilter(item)}
                    >
                      {item === "TODAY" ? "For today" : item.toLowerCase()}
                      {item === "READY" && <span>{readyCount}</span>}
                    </button>
                  ),
                )}
              </div>

              <form className="lead-form hunt-form" onSubmit={runHunt}>
                <Icon name="radar" />
                <input
                  aria-label="What do you want to win"
                  placeholder="What do you want to win? e.g. headphones, shipped to Germany"
                  value={brief}
                  onChange={(event) => setBrief(event.target.value)}
                />
                <button disabled={hunting || !brief.trim()}>
                  {hunting ? "Hunting…" : "Hunt"}
                </button>
              </form>

              <form className="lead-form" onSubmit={addLead}>
                <Icon name="link" />
                <input
                  aria-label="Contest URL"
                  placeholder="Paste a contest URL"
                  value={leadUrl}
                  onChange={(event) => setLeadUrl(event.target.value)}
                />
                <button disabled={adding || !leadUrl.trim()}>
                  {adding ? "Adding…" : "Add"}
                </button>
              </form>
            </div>

            <div className="queue-layout">
              <div className="contest-list">
                {visible.length ? (
                  visible.map((contest) => (
                    <ContestCard
                      key={contest.id}
                      contest={contest}
                      selected={selected?.id === contest.id}
                      onSelect={() => {
                        setSelectedId(contest.id);
                        setDetailOpen(true);
                      }}
                      onStatus={setStatus}
                    />
                  ))
                ) : (
                  <div className="empty-state">
                    <LokiMark />
                    <h3>Nothing in this view</h3>
                    <p>Change the filter or add a contest URL.</p>
                  </div>
                )}
              </div>

              {selected && (
                <aside className={`detail-panel ${detailOpen ? "is-open" : ""}`}>
                  <button
                    className="icon-button detail-close"
                    aria-label="Close details"
                    onClick={() => setDetailOpen(false)}
                  >
                    <Icon name="x" />
                  </button>
                  <ContestDetail contest={selected} onStatus={setStatus} />
                </aside>
              )}
            </div>
          </section>
        </div>
      </section>

      {settingsOpen && (
        <ConnectionModal
          railway={railway}
          setRailway={setRailway}
          testing={testingConnection}
          connection={connection}
          onTest={() => void testRailway()}
          onSave={saveRailway}
          onExport={exportBackup}
          onImport={importBackup}
          onClose={() => setSettingsOpen(false)}
        />
      )}

      {toast && (
        <div className="toast" role="status">
          <LokiMark />
          <span>{toast}</span>
        </div>
      )}
    </main>
  );
}

function ContestCard({
  contest,
  selected,
  onSelect,
  onStatus,
}: {
  contest: Contest;
  selected: boolean;
  onSelect: () => void;
  onStatus: (id: number, status: ContestStatus) => void;
}) {
  return (
    <article className={`contest-card ${selected ? "is-selected" : ""}`}>
      <button className="card-main" onClick={onSelect}>
        <div className="score">
          <span>{contest.status === "BLOCKED" ? "—" : contest.score}</span>
          <small>score</small>
        </div>
        <div className="card-copy">
          <div className="card-meta">
            <span className={`status-pill status-${contest.status.toLowerCase()}`}>
              {contest.status}
            </span>
            <span>{contest.locality}</span>
            <span>{contest.confidence} confidence</span>
          </div>
          <h3>{contest.title}</h3>
          <p>{contest.prize}</p>
        </div>
        <div className="chance-cell">
          <small>Field size</small>
          <b>{crowdLabel(contest)}</b>
          <span>est. {chanceRange(contest)}</span>
        </div>
        <div className="card-deadline">
          <small>Deadline</small>
          <b>{formatDeadline(contest.deadline)}</b>
          <span>
            {deadlineCountdown(contest.deadline)}
          </span>
        </div>
      </button>
      <div className="card-actions">
        <span>
          <Icon name="clock" size={15} />
          {contest.friction}
        </span>
        <span>{contest.winners} winner{contest.winners === 1 ? "" : "s"}</span>
        <span>{contest.competition} competition</span>
        {contest.status !== "ENTERED" && contest.status !== "BLOCKED" && (
          <>
            <button onClick={() => onStatus(contest.id, "SKIPPED")}>
              <Icon name="skip" size={15} /> Skip
            </button>
            <button
              className="quick-enter"
              onClick={() => onStatus(contest.id, "ENTERED")}
            >
              <Icon name="check" size={15} /> Entered
            </button>
          </>
        )}
      </div>
    </article>
  );
}

function ContestDetail({
  contest,
  onStatus,
}: {
  contest: Contest;
  onStatus: (id: number, status: ContestStatus) => void;
}) {
  const reasons = parseReasons(contest.reasons);
  const evidence = parseEvidence(contest.evidenceUrls);
  const breakdown = parseBreakdown(contest.scoreBreakdown);

  return (
    <>
      <div className="detail-heading">
        <span className={`status-pill status-${contest.status.toLowerCase()}`}>
          {contest.status}
        </span>
        <span>{contest.organizer}</span>
      </div>
      <h2>{contest.title}</h2>
      <p className="detail-description">{contest.description}</p>

      <div className="probability-card">
        <span>Estimated probability (unverified)</span>
        <strong>{crowdLabel(contest)}</strong>
        <small>
          {chanceRange(contest)} · likely{" "}
          {formatChance(contest.chanceLikelyPpm)} · about{" "}
          {contest.entrantsLow.toLocaleString("en-GB")}–
          {contest.entrantsHigh.toLocaleString("en-GB")} entrants
        </small>
        <div className="confidence-line">
          <span>Confidence</span>
          <b>{contest.confidence}</b>
          <span className="confidence-track">
            <i
              style={{
                width:
                  contest.confidence === "High"
                    ? "100%"
                    : contest.confidence === "Medium"
                      ? "66%"
                      : "33%",
              }}
            />
          </span>
        </div>
      </div>

      <div className="intel-grid">
        <div>
          <span>Score</span>
          <b>{contest.score}/100</b>
        </div>
        <div>
          <span>Deadline</span>
          <b>{formatDeadline(contest.deadline)}</b>
        </div>
        <div>
          <span>Eligibility</span>
          <b>{contest.eligibility}</b>
        </div>
        <div>
          <span>Entry route</span>
          <b>{contest.entryMethod}</b>
        </div>
      </div>

      <section className="breakdown">
        <div className="detail-section-title">
          <b>Loki Score</b>
          <span>Fixed formula, not an LLM opinion</span>
        </div>
        {Object.entries(breakdown).map(([label, value]) => (
          <div className="breakdown-row" key={label}>
            <span>{label}</span>
            <i>
              <b style={{ width: `${Math.max(0, Math.min(100, value))}%` }} />
            </i>
            <strong>{value}</strong>
          </div>
        ))}
      </section>

      <section className="reason-box">
        <div className="detail-section-title">
          <b>Evidence summary</b>
          <span>{contest.analysisMethod}</span>
        </div>
        <ul>
          {reasons.map((reason) => (
            <li key={reason}>
              <Icon
                name={contest.status === "BLOCKED" ? "x" : "check"}
                size={15}
              />
              {reason}
            </li>
          ))}
        </ul>
      </section>

      <div className="verification">
        <span className="connection-light is-connected" />
        <div>
          <b>Research note</b>
          <p>{contest.verification}</p>
        </div>
      </div>

      {evidence.length > 0 && (
        <div className="evidence-links">
          {evidence.slice(0, 3).map((url, index) => (
            <a href={url} target="_blank" rel="noreferrer" key={url}>
              Source {index + 1}
              <Icon name="external" size={14} />
            </a>
          ))}
        </div>
      )}

      {contest.musicUrl && (
        <a
          className="music-link"
          href={contest.musicUrl}
          target="_blank"
          rel="noreferrer"
        >
          <span>
            <small>Listen before deciding</small>
            <b>Santa Monica Dream · Angus & Julia Stone</b>
          </span>
          <Icon name="external" />
        </a>
      )}

      <div className="detail-actions">
        <a href={contest.url} target="_blank" rel="noreferrer">
          Open contest <Icon name="external" />
        </a>
        {contest.status !== "ENTERED" && contest.status !== "BLOCKED" && (
          <button onClick={() => onStatus(contest.id, "ENTERED")}>
            <Icon name="check" /> Mark entered
          </button>
        )}
      </div>
    </>
  );
}

function ConnectionModal({
  railway,
  setRailway,
  testing,
  connection,
  onTest,
  onSave,
  onExport,
  onImport,
  onClose,
}: {
  railway: RailwayConfig;
  setRailway: React.Dispatch<React.SetStateAction<RailwayConfig>>;
  testing: boolean;
  connection: ConnectionState;
  onTest: () => void;
  onSave: () => void;
  onExport: () => void;
  onImport: (file: File) => void;
  onClose: () => void;
}) {
  return (
    <div className="modal-backdrop" role="presentation" onMouseDown={onClose}>
      <section
        className="connection-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="connection-title"
        onMouseDown={(event) => event.stopPropagation()}
      >
        <div className="modal-head">
          <span className="modal-icon">
            <Icon name="server" />
          </span>
          <div>
            <h2 id="connection-title">Railway intelligence service</h2>
            <p>Connect the private backend that performs web research.</p>
          </div>
          <button className="icon-button" aria-label="Close" onClick={onClose}>
            <Icon name="x" />
          </button>
        </div>

        <label>
          <span>Railway service URL</span>
          <input
            type="url"
            placeholder="https://your-service.up.railway.app"
            value={railway.url}
            onChange={(event) =>
              setRailway((current) => ({ ...current, url: event.target.value }))
            }
          />
        </label>
        <label>
          <span>Shared secret</span>
          <input
            type="password"
            autoComplete="off"
            placeholder="Generated with openssl rand -hex 32"
            value={railway.secret}
            onChange={(event) =>
              setRailway((current) => ({
                ...current,
                secret: event.target.value,
              }))
            }
          />
        </label>

        <div className="privacy-note">
          <Icon name="check" size={16} />
          The URL and secret stay in this browser. They are sent only to your
          Railway service.
        </div>

        <div className="backup-panel">
          <div>
            <b>Move or back up this instance</b>
            <span>
              The JSON includes contest history and your Railway secret. Store it
              privately.
            </span>
          </div>
          <div className="backup-actions">
            <button type="button" onClick={onExport}>
              <Icon name="download" size={16} />
              Export
            </button>
            <label>
              <Icon name="upload" size={16} />
              Import
              <input
                type="file"
                accept="application/json,.json"
                onChange={(event) => {
                  const file = event.target.files?.[0];
                  if (file) void onImport(file);
                  event.target.value = "";
                }}
              />
            </label>
          </div>
        </div>

        <div className="modal-status">
          <span className={`connection-light is-${connection}`} />
          {connection === "connected"
            ? "Connected and ready"
            : "Not connected yet"}
        </div>

        <div className="modal-actions">
          <button className="secondary-button" onClick={onTest} disabled={testing}>
            {testing ? "Testing…" : "Test connection"}
          </button>
          <button
            className="primary-button"
            onClick={onSave}
            disabled={!railway.url.trim() || !railway.secret.trim()}
          >
            Save connection
          </button>
        </div>
      </section>
    </div>
  );
}
