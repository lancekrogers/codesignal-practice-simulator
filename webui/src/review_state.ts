import type { AttemptStatus, Profile, ScoreSummary } from "./state";
import { isHistoryStatus } from "./history_state";

/**
 * Review screen document (D002/D004). Every field of the stored review is
 * validated; an incomplete or altered payload is an error, never an empty
 * success. Nothing here is ever written back.
 */

export type ReviewAssessment = {
  assessment_id: string;
  display_name: string;
  level_count: number;
  content_identity: "pinned" | "unavailable";
  content_version: string | null;
  content_digest: string | null;
};

export type ReviewSource = {
  filename: string;
  sha256: string;
  content: string;
  binding: "captured" | "legacy_unbound";
};

export type ReviewRecord = {
  attempt_id: string;
  schema_version: string;
  status: AttemptStatus;
  assessment: ReviewAssessment;
  profile: Profile;
  started_at: string;
  deadline_at: string;
  submitted_at: string | null;
  score: ScoreSummary | null;
  practice_score: ScoreSummary | null;
  source_binding: "captured" | "not_captured" | "not_applicable";
  source: ReviewSource | null;
  issues: string[];
};

export const LEGACY_BINDING_UNAVAILABLE = "submitted_source_binding_unavailable";
export const SOURCE_UNREADABLE_AT_SUBMISSION = "submitted_source_was_unreadable";
export const LEGACY_SOURCE_UNAVAILABLE = "legacy_source_unavailable";
export const CONTENT_IDENTITY_UNAVAILABLE = "content_identity_unavailable";

const SHA256 = /^[0-9a-f]{64}$/u;
const MAX_SOURCE_BYTES = 1024 * 1024;

export function normalizeReview(value: unknown, attemptId: string): ReviewRecord {
  const item = record(value, "review");
  const issues = list(item.issues, "review issues");
  if (
    item.attempt_id !== attemptId ||
    typeof item.schema_version !== "string" ||
    !isHistoryStatus(item.status) ||
    typeof item.started_at !== "string" ||
    typeof item.deadline_at !== "string" ||
    (item.submitted_at !== null && typeof item.submitted_at !== "string") ||
    !["captured", "not_captured", "not_applicable"].includes(item.source_binding) ||
    !issues.every((issue) => typeof issue === "string")
  ) {
    throw new Error("review is invalid");
  }
  const source = item.source == null ? null : normalizeSource(item.source);
  // The binding axis and the source view must agree in both directions:
  // captured ⇔ a captured source view; not_captured ⇒ no source or an
  // explicitly unbound legacy view; not_applicable ⇒ no source at all.
  if (item.source_binding === "not_applicable" && source !== null) {
    throw new Error("review is invalid");
  }
  if (item.source_binding === "captured" && source?.binding !== "captured") {
    throw new Error("review is invalid");
  }
  if (item.source_binding === "not_captured" && source !== null && source.binding !== "legacy_unbound") {
    throw new Error("review is invalid");
  }
  if (item.practice_score != null && item.status !== "abandoned") {
    throw new Error("review is invalid");
  }
  return {
    attempt_id: attemptId,
    schema_version: item.schema_version,
    status: item.status,
    assessment: normalizeAssessment(item.assessment),
    profile: normalizeProfile(item.profile),
    started_at: item.started_at,
    deadline_at: item.deadline_at,
    submitted_at: item.submitted_at as string | null,
    score: item.score == null ? null : normalizeScore(item.score),
    practice_score: item.practice_score == null ? null : normalizeScore(item.practice_score),
    source_binding: item.source_binding,
    source,
    issues: issues as string[],
  };
}

function normalizeAssessment(value: unknown): ReviewAssessment {
  const item = record(value, "review assessment");
  if (
    typeof item.assessment_id !== "string" ||
    typeof item.display_name !== "string" ||
    !Number.isInteger(item.level_count) ||
    (item.content_identity !== "pinned" && item.content_identity !== "unavailable") ||
    (item.content_version !== null && typeof item.content_version !== "string") ||
    (item.content_digest !== null && typeof item.content_digest !== "string") ||
    (item.content_identity === "pinned" &&
      (typeof item.content_version !== "string" || typeof item.content_digest !== "string"))
  ) {
    throw new Error("review assessment is invalid");
  }
  return {
    assessment_id: item.assessment_id,
    display_name: item.display_name,
    level_count: item.level_count as number,
    content_identity: item.content_identity,
    content_version: item.content_version as string | null,
    content_digest: item.content_digest as string | null,
  };
}

function normalizeSource(value: unknown): ReviewSource {
  const item = record(value, "review source");
  if (
    typeof item.filename !== "string" ||
    typeof item.sha256 !== "string" ||
    !SHA256.test(item.sha256) ||
    typeof item.content !== "string" ||
    item.content.length > MAX_SOURCE_BYTES ||
    (item.binding !== "captured" && item.binding !== "legacy_unbound")
  ) {
    throw new Error("review source is invalid");
  }
  return {
    filename: item.filename,
    sha256: item.sha256,
    content: item.content,
    binding: item.binding,
  };
}

function normalizeProfile(value: unknown): Profile {
  const item = record(value, "review profile");
  if (
    (item.mode !== "full" && item.mode !== "drill") ||
    typeof item.profile_id !== "string" ||
    !Number.isInteger(item.duration_seconds) ||
    (item.duration_seconds as number) <= 0
  ) {
    throw new Error("review profile is invalid");
  }
  return {
    mode: item.mode,
    profile_id: item.profile_id,
    duration_seconds: item.duration_seconds as number,
  };
}

function normalizeScore(value: unknown): ScoreSummary {
  const item = record(value, "review score");
  const levels = list(item.levels, "review score levels").map((level) => {
    const entry = record(level, "review score level");
    if (
      !Number.isInteger(entry.level) ||
      (entry.outcome !== "passed" && entry.outcome !== "failed" && entry.outcome !== "error")
    ) {
      throw new Error("review score level is invalid");
    }
    return { level: entry.level as number, outcome: entry.outcome };
  });
  if (
    !Number.isInteger(item.passed_levels) ||
    !Number.isInteger(item.highest_contiguous_level) ||
    levels.length === 0 ||
    (item.passed_levels as number) > levels.length
  ) {
    throw new Error("review score is invalid");
  }
  return {
    passed_levels: item.passed_levels as number,
    highest_contiguous_level: item.highest_contiguous_level as number,
    levels,
  } as ScoreSummary;
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
