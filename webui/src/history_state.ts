import type { AttemptStatus, Profile, ScoreSummary } from "./state";

/**
 * History screen state (D004): filters and the page cursor live in the URL
 * fragment of `/history`, never in a query string (the server serves the shell
 * only for query-less routes) and never with source text or a token. The
 * listing document is validated field by field; unknown shapes are rejected
 * rather than rendered.
 */

export const HISTORY_STATUSES: readonly AttemptStatus[] = [
  "active",
  "expired",
  "submitted",
  "abandoned",
];

export const HISTORY_PAGE_SIZES: readonly number[] = [10, 25, 50, 100];
export const DEFAULT_HISTORY_LIMIT = 25;
const MAX_HISTORY_LIMIT = 100;
const MAX_CURSOR_LENGTH = 4096;
const CURSOR_SHAPE = /^[A-Za-z0-9_-]+$/u;
const ASSESSMENT_ID_SHAPE = /^[a-z0-9_]+$/u;

export type HistoryQuery = {
  status: AttemptStatus | null;
  assessmentId: string | null;
  cursor: string | null;
  limit: number;
};

export type HistoryAssessment = {
  assessment_id: string;
  display_name: string;
  level_count: number;
  content_identity: string;
  content_version: string | null;
};

export type HistoryItem = {
  attempt_id: string;
  available: boolean;
  issues: string[];
  /** Null only for rows whose record could not be read (`available: false`). */
  status: AttemptStatus | null;
  persisted_status: AttemptStatus | null;
  assessment: HistoryAssessment | null;
  profile: Profile | null;
  started_at: string | null;
  deadline_at: string | null;
  submitted_at: string | null;
  ended_at: string | null;
  score: ScoreSummary | null;
  practice_score: ScoreSummary | null;
  review_available: boolean;
};

export type HistoryWarning = { code: string; count: number };

export type HistoryPage = {
  items: HistoryItem[];
  next_cursor: string | null;
  warnings: HistoryWarning[];
  limit: number;
};

export type HistoryStateIssue = "cursor_shape" | "limit_shape" | "status_shape" | "assessment_shape";

export type HistoryFragment = {
  query: HistoryQuery;
  issues: HistoryStateIssue[];
};

export function defaultHistoryQuery(): HistoryQuery {
  return { status: null, assessmentId: null, cursor: null, limit: DEFAULT_HISTORY_LIMIT };
}

/** Parse the fragment; a malformed value drops back to the default and is reported. */
export function readHistoryFragment(hash: string): HistoryFragment {
  const params = new URLSearchParams(hash.replace(/^#/u, ""));
  const query = defaultHistoryQuery();
  const issues: HistoryStateIssue[] = [];
  const status = params.get("status");
  if (status !== null) {
    if (isHistoryStatus(status)) query.status = status;
    else issues.push("status_shape");
  }
  const assessment = params.get("assessment_id");
  if (assessment !== null) {
    if (ASSESSMENT_ID_SHAPE.test(assessment) && assessment.length <= 64) {
      query.assessmentId = assessment;
    } else {
      issues.push("assessment_shape");
    }
  }
  const cursor = params.get("cursor");
  if (cursor !== null) {
    if (CURSOR_SHAPE.test(cursor) && cursor.length <= MAX_CURSOR_LENGTH) query.cursor = cursor;
    else issues.push("cursor_shape");
  }
  const limit = params.get("limit");
  if (limit !== null) {
    const value = Number(limit);
    if (/^\d{1,3}$/u.test(limit) && value >= 1 && value <= MAX_HISTORY_LIMIT) query.limit = value;
    else issues.push("limit_shape");
  }
  return { query, issues };
}

export function historyFragment(query: HistoryQuery): string {
  const params = new URLSearchParams();
  if (query.status) params.set("status", query.status);
  if (query.assessmentId) params.set("assessment_id", query.assessmentId);
  if (query.cursor) params.set("cursor", query.cursor);
  if (query.limit !== DEFAULT_HISTORY_LIMIT) params.set("limit", String(query.limit));
  const encoded = params.toString();
  return encoded ? `#${encoded}` : "";
}

export function writeHistoryFragment(query: HistoryQuery): void {
  if (typeof window === "undefined") return;
  window.history.replaceState(
    null,
    "",
    `${window.location.pathname}${window.location.search}${historyFragment(query)}`,
  );
}

export function historyRequestPath(query: HistoryQuery): string {
  const params = new URLSearchParams();
  if (query.status) params.set("status", query.status);
  if (query.assessmentId) params.set("assessment_id", query.assessmentId);
  if (query.cursor) params.set("cursor", query.cursor);
  params.set("limit", String(query.limit));
  return `/api/attempts?${params.toString()}`;
}

export function isHistoryStatus(value: unknown): value is AttemptStatus {
  return typeof value === "string" && (HISTORY_STATUSES as readonly string[]).includes(value);
}

export function normalizeHistoryPage(value: unknown): HistoryPage {
  const data = record(value, "history page");
  const items = list(data.items, "history items").map(normalizeHistoryItem);
  const warnings = list(data.warnings, "history warnings").map(normalizeWarning);
  if (
    (data.next_cursor !== null && typeof data.next_cursor !== "string") ||
    !Number.isInteger(data.limit) ||
    (data.limit as number) < 1 ||
    (data.limit as number) > MAX_HISTORY_LIMIT ||
    items.length > (data.limit as number)
  ) {
    throw new Error("history page is invalid");
  }
  if (typeof data.next_cursor === "string" &&
    (!CURSOR_SHAPE.test(data.next_cursor) || data.next_cursor.length > MAX_CURSOR_LENGTH)) {
    throw new Error("history page is invalid");
  }
  return { items, next_cursor: data.next_cursor as string | null, warnings, limit: data.limit as number };
}

function normalizeHistoryItem(value: unknown): HistoryItem {
  const item = record(value, "history item");
  const issues = list(item.issues, "history issues");
  if (
    typeof item.attempt_id !== "string" ||
    typeof item.available !== "boolean" ||
    !issues.every((issue) => typeof issue === "string") ||
    !(isHistoryStatus(item.status) || (item.status == null && item.available === false)) ||
    !(isHistoryStatus(item.persisted_status) ||
      (item.persisted_status == null && item.available === false)) ||
    typeof item.review_available !== "boolean" ||
    !Number.isInteger(item.revision) && item.revision !== null ||
    // A practice result belongs only to an ended attempt; a final score only
    // to a submitted one. Anything else would be labelled misleadingly.
    (item.practice_score != null && item.status !== "abandoned") ||
    (item.score != null && item.status !== "submitted" && item.status !== "expired" &&
      item.status !== "active")
  ) {
    throw new Error("history item is invalid");
  }
  return {
    attempt_id: item.attempt_id,
    available: item.available,
    issues: issues as string[],
    status: item.status ?? null,
    persisted_status: item.persisted_status ?? null,
    assessment: item.assessment == null ? null : normalizeAssessment(item.assessment),
    profile: item.profile == null ? null : normalizeProfile(item.profile),
    started_at: optionalString(item.started_at),
    deadline_at: optionalString(item.deadline_at),
    submitted_at: optionalString(item.submitted_at),
    ended_at: optionalString(item.ended_at),
    score: item.score == null ? null : normalizeScore(item.score),
    practice_score: item.practice_score == null ? null : normalizeScore(item.practice_score),
    review_available: item.review_available,
  };
}

function normalizeAssessment(value: unknown): HistoryAssessment {
  const item = record(value, "history assessment");
  if (
    typeof item.assessment_id !== "string" ||
    typeof item.display_name !== "string" ||
    !Number.isInteger(item.level_count) ||
    typeof item.content_identity !== "string" ||
    (item.content_version !== null && typeof item.content_version !== "string")
  ) {
    throw new Error("history assessment is invalid");
  }
  return {
    assessment_id: item.assessment_id,
    display_name: item.display_name,
    level_count: item.level_count as number,
    content_identity: item.content_identity,
    content_version: item.content_version as string | null,
  };
}

function normalizeProfile(value: unknown): Profile {
  const item = record(value, "history profile");
  if (
    (item.mode !== "full" && item.mode !== "drill") ||
    typeof item.profile_id !== "string" ||
    !Number.isInteger(item.duration_seconds) ||
    (item.duration_seconds as number) <= 0
  ) {
    throw new Error("history profile is invalid");
  }
  return {
    mode: item.mode,
    profile_id: item.profile_id,
    duration_seconds: item.duration_seconds as number,
  };
}

function normalizeScore(value: unknown): ScoreSummary {
  const item = record(value, "history score");
  const levels = list(item.levels, "history score levels").map((level) => {
    const entry = record(level, "history score level");
    if (
      !Number.isInteger(entry.level) ||
      (entry.outcome !== "passed" && entry.outcome !== "failed" && entry.outcome !== "error")
    ) {
      throw new Error("history score level is invalid");
    }
    return { level: entry.level as number, outcome: entry.outcome };
  });
  if (
    !Number.isInteger(item.passed_levels) ||
    !Number.isInteger(item.highest_contiguous_level) ||
    levels.length === 0
  ) {
    throw new Error("history score is invalid");
  }
  return {
    passed_levels: item.passed_levels as number,
    highest_contiguous_level: item.highest_contiguous_level as number,
    levels,
  } as ScoreSummary;
}

function normalizeWarning(value: unknown): HistoryWarning {
  const item = record(value, "history warning");
  if (typeof item.code !== "string" || !Number.isInteger(item.count) || (item.count as number) < 0) {
    throw new Error("history warning is invalid");
  }
  return { code: item.code, count: item.count as number };
}

function optionalString(value: unknown): string | null {
  if (value == null) return null;
  if (typeof value !== "string") throw new Error("history timestamp is invalid");
  return value;
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
