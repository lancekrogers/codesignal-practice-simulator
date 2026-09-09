import type { StaticManifest } from "./api";

export type Mode = "full" | "drill";
export type AttemptStatus = "active" | "expired" | "submitted";
export type ConnectionState = "connected" | "reconnecting";
export type PromptTab = "description" | "history" | "rules" | "info";

export type Profile = {
  mode: Mode;
  profile_id: string;
  duration_seconds: number;
};

export type ScoreSummary = {
  levels: Array<{ level: number; outcome: "passed" | "failed" | "error" }>;
  passed_levels: number;
  highest_contiguous_level: number;
};

export type Session = {
  attempt_id: string;
  status: AttemptStatus;
  assessment?: Record<string, unknown>;
  profile?: Profile;
  started_at: string;
  deadline_at: string;
  score: ScoreSummary | null;
  submitted_at: string | null;
  [key: string]: unknown;
};

export type TimeSnapshot = {
  session: Session;
  observed_at: string;
  elapsed_seconds: number;
  remaining_seconds: number;
};

export type BootstrapTime = {
  observed_at: string;
  remaining_seconds: number;
};

export type Bootstrap = {
  assessment: {
    assessment_id: string;
    display_name: string;
    level_count: 4;
  };
  levels: Array<{ level: number; label: string }>;
  profiles: Profile[];
  rules: string[];
  session: Session | null;
  time: BootstrapTime | null;
};

export type BootingState = {
  phase: "booting";
  manifest: StaticManifest;
};

export type EntryState = {
  phase: "entry";
  bootstrap: Bootstrap;
  manifest: StaticManifest;
  selectedMode: Mode;
};

export type AttemptState = {
  phase: "attempt";
  bootstrap: Bootstrap;
  manifest: StaticManifest;
  session: Session;
  source: string | null;
  time: TimeSnapshot;
  selectedLevel: number;
  selectedTab: PromptTab;
  connection: ConnectionState;
};

export type ErrorState = {
  phase: "error";
  manifest: StaticManifest;
  message: string;
};

export type BrowserState = BootingState | EntryState | AttemptState | ErrorState;

export function initialState(manifest: StaticManifest | null = null): BootingState {
  return { phase: "booting", manifest: manifest || {} };
}

export function entryState(
  manifest: StaticManifest,
  bootstrap: Bootstrap,
): EntryState {
  return { phase: "entry", manifest, bootstrap, selectedMode: "full" };
}

export function attemptState(
  manifest: StaticManifest,
  bootstrap: Bootstrap,
  payload: AttemptPayload,
  selectedLevel = 1,
): AttemptState {
  return {
    phase: "attempt",
    manifest,
    bootstrap,
    session: payload.session,
    source: payload.source,
    time: payload.time,
    selectedLevel,
    selectedTab: "description",
    connection: "connected",
  };
}

export function errorState(manifest: StaticManifest, message: string): ErrorState {
  return { phase: "error", manifest, message };
}

export type AttemptPayload = {
  session: Session;
  source: string | null;
  time: TimeSnapshot;
};

export function normalizeBootstrap(value: unknown): Bootstrap {
  const data = record(value, "bootstrap");
  const assessment = record(data.assessment, "assessment");
  const levels = list(data.levels, "levels");
  const profiles = list(data.profiles, "profiles");
  const rules = list(data.rules, "rules");
  if (
    typeof assessment.assessment_id !== "string" ||
    typeof assessment.display_name !== "string" ||
    assessment.level_count !== 4 ||
    levels.length !== 4 ||
    profiles.length < 2 ||
    !rules.every((rule) => typeof rule === "string")
  ) {
    throw new Error("bootstrap is invalid");
  }
  const normalizedLevels = levels.map(normalizeLevel);
  if (normalizedLevels.some((item, index) => item.level !== index + 1)) {
    throw new Error("bootstrap is invalid");
  }
  const normalizedProfiles = profiles.map(normalizeProfile);
  if (
    !normalizedProfiles.some((profile) => profile.mode === "full") ||
    !normalizedProfiles.some((profile) => profile.mode === "drill")
  ) {
    throw new Error("bootstrap is invalid");
  }
  return {
    assessment: {
      assessment_id: assessment.assessment_id,
      display_name: assessment.display_name,
      level_count: 4,
    },
    levels: normalizedLevels,
    profiles: normalizedProfiles,
    rules: rules as string[],
    session: data.session == null ? null : normalizeSession(data.session),
    time: data.time == null ? null : normalizeBootstrapTime(data.time),
  };
}

export function normalizeAttempt(value: unknown): AttemptPayload {
  const data = record(value, "attempt");
  const session = normalizeSession(data.session);
  const time = normalizeTimeSnapshot(data.time);
  if (
    time.session.attempt_id !== session.attempt_id ||
    time.session.status !== session.status
  ) {
    throw new Error("attempt response is invalid");
  }
  const source = data.source == null ? null : normalizeSource(data.source);
  if (session.status === "active" && source === null) {
    throw new Error("active attempt source is missing");
  }
  return { session, source, time };
}

export function normalizeTime(value: unknown): TimeSnapshot {
  return normalizeTimeSnapshot(value);
}

export function normalizePrompt(value: unknown): {
  attempt_id: string;
  level: number;
  prompt: string;
} {
  const data = record(value, "prompt");
  if (
    typeof data.attempt_id !== "string" ||
    !Number.isInteger(data.level) ||
    data.level < 1 ||
    data.level > 4 ||
    typeof data.prompt !== "string" ||
    data.prompt.length > 512 * 1024
  ) {
    throw new Error("prompt response is invalid");
  }
  return {
    attempt_id: data.attempt_id,
    level: data.level,
    prompt: data.prompt,
  };
}

export function workerUrls(manifest: StaticManifest): {
  editor: string;
  language: string;
} {
  const editor = findAsset(manifest, "editor.worker-");
  const language = findAsset(manifest, "language.worker-");
  return { editor: `/${editor}`, language: `/${language}` };
}

function findAsset(manifest: StaticManifest, prefix: string): string {
  const name = Object.keys(manifest).find(
    (candidate) => candidate.startsWith(prefix) && candidate.endsWith(".js"),
  );
  if (!name) throw new Error(`required packaged worker is missing: ${prefix}`);
  return name;
}

function normalizeLevel(value: unknown): { level: number; label: string } {
  const item = record(value, "level");
  if (typeof item.level !== "number" || typeof item.label !== "string") {
    throw new Error("bootstrap is invalid");
  }
  return { level: item.level, label: item.label };
}

function normalizeProfile(value: unknown): Profile {
  const item = record(value, "profile");
  if (
    (item.mode !== "full" && item.mode !== "drill") ||
    typeof item.profile_id !== "string" ||
    !Number.isInteger(item.duration_seconds) ||
    item.duration_seconds <= 0
  ) {
    throw new Error("bootstrap is invalid");
  }
  return {
    mode: item.mode,
    profile_id: item.profile_id,
    duration_seconds: item.duration_seconds,
  };
}

function normalizeSession(value: unknown): Session {
  const item = record(value, "session");
  const submittedAt = item.submitted_at;
  if (
    typeof item.attempt_id !== "string" ||
    item.attempt_id.length === 0 ||
    !isAttemptStatus(item.status) ||
    typeof item.started_at !== "string" ||
    typeof item.deadline_at !== "string" ||
    (submittedAt !== null && submittedAt !== undefined && typeof submittedAt !== "string")
  ) {
    throw new Error("session data is invalid");
  }
  return {
    ...item,
    attempt_id: item.attempt_id,
    status: item.status,
    started_at: item.started_at,
    deadline_at: item.deadline_at,
    score: item.score == null ? null : normalizeScore(item.score),
    submitted_at: submittedAt == null ? null : submittedAt,
  } as Session;
}

function normalizeTimeSnapshot(value: unknown): TimeSnapshot {
  const data = record(value, "time");
  const session = normalizeSession(data.session);
  if (
    typeof data.observed_at !== "string" ||
    !Number.isInteger(data.elapsed_seconds) ||
    data.elapsed_seconds < 0 ||
    !Number.isInteger(data.remaining_seconds) ||
    data.remaining_seconds < 0
  ) {
    throw new Error("time response is invalid");
  }
  return {
    session,
    observed_at: data.observed_at,
    elapsed_seconds: data.elapsed_seconds,
    remaining_seconds: data.remaining_seconds,
  };
}

function normalizeBootstrapTime(value: unknown): BootstrapTime {
  const data = record(value, "time");
  if (
    typeof data.observed_at !== "string" ||
    !Number.isInteger(data.remaining_seconds) ||
    data.remaining_seconds < 0
  ) {
    throw new Error("time response is invalid");
  }
  return {
    observed_at: data.observed_at,
    remaining_seconds: data.remaining_seconds,
  };
}

function normalizeSource(value: unknown): string {
  const data = record(value, "source");
  if (typeof data.content !== "string" || data.content.length > 2 * 1024 * 1024) {
    throw new Error("source response is invalid");
  }
  return data.content;
}

function normalizeScore(value: unknown): ScoreSummary {
  const data = record(value, "score");
  const levels = list(data.levels, "score levels").map((item) => {
    const level = record(item, "score level");
    if (
      !Number.isInteger(level.level) ||
      level.level < 1 ||
      level.level > 4 ||
      !["passed", "failed", "error"].includes(String(level.outcome))
    ) {
      throw new Error("score response is invalid");
    }
    return {
      level: level.level,
      outcome: level.outcome as "passed" | "failed" | "error",
    };
  });
  if (
    levels.length !== 4 ||
    !Number.isInteger(data.passed_levels) ||
    data.passed_levels < 0 ||
    data.passed_levels > 4 ||
    !Number.isInteger(data.highest_contiguous_level) ||
    data.highest_contiguous_level < 0 ||
    data.highest_contiguous_level > 4 ||
    levels.some((item, index) => item.level !== index + 1)
  ) {
    throw new Error("score response is invalid");
  }
  return {
    levels,
    passed_levels: data.passed_levels,
    highest_contiguous_level: data.highest_contiguous_level,
  };
}

function isAttemptStatus(value: unknown): value is AttemptStatus {
  return value === "active" || value === "expired" || value === "submitted";
}

function record(value: unknown, label: string): Record<string, any> {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    throw new Error(`${label} is invalid`);
  }
  return value as Record<string, any>;
}

function list(value: unknown, label: string): unknown[] {
  if (!Array.isArray(value)) throw new Error(`${label} is invalid`);
  return value;
}

export type CountdownUpdate = {
  session: Session;
  time: TimeSnapshot;
  remainingSeconds: number;
};
export type CountdownController = {
  stop(): void;
};

type CountdownRuntime = {
  current: TimeSnapshot;
  anchor: number;
  displayedRemaining: number;
  stopped: boolean;
  resyncInFlight: boolean;
  tickTimer?: ReturnType<typeof setTimeout>;
  resyncTimer?: ReturnType<typeof setTimeout>;
};

export function createCountdown(
  initial: TimeSnapshot,
  onUpdate: (update: CountdownUpdate) => void,
  onResync: () => Promise<TimeSnapshot>,
  onResyncError: () => void,
): CountdownController {
  const receivedAt = monotonicNow();
  const anchor = receivedAt - snapshotTransitAge(initial);
  const runtime: CountdownRuntime = {
    current: initial,
    anchor,
    displayedRemaining: displayCountdown(initial, anchor, receivedAt),
    stopped: false,
    resyncInFlight: false,
  };
  const emit = (): void => emitCountdown(runtime, onUpdate);
  const tick = (): void => {
    if (runtime.stopped) return;
    emit();
    if (!runtime.stopped) runtime.tickTimer = setTimeout(tick, 1000);
  };
  const resync = (): Promise<void> =>
    resyncCountdown(runtime, onResync, onResyncError, emit, resync);
  emit();
  if (!runtime.stopped) {
    runtime.tickTimer = setTimeout(tick, 1000);
    runtime.resyncTimer = setTimeout(resync, 15000);
  }
  return { stop: () => stopCountdown(runtime) };
}

function emitCountdown(
  runtime: CountdownRuntime,
  onUpdate: (update: CountdownUpdate) => void,
): void {
  const candidate = runtime.current.session.status === "active"
    ? displayCountdown(runtime.current, runtime.anchor, monotonicNow())
    : 0;
  runtime.displayedRemaining = Math.min(runtime.displayedRemaining, candidate);
  onUpdate({
    session: runtime.current.session,
    time: runtime.current,
    remainingSeconds: runtime.displayedRemaining,
  });
  if (runtime.current.session.status !== "active") stopCountdown(runtime);
}

async function resyncCountdown(
  runtime: CountdownRuntime,
  onResync: () => Promise<TimeSnapshot>,
  onResyncError: () => void,
  emit: () => void,
  schedule: () => Promise<void>,
): Promise<void> {
  if (runtime.stopped || runtime.resyncInFlight) return;
  runtime.resyncInFlight = true;
  try {
    const next = await onResync();
    if (!runtime.stopped) {
      const receivedAt = monotonicNow();
      runtime.current = next;
      runtime.anchor = receivedAt - snapshotTransitAge(next);
      emit();
    }
  } catch {
    if (!runtime.stopped) onResyncError();
  } finally {
    runtime.resyncInFlight = false;
    if (!runtime.stopped) runtime.resyncTimer = setTimeout(schedule, 15000);
  }
}

function stopCountdown(runtime: CountdownRuntime): void {
  runtime.stopped = true;
  if (runtime.tickTimer !== undefined) clearTimeout(runtime.tickTimer);
  if (runtime.resyncTimer !== undefined) clearTimeout(runtime.resyncTimer);
}

export function displayCountdown(
  snapshot: TimeSnapshot,
  anchor: number,
  now: number,
): number {
  const elapsed = Math.max(0, Math.floor((now - anchor) / 1000));
  const observedRemaining = Math.max(0, snapshot.remaining_seconds - elapsed);
  const deadline = Date.parse(snapshot.session.deadline_at);
  const observed = Date.parse(snapshot.observed_at);
  if (!Number.isFinite(deadline) || !Number.isFinite(observed)) {
    return observedRemaining;
  }
  const deadlineRemaining = Math.max(
    0,
    Math.ceil((deadline - observed) / 1000) - elapsed,
  );
  return Math.min(observedRemaining, deadlineRemaining);
}
function snapshotTransitAge(snapshot: TimeSnapshot): number {
  const observed = Date.parse(snapshot.observed_at);
  return Number.isFinite(observed)
    ? Math.max(0, Date.now() - observed)
    : snapshot.elapsed_seconds * 1000;
}

function monotonicNow(): number {
  return typeof performance !== "undefined" ? performance.now() : Date.now();
}
