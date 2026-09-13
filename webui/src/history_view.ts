import type { AttemptStatus, Bootstrap } from "./state";
import { lifecycleLabel } from "./attempt_dom";
import {
  HISTORY_PAGE_SIZES,
  HISTORY_STATUSES,
  type HistoryItem,
  type HistoryPage,
  type HistoryQuery,
  type HistoryStateIssue,
  type HistoryWarning,
} from "./history_state";

/**
 * Attempt history screen (D004): filters, one bounded page of metadata rows,
 * aggregate warnings for skipped entries, per-row availability, and Review /
 * Resume actions. Rendering reads nothing but the page document; the caller
 * owns requests and navigation.
 */

export type HistoryScreenState = {
  bootstrap: Bootstrap;
  query: HistoryQuery;
  page: HistoryPage | null;
  loading: boolean;
  error: { message: string; recoverable: boolean } | null;
  fragmentIssues: HistoryStateIssue[];
};

export type HistoryCallbacks = {
  onFilters(query: Pick<HistoryQuery, "status" | "assessmentId" | "limit">): void;
  onNewest(): void;
  onOlder(cursor: string): void;
  onRefresh(): void;
  onRetry(): void;
  onReview(attemptId: string): void;
  onResume(attemptId: string): void;
  onLibrary(): void;
};

export type HistoryElements = {
  heading: HTMLElement;
  status: HTMLElement;
};

const WARNING_COPY: Record<string, (count: number) => string> = {
  unsafe_entries_skipped: (count) =>
    `${count} ${count === 1 ? "entry" : "entries"} in the attempts folder ${count === 1 ? "is" : "are"} not a safe attempt record and ${count === 1 ? "was" : "were"} skipped.`,
  unavailable_records_excluded_by_filter: (count) =>
    `${count} unavailable ${count === 1 ? "record is" : "records are"} hidden by the current filters.`,
  restart_journals_unreadable: (count) =>
    `${count} restart ${count === 1 ? "journal" : "journals"} could not be read; the attempts involved may be shown as available.`,
};

const ISSUE_COPY: Record<string, string> = {
  record_unavailable: "Record unavailable",
  record_corrupt: "Record corrupt",
  restart_pending: "Restart pending",
  finalization_pending: "Finalization pending",
  content_identity_unavailable: "Content identity unavailable",
};

const FRAGMENT_ISSUE_COPY: Record<HistoryStateIssue, string> = {
  cursor_shape: "The page position in this address is not valid; showing the newest attempts instead.",
  limit_shape: "The rows-per-page value in this address is not valid; using the default.",
  status_shape: "The status filter in this address is not valid; showing all statuses.",
  assessment_shape: "The exercise filter in this address is not valid; showing all exercises.",
};

export function renderHistory(
  root: HTMLElement,
  state: HistoryScreenState,
  callbacks: HistoryCallbacks,
): HistoryElements {
  root.replaceChildren();
  const main = document.createElement("main");
  main.className = "shell entry attempts-history";
  main.setAttribute("aria-labelledby", "history-title");
  const header = document.createElement("header");
  header.className = "library-header";
  const heading = document.createElement("h1");
  heading.id = "history-title";
  heading.tabIndex = -1;
  heading.textContent = "Attempt history";
  const framing = document.createElement("p");
  framing.textContent =
    "Stored attempts, newest first, from their saved metadata only. Opening a review never changes which attempt is selected.";
  const nav = document.createElement("nav");
  nav.setAttribute("aria-label", "History navigation");
  const library = button("Back to library", "secondary", "history-library");
  library.addEventListener("click", callbacks.onLibrary);
  nav.append(library);
  header.append(heading, framing, nav);
  const status = document.createElement("p");
  status.className = "status";
  status.setAttribute("role", "status");
  status.textContent = statusText(state);
  main.append(header, filters(state, callbacks), status);
  for (const issue of state.fragmentIssues) {
    main.append(notice(FRAGMENT_ISSUE_COPY[issue], "history-notice"));
  }
  if (state.error) main.append(errorBanner(state.error, callbacks));
  if (state.page) {
    for (const warning of state.page.warnings) {
      if (warning.count > 0) main.append(notice(warningText(warning), "history-warning"));
    }
    main.append(rows(state, callbacks), pagination(state, callbacks));
  }
  root.append(main);
  return { heading, status };
}

function statusText(state: HistoryScreenState): string {
  if (state.loading) return "Loading attempt history…";
  if (state.error) return "Attempt history could not be loaded.";
  if (!state.page) return "";
  const count = state.page.items.length;
  if (count === 0) {
    return state.query.status || state.query.assessmentId
      ? "No attempts match these filters."
      : "No attempts yet. Start one from the library.";
  }
  const page = state.query.cursor ? "an older page" : "the newest page";
  return `Showing ${count} ${count === 1 ? "attempt" : "attempts"} on ${page}.`;
}

function filters(state: HistoryScreenState, callbacks: HistoryCallbacks): HTMLElement {
  const form = document.createElement("form");
  form.className = "history-filters";
  form.setAttribute("aria-label", "History filters");
  form.addEventListener("submit", (event) => event.preventDefault());
  const exercise = select("history-assessment", "Exercise", [
    { value: "", label: "All exercises" },
    ...orderedCatalog(state.bootstrap).map((entry) => ({
      value: entry.assessment_id,
      label: entry.display_name,
    })),
  ], state.query.assessmentId || "");
  const status = select("history-status", "Status", [
    { value: "", label: "All statuses" },
    ...HISTORY_STATUSES.map((value) => ({ value, label: lifecycleLabel(value) })),
  ], state.query.status || "");
  const sizes = HISTORY_PAGE_SIZES.includes(state.query.limit)
    ? HISTORY_PAGE_SIZES
    : [state.query.limit, ...HISTORY_PAGE_SIZES].sort((a, b) => a - b);
  const limit = select("history-limit", "Rows per page",
    sizes.map((value) => ({ value: String(value), label: String(value) })),
    String(state.query.limit));
  const apply = (): void => {
    const nextStatus = status.select.value;
    callbacks.onFilters({
      status: nextStatus && (HISTORY_STATUSES as readonly string[]).includes(nextStatus)
        ? nextStatus as AttemptStatus
        : null,
      assessmentId: exercise.select.value || null,
      limit: Number(limit.select.value),
    });
  };
  exercise.select.addEventListener("change", apply);
  status.select.addEventListener("change", apply);
  limit.select.addEventListener("change", apply);
  const refresh = button("Refresh", "secondary", "history-refresh");
  refresh.addEventListener("click", callbacks.onRefresh);
  // Controls stay enabled while a page loads so keyboard focus survives the
  // re-render; the controller drops responses from superseded requests.
  form.append(exercise.field, status.field, limit.field, refresh);
  return form;
}

function orderedCatalog(bootstrap: Bootstrap): Bootstrap["catalog"] {
  const primary = bootstrap.assessment.assessment_id;
  return [
    ...bootstrap.catalog.filter((entry) => entry.assessment_id === primary),
    ...bootstrap.catalog.filter((entry) => entry.assessment_id !== primary),
  ];
}

function select(
  id: string,
  labelText: string,
  options: Array<{ value: string; label: string }>,
  selected: string,
): { field: HTMLElement; select: HTMLSelectElement } {
  const field = document.createElement("label");
  field.className = "history-field";
  field.htmlFor = id;
  const text = document.createElement("span");
  text.textContent = labelText;
  const control = document.createElement("select");
  control.id = id;
  control.name = id;
  for (const option of options) {
    const element = document.createElement("option");
    element.value = option.value;
    element.textContent = option.label;
    element.selected = option.value === selected;
    control.append(element);
  }
  field.append(text, control);
  return { field, select: control };
}

function notice(text: string, className: string): HTMLElement {
  const element = document.createElement("p");
  element.className = className;
  element.textContent = text;
  return element;
}

function warningText(warning: HistoryWarning): string {
  const copy = WARNING_COPY[warning.code];
  return copy
    ? copy(warning.count)
    : `${warning.count} ${warning.count === 1 ? "entry was" : "entries were"} reported with a warning (${warning.code}).`;
}

function errorBanner(
  error: { message: string; recoverable: boolean },
  callbacks: HistoryCallbacks,
): HTMLElement {
  const section = document.createElement("section");
  section.className = "history-error";
  const message = document.createElement("p");
  message.className = "error-message";
  message.setAttribute("role", "alert");
  message.textContent = error.message;
  const actions = document.createElement("div");
  actions.className = "action-group";
  const retry = button("Retry", "primary", "history-retry");
  retry.addEventListener("click", callbacks.onRetry);
  const newest = button("Show newest", "secondary", "history-show-newest");
  newest.addEventListener("click", callbacks.onNewest);
  actions.append(retry, newest);
  section.append(message, actions);
  return section;
}

function rows(state: HistoryScreenState, callbacks: HistoryCallbacks): HTMLElement {
  const page = state.page!;
  if (page.items.length === 0) {
    const empty = document.createElement("p");
    empty.className = "history-empty";
    empty.textContent = state.query.status || state.query.assessmentId
      ? "No attempts match these filters. Clear a filter or refresh."
      : "No attempts yet. Start one from the library.";
    return empty;
  }
  const wrapper = document.createElement("div");
  wrapper.className = "history-table";
  const table = document.createElement("table");
  const caption = document.createElement("caption");
  caption.textContent = "Attempts on this page, newest first";
  const head = document.createElement("thead");
  const headRow = document.createElement("tr");
  for (const label of ["Exercise", "Status", "Format", "Started", "Result", "Review", "Actions"]) {
    const cell = document.createElement("th");
    cell.scope = "col";
    cell.textContent = label;
    headRow.append(cell);
  }
  head.append(headRow);
  const body = document.createElement("tbody");
  for (const item of page.items) body.append(row(item, state, callbacks));
  table.append(caption, head, body);
  wrapper.append(table);
  return wrapper;
}

function row(item: HistoryItem, state: HistoryScreenState, callbacks: HistoryCallbacks): HTMLElement {
  const tr = document.createElement("tr");
  tr.dataset.attemptId = item.attempt_id;
  tr.dataset.available = String(item.available);
  const exercise = document.createElement("th");
  exercise.scope = "row";
  exercise.textContent = item.assessment?.display_name || "Unknown exercise";
  if (item.assessment?.content_version) {
    const version = document.createElement("span");
    version.className = "exercise-meta";
    version.textContent = ` · ${item.assessment.content_version}`;
    exercise.append(version);
  }
  tr.append(
    exercise,
    cell(statusCell(item)),
    cell(item.profile ? `${item.profile.mode} · ${Math.floor(item.profile.duration_seconds / 60)} min` : "—"),
    cell(item.started_at || "—"),
    cell(resultText(item)),
    cell(reviewText(item)),
    actions(item, state, callbacks),
  );
  return tr;
}

function statusCell(item: HistoryItem): HTMLElement {
  const container = document.createElement("span");
  const label = document.createElement("span");
  label.className = `lifecycle lifecycle-${item.status ?? "unknown"}`;
  label.textContent = item.status ? lifecycleLabel(item.status) : "Unknown";
  container.append(label);
  if (item.status && item.persisted_status && item.status !== item.persisted_status) {
    const note = document.createElement("span");
    note.className = "exercise-meta";
    note.textContent = " (not yet recorded)";
    container.append(note);
  }
  if (!item.available) {
    const badge = document.createElement("span");
    badge.className = "readiness readiness-setup";
    badge.textContent = "Unavailable";
    badge.title = item.issues.map((issue) => ISSUE_COPY[issue] || issue).join(", ");
    const issues = document.createElement("span");
    issues.className = "history-issues";
    issues.textContent = item.issues.map((issue) => ISSUE_COPY[issue] || issue).join(", ");
    container.append(" ", badge, " ", issues);
  }
  return container;
}

function resultText(item: HistoryItem): string {
  if (item.status === "submitted" && item.score) {
    return `Final: ${item.score.passed_levels} of ${item.score.levels.length} levels`;
  }
  // An ended attempt keeps its last practice result in practice_score; an
  // active or expired one still holds it in score. Neither is a final result.
  const practice = item.practice_score ?? (item.status !== "submitted" ? item.score : null);
  if (practice) {
    return `Last practice: ${practice.passed_levels} of ${practice.levels.length} levels`;
  }
  if (item.status === "submitted") return "Final result unavailable";
  return "No result recorded";
}

function reviewText(item: HistoryItem): string {
  if (item.review_available) return "Submission review available";
  if (item.status === "submitted") return "No submission review stored";
  return "Saved work only";
}

function actions(item: HistoryItem, state: HistoryScreenState, callbacks: HistoryCallbacks): HTMLElement {
  const td = document.createElement("td");
  const group = document.createElement("div");
  group.className = "action-group";
  const review = button("Review", "secondary");
  review.setAttribute("aria-label", `Review ${item.assessment?.display_name || "attempt"} ${shortId(item.attempt_id)}`);
  review.disabled = !item.available;
  review.addEventListener("click", () => callbacks.onReview(item.attempt_id));
  group.append(review);
  const selected = state.bootstrap.session?.attempt_id === item.attempt_id;
  if (selected && item.status === "active" && item.available) {
    const resume = button("Resume", "primary");
    resume.setAttribute("aria-label", `Resume ${item.assessment?.display_name || "attempt"} ${shortId(item.attempt_id)}`);
    resume.addEventListener("click", () => callbacks.onResume(item.attempt_id));
    group.append(resume);
  }
  td.append(group);
  return td;
}

function shortId(attemptId: string): string {
  return attemptId.slice(0, 8);
}

function pagination(state: HistoryScreenState, callbacks: HistoryCallbacks): HTMLElement {
  const page = state.page!;
  const nav = document.createElement("nav");
  nav.className = "history-pagination";
  nav.setAttribute("aria-label", "History pages");
  const newest = button("Newest", "secondary", "history-newest");
  newest.disabled = !state.query.cursor;
  newest.addEventListener("click", callbacks.onNewest);
  const older = button("Older", "secondary", "history-older");
  older.disabled = !page.next_cursor;
  if (page.next_cursor) {
    const cursor = page.next_cursor;
    older.addEventListener("click", () => callbacks.onOlder(cursor));
  }
  nav.append(newest, older);
  if (state.query.cursor) {
    const note = document.createElement("p");
    note.className = "history-notice";
    note.textContent =
      "This is an older page. Attempts created or removed since you started browsing can move between pages; choose Newest or Refresh to see the current list.";
    nav.append(note);
  }
  return nav;
}

function cell(content: string | HTMLElement): HTMLElement {
  const td = document.createElement("td");
  if (typeof content === "string") td.textContent = content;
  else td.append(content);
  return td;
}

function button(label: string, kind: "primary" | "secondary", id = ""): HTMLButtonElement {
  const element = document.createElement("button");
  element.type = "button";
  element.className = kind;
  element.textContent = label;
  if (id) element.id = id;
  return element;
}
