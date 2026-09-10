import { normalizeSource } from "./source_api";
import type {
  AttemptPayload,
  AttemptStatus,
  Bootstrap,
  BootstrapTime,
  EvaluationPayload,
  PracticeLevelResult,
  PracticeResult,
  Profile,
  ScoreSummary,
  Session,
  TimeSnapshot,
} from "./attempt_state";
import type { StaticManifest } from "./api";

export function normalizeEvaluation(value: unknown): EvaluationPayload {
  const data = record(value, "evaluation");
  const attempt = normalizeAttempt(data);
  if (attempt.source === null || attempt.sourceEtag === null) {
    throw new Error("evaluation response source is missing");
  }
  if (typeof data.newly_submitted !== "boolean") {
    throw new Error("evaluation response is invalid");
  }
  return {
    ...attempt,
    time: { ...attempt.time, session: attempt.session },
    practice: normalizePractice(data.practice, attempt.session.score),
    newlySubmitted: data.newly_submitted,
  };
}

export function normalizeBootstrap(value: unknown): Bootstrap {
  const data = record(value, "bootstrap");
  const assessment = record(data.assessment, "assessment");
  const levels = list(data.levels, "levels").map(normalizeLevel);
  const profiles = list(data.profiles, "profiles").map(normalizeProfile);
  const rules = list(data.rules, "rules");
  if (!validBootstrap(assessment, levels, profiles, rules)) {
    throw new Error("bootstrap is invalid");
  }
  return {
    assessment: {
      assessment_id: assessment.assessment_id,
      display_name: assessment.display_name,
      level_count: 4,
    },
    levels,
    profiles,
    rules: rules as string[],
    session: data.session == null ? null : normalizeSession(data.session),
    time: data.time == null ? null : normalizeBootstrapTime(data.time),
  };
}

function validBootstrap(
  assessment: Record<string, any>,
  levels: Array<{ level: number; label: string }>,
  profiles: Profile[],
  rules: unknown[],
): boolean {
  return typeof assessment.assessment_id === "string" &&
    typeof assessment.display_name === "string" &&
    assessment.level_count === 4 &&
    levels.length === 4 &&
    levels.every((item, index) => item.level === index + 1) &&
    profiles.length >= 2 &&
    profiles.some((profile) => profile.mode === "full") &&
    profiles.some((profile) => profile.mode === "drill") &&
    rules.every((rule) => typeof rule === "string");
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
  const sourceDocument = data.source == null ? null : normalizeSource(data.source);
  const source = sourceDocument?.content ?? null;
  if (session.status === "active" && source === null) {
    throw new Error("active attempt source is missing");
  }
  return {
    session,
    source,
    sourceEtag: sourceDocument?.etag ?? null,
    time,
  };
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
  return {
    editor: `/${findAsset(manifest, "editor.worker-")}`,
    language: `/${findAsset(manifest, "language.worker-")}`,
  };
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
    (submittedAt !== null && submittedAt !== undefined &&
      typeof submittedAt !== "string")
  ) {
    throw new Error("session data is invalid");
  }
  return {
    ...item,
    attempt_id: item.attempt_id,
    status: item.status,
    profile: normalizeProfile(item.profile),
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

function normalizeScore(value: unknown): ScoreSummary {
  const data = record(value, "score");
  exactKeys(
    data,
    ["levels", "passed_levels", "highest_contiguous_level"],
    "score",
  );
  const levels = list(data.levels, "score levels").map((item) => {
    const level = record(item, "score level");
    exactKeys(level, ["level", "outcome"], "score level");
    if (
      !Number.isInteger(level.level) ||
      level.level < 1 ||
      level.level > 4 ||
      typeof level.outcome !== "string" ||
      !["passed", "failed", "error"].includes(level.outcome)
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
    levels.some((item, index) => item.level !== index + 1) ||
    !Number.isInteger(data.passed_levels) ||
    !Number.isInteger(data.highest_contiguous_level) ||
    data.passed_levels !== levels.filter((item) => item.outcome === "passed").length
  ) {
    throw new Error("score response is invalid");
  }
  let highestContiguous = 0;
  let prefixIsPassing = true;
  for (const level of levels) {
    if (level.outcome === "passed") {
      if (prefixIsPassing) highestContiguous = level.level;
    } else if (prefixIsPassing) {
      prefixIsPassing = false;
    }
  }
  if (data.highest_contiguous_level !== highestContiguous) {
    throw new Error("score response is invalid");
  }
  return {
    levels,
    passed_levels: data.passed_levels,
    highest_contiguous_level: data.highest_contiguous_level,
  };
}

function normalizePractice(
  value: unknown,
  score: ScoreSummary | null,
): PracticeResult | null {
  if (value === undefined) {
    return score === null ? null : practiceFromScore(score);
  }
  if (value === null) {
    if (score !== null) throw new Error("practice result is missing");
    return null;
  }
  if (score === null) throw new Error("practice result has no score");
  const data = record(value, "practice result");
  exactKeys(data, ["levels"], "practice result");
  const levels = list(data.levels, "practice levels").map(normalizePracticeLevel);
  if (
    levels.length !== 4 ||
    levels.some((item, index) =>
      item.level !== index + 1 ||
      item.outcome !== score.levels[index].outcome
    )
  ) {
    throw new Error("practice result is invalid");
  }
  return { levels };
}

export function practiceFromScore(score: ScoreSummary): PracticeResult {
  return {
    levels: score.levels.map((level) => ({
      level: level.level,
      outcome: level.outcome,
      candidate_output: level.outcome === "failed"
        ? "The candidate solution did not pass this practice level."
        : null,
      candidate_error: level.outcome === "error"
        ? "The local practice check could not be completed."
        : null,
    })),
  };
}

function normalizePracticeLevel(value: unknown): PracticeLevelResult {
  const level = record(value, "practice level");
  exactKeys(
    level,
    ["level", "outcome", "candidate_output", "candidate_error"],
    "practice level",
  );
  if (
    !Number.isInteger(level.level) ||
    level.level < 1 ||
    level.level > 4 ||
    typeof level.outcome !== "string" ||
    !["passed", "failed", "error"].includes(level.outcome)
  ) {
    throw new Error("practice result is invalid");
  }
  const outcome = level.outcome as PracticeLevelResult["outcome"];
  const candidateOutput = safeResultText(
    level.candidate_output,
    outcome === "failed" ? "output" : null,
    outcome === "failed",
  );
  const candidateError = safeResultText(
    level.candidate_error,
    outcome === "error" ? "error" : null,
    outcome === "error",
  );
  return {
    level: level.level,
    outcome,
    candidate_output: candidateOutput,
    candidate_error: candidateError,
  };
}

function safeResultText(
  value: unknown,
  kind: "output" | "error" | null,
  required: boolean,
): string | null {
  if (!required) {
    if (value !== null) throw new Error("practice result contains unsupported text");
    return null;
  }
  if (typeof value !== "string" || !kind) {
    throw new Error("practice result contains unsupported text");
  }
  const bytes = new TextEncoder().encode(value);
  if (bytes.length > 4096) {
    throw new Error("practice result text is too long");
  }
  const allowed = kind === "output"
    ? "The candidate solution did not pass this practice level."
    : "The local practice check could not be completed.";
  if (value !== allowed) {
    throw new Error("practice result contains unsupported text");
  }
  return value;
}

function exactKeys(
  value: Record<string, any>,
  expected: string[],
  label: string,
): void {
  const actual = Object.keys(value).sort().join(",");
  if (actual !== [...expected].sort().join(",")) {
    throw new Error(`${label} has an invalid field set`);
  }
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

