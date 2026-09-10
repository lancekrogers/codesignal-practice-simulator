import type { StaticManifest } from "./api";
import { createSourceState, type SourceState } from "./source_state";
import {
  defaultAttemptViewState,
  readAttemptViewState,
  type PromptTab,
} from "./view_state";

export type Mode = "full" | "drill";
export type AttemptStatus = "active" | "expired" | "submitted";
export type ConnectionState = "connected" | "reconnecting";
export type ActionState = "idle" | "testing" | "submitting";

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

export type PracticeLevelResult = {
  level: number;
  outcome: "passed" | "failed" | "error";
  candidate_output: string | null;
  candidate_error: string | null;
};

export type PracticeResult = {
  levels: PracticeLevelResult[];
};

export type Session = {
  attempt_id: string;
  status: AttemptStatus;
  assessment?: Record<string, unknown>;
  profile: Profile;
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
  practice: PracticeResult | null;
  source: string | null;
  sourceEtag: string | null;
  sourceState: SourceState | null;
  time: TimeSnapshot;
  selectedLevel: number;
  selectedTab: PromptTab;
  connection: ConnectionState;
  action: ActionState;
};

export type ErrorState = {
  phase: "error";
  manifest: StaticManifest;
  message: string;
};

export type BrowserState = BootingState | EntryState | AttemptState | ErrorState;

export type AttemptPayload = {
  session: Session;
  practice?: PracticeResult | null;
  source: string | null;
  sourceEtag: string | null;
  time: TimeSnapshot;
};

export type EvaluationPayload = Omit<AttemptPayload, "source" | "sourceEtag"> & {
  source: string;
  sourceEtag: string;
  practice: PracticeResult | null;
  newlySubmitted: boolean;
};

export function initialState(
  manifest: StaticManifest | null = null,
): BootingState {
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
): AttemptState {
  const view = bootstrap.session?.attempt_id === payload.session.attempt_id
    ? readAttemptViewState(payload.session.attempt_id)
    : defaultAttemptViewState();
  const sourceState = payload.source !== null && payload.sourceEtag !== null
    ? createSourceState(payload.source, payload.sourceEtag)
    : null;
  return {
    phase: "attempt",
    manifest,
    bootstrap,
    session: payload.session,
    practice: payload.practice ?? null,
    source: payload.source,
    sourceEtag: payload.sourceEtag,
    sourceState,
    time: payload.time,
    selectedLevel: view.level,
    selectedTab: view.tab,
    connection: "connected",
    action: "idle",
  };
}

export function errorState(
  manifest: StaticManifest,
  message: string,
): ErrorState {
  return { phase: "error", manifest, message };
}

