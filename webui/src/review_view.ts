import type { Bootstrap, CatalogEntry, ScoreSummary } from "./state";
import { lifecycleLabel } from "./attempt_dom";
import { createDialogFocusTrap } from "./a11y";
import {
  CONTENT_IDENTITY_UNAVAILABLE,
  LEGACY_BINDING_UNAVAILABLE,
  LEGACY_SOURCE_UNAVAILABLE,
  SOURCE_UNREADABLE_AT_SUBMISSION,
  type ReviewRecord,
} from "./review_state";

/**
 * Read-only review screen (D002/D004). Shows stored metadata, the three
 * honest axes (stored metadata, content identity, source binding), the result
 * labelled by what it is (final vs last practice), and the source with its
 * binding named. Retry starts a new attempt from the current library after
 * confirmation; a live attempt is never displaced silently.
 */

export type SavedWork =
  | { kind: "none" }
  | { kind: "loaded"; content: string; etag: string }
  | { kind: "unavailable" };

export type ReviewScreenState = {
  bootstrap: Bootstrap;
  attemptId: string;
  review: ReviewRecord | null;
  savedWork: SavedWork;
  loading: boolean;
  error: { title: string; message: string; retryable: boolean } | null;
  message: string | null;
  busy: boolean;
};

export type RetryPlan = {
  entry: CatalogEntry | null;
  blockedReason: string | null;
  versionNotice: string | null;
  liveAttemptId: string | null;
};

export type ReviewCallbacks = {
  onRetryStart(plan: RetryPlan): void;
  onResumeLive(attemptId: string): void;
  onEndLiveAndStart(plan: RetryPlan): void;
  onReload(): void;
  onHistory(): void;
  onLibrary(): void;
};

export type ReviewElements = {
  heading: HTMLElement;
  status: HTMLElement;
  destroy(): void;
};

export function retryPlan(state: ReviewScreenState): RetryPlan {
  const review = state.review;
  if (!review) return { entry: null, blockedReason: "unavailable", versionNotice: null, liveAttemptId: null };
  const entry = state.bootstrap.catalog.find(
    (candidate) => candidate.assessment_id === review.assessment.assessment_id,
  ) || null;
  let blockedReason: string | null = null;
  if (!entry) {
    blockedReason =
      "This exercise is not installed in the current library, so it cannot be retried. The stored results above remain readable.";
  } else if (!entry.available) {
    blockedReason = entry.setup_message ||
      "This exercise needs local setup before a new attempt can start. The stored results above remain readable.";
  }
  let versionNotice: string | null = null;
  if (entry) {
    const stored = review.assessment.content_identity === "pinned"
      ? review.assessment.content_version
      : null;
    if (stored === null) {
      versionNotice =
        `This attempt's content version is not recorded (legacy record). The new attempt uses the current library version${entry.content_version ? ` ${entry.content_version}` : ""}.`;
    } else if (entry.content_version !== stored) {
      versionNotice =
        `The current library version${entry.content_version ? ` ${entry.content_version}` : ""} differs from the version this attempt used (${stored}). The new attempt uses the current version.`;
    }
  }
  const live = state.bootstrap.session;
  return {
    entry,
    blockedReason,
    versionNotice,
    liveAttemptId: live && live.status === "active" ? live.attempt_id : null,
  };
}

export function renderReview(
  root: HTMLElement,
  state: ReviewScreenState,
  callbacks: ReviewCallbacks,
): ReviewElements {
  root.replaceChildren();
  const main = document.createElement("main");
  main.className = "shell entry attempt-review";
  main.setAttribute("aria-labelledby", "review-title");
  main.dataset.reviewAttemptId = state.attemptId;
  const header = document.createElement("header");
  header.className = "library-header";
  const heading = document.createElement("h1");
  heading.id = "review-title";
  heading.tabIndex = -1;
  heading.textContent = state.review
    ? `Attempt review: ${state.review.assessment.display_name}`
    : "Attempt review";
  const nav = document.createElement("nav");
  nav.setAttribute("aria-label", "Review navigation");
  const history = button("Back to history", "secondary", "review-history");
  history.addEventListener("click", callbacks.onHistory);
  const library = button("Back to library", "secondary", "review-library");
  library.addEventListener("click", callbacks.onLibrary);
  nav.append(history, library);
  header.append(heading, nav);
  const status = document.createElement("p");
  status.className = "status";
  status.setAttribute("role", "status");
  status.textContent = statusText(state);
  main.append(header, status);
  let disposeDialogs = (): void => undefined;
  if (state.error) {
    main.append(errorBanner(state.error, callbacks));
  } else if (state.review) {
    const review = state.review;
    for (const banner of banners(review)) main.append(banner);
    main.append(metadata(review), result(review), sourcePane(review, state.savedWork));
    const retry = retrySection(state, callbacks);
    main.append(retry.element);
    disposeDialogs = retry.dispose;
  }
  root.append(main);
  return { heading, status, destroy: disposeDialogs };
}

function statusText(state: ReviewScreenState): string {
  if (state.loading) return "Loading the stored review…";
  if (state.message) return state.message;
  if (state.error) return "The review could not be shown.";
  if (!state.review) return "";
  const label = lifecycleLabel(state.review.status).toLowerCase();
  const article = /^[aeiou]/u.test(label) ? "an" : "a";
  return `Read-only review of ${article} ${label} attempt. Nothing here can be edited, submitted or rescored.`;
}

function banners(review: ReviewRecord): HTMLElement[] {
  const out: HTMLElement[] = [];
  if (review.issues.includes(LEGACY_BINDING_UNAVAILABLE)) {
    out.push(notice(
      "Submitted-source binding unavailable: this attempt was submitted before source capture existed. " +
      "The stored score and timestamps are shown; the source below is the attempt's current file, not proven submitted bytes.",
      "review-legacy",
    ));
  }
  if (review.issues.includes(SOURCE_UNREADABLE_AT_SUBMISSION)) {
    out.push(notice(
      "The source could not be read when this attempt was submitted, so no submitted bytes are stored. The score stands as recorded.",
      "review-legacy",
    ));
  }
  if (review.issues.includes(LEGACY_SOURCE_UNAVAILABLE)) {
    out.push(notice("No legacy source file is available for this attempt.", "review-legacy"));
  }
  if (review.assessment.content_identity !== "pinned" || review.issues.includes(CONTENT_IDENTITY_UNAVAILABLE)) {
    out.push(notice(
      "Content identity unavailable: this record predates content pinning, so the exact exercise version it used is not recorded.",
      "review-legacy",
    ));
  }
  return out;
}

function metadata(review: ReviewRecord): HTMLElement {
  const section = document.createElement("section");
  section.setAttribute("aria-labelledby", "review-metadata-title");
  const title = document.createElement("h2");
  title.id = "review-metadata-title";
  title.textContent = "Stored metadata";
  const list = document.createElement("dl");
  list.className = "session-summary";
  detail(list, "Exercise", review.assessment.display_name);
  detail(list, "Content version", review.assessment.content_identity === "pinned"
    ? `${review.assessment.content_version} (pinned)`
    : "unavailable (legacy record)");
  detail(list, "Status", lifecycleLabel(review.status));
  detail(list, "Format", `${review.profile.mode} · ${Math.floor(review.profile.duration_seconds / 60)} min`);
  detail(list, "Started", review.started_at);
  detail(list, "Deadline", review.deadline_at);
  if (review.submitted_at) detail(list, "Submitted", review.submitted_at);
  detail(list, "Record", review.schema_version);
  section.append(title, list);
  return section;
}

function result(review: ReviewRecord): HTMLElement {
  const section = document.createElement("section");
  section.className = "review-result";
  section.setAttribute("aria-labelledby", "review-result-title");
  const title = document.createElement("h2");
  title.id = "review-result-title";
  const copy = document.createElement("p");
  section.append(title, copy);
  if (review.status === "submitted") {
    title.textContent = "Final result";
    if (review.score) {
      copy.textContent = `Passed ${review.score.passed_levels} of ${review.score.levels.length} levels.`;
      section.append(levels(review.score));
    } else {
      copy.textContent = "The final result is not recorded for this attempt.";
    }
    return section;
  }
  title.textContent = "Last practice result";
  const practice = review.status === "abandoned" ? review.practice_score : review.score;
  const framing = review.status === "abandoned"
    ? "This attempt was ended without a submission."
    : review.status === "expired"
      ? "This attempt expired without a submission."
      : "This attempt is still in progress.";
  if (practice) {
    copy.textContent = `${framing} The last local practice check passed ${practice.passed_levels} of ${practice.levels.length} levels; this is not a final result.`;
    section.append(levels(practice));
  } else {
    copy.textContent = `${framing} No local practice result was recorded.`;
  }
  return section;
}

function levels(score: ScoreSummary): HTMLElement {
  const list = document.createElement("ol");
  list.className = "practice-results";
  for (const level of score.levels) {
    const item = document.createElement("li");
    item.className = `practice-result practice-${level.outcome}`;
    item.textContent = `Level ${level.level}: ${level.outcome === "passed" ? "Passed" : level.outcome === "failed" ? "Needs work" : "Unavailable"}`;
    list.append(item);
  }
  return list;
}

function sourcePane(review: ReviewRecord, savedWork: SavedWork): HTMLElement {
  const section = document.createElement("section");
  section.className = "review-source";
  section.setAttribute("aria-labelledby", "review-source-title");
  const title = document.createElement("h2");
  title.id = "review-source-title";
  const copy = document.createElement("p");
  copy.className = "exercise-meta";
  section.append(title, copy);
  const viewer = (content: string, label: string): void => {
    const area = document.createElement("textarea");
    area.className = "fallback review-source-text";
    area.readOnly = true;
    area.setAttribute("aria-label", label);
    area.value = content;
    section.append(area);
  };
  if (review.source_binding === "captured" && review.source) {
    title.textContent = "Submitted source";
    copy.textContent = `${review.source.filename} · exact scored bytes · sha256 ${review.source.sha256}`;
    viewer(review.source.content, "Submitted source, read-only");
  } else if (review.source?.binding === "legacy_unbound") {
    title.textContent = "Current file (not proven submitted)";
    copy.textContent = `${review.source.filename} · current bytes, unbound · sha256 ${review.source.sha256}`;
    viewer(review.source.content, "Legacy source, read-only");
  } else if (review.status === "submitted") {
    title.textContent = "Submitted source";
    copy.textContent = "No submitted source is stored for this attempt.";
  } else {
    title.textContent = "Saved work (not a submission)";
    if (savedWork.kind === "loaded") {
      copy.textContent = "simulation.py · the last saved version of this attempt; it was never submitted.";
      viewer(savedWork.content, "Saved work, read-only");
    } else if (savedWork.kind === "unavailable") {
      copy.textContent = "The saved work for this attempt could not be read.";
    } else {
      copy.textContent = "Saved work is loading…";
    }
  }
  return section;
}

function retrySection(
  state: ReviewScreenState,
  callbacks: ReviewCallbacks,
): { element: HTMLElement; dispose(): void } {
  const plan = retryPlan(state);
  const section = document.createElement("section");
  section.className = "review-retry";
  section.setAttribute("aria-labelledby", "review-retry-title");
  const title = document.createElement("h2");
  title.id = "review-retry-title";
  title.textContent = "Retry this exercise";
  const copy = document.createElement("p");
  copy.className = "exercise-meta";
  copy.id = "review-retry-copy";
  const retry = button("Retry this exercise", "primary", "review-retry");
  retry.setAttribute("aria-describedby", copy.id);
  section.append(title, copy, retry);
  if (plan.blockedReason) {
    copy.textContent = plan.blockedReason;
    retry.disabled = true;
    return { element: section, dispose: () => undefined };
  }
  copy.textContent =
    `Starts a new ${state.review!.profile.mode} attempt of ${plan.entry!.display_name} from the current library. ` +
    "This review and its stored results are never changed.";
  retry.disabled = state.busy;
  const dialog = createRetryDialog(section, plan, state, callbacks);
  retry.addEventListener("click", () => dialog.open(retry));
  return { element: section, dispose: dialog.dispose };
}

function createRetryDialog(
  parent: HTMLElement,
  plan: RetryPlan,
  state: ReviewScreenState,
  callbacks: ReviewCallbacks,
): { open(opener: HTMLElement): void; dispose(): void } {
  const dialog = document.createElement("dialog");
  dialog.className = "confirmation";
  dialog.setAttribute("aria-labelledby", "retry-title");
  dialog.setAttribute("aria-describedby", "retry-description");
  const title = document.createElement("h2");
  title.id = "retry-title";
  const description = document.createElement("p");
  description.id = "retry-description";
  const notice = document.createElement("p");
  notice.className = "warning";
  notice.hidden = plan.versionNotice === null;
  notice.textContent = plan.versionNotice || "";
  const actions = document.createElement("div");
  actions.className = "action-group";
  const cancel = button("Cancel", "secondary");
  const mode = state.review!.profile.mode;
  if (plan.liveAttemptId) {
    title.textContent = "An attempt is already in progress";
    description.textContent =
      "Only one attempt can be live. Resume the active attempt, or end it (its saved work is kept, no score is recorded) and start a new " +
      `${mode} attempt of ${plan.entry!.display_name}. Nothing happens until you choose.`;
    const resume = button("Resume active attempt", "primary");
    const endAndStart = button("End it and start a new attempt", "secondary");
    const live = plan.liveAttemptId;
    resume.addEventListener("click", () => {
      trap.close();
      callbacks.onResumeLive(live);
    });
    endAndStart.addEventListener("click", () => {
      trap.close();
      callbacks.onEndLiveAndStart(plan);
    });
    actions.append(resume, endAndStart, cancel);
  } else {
    title.textContent = "Start a new attempt?";
    description.textContent =
      `Starting creates one new ${mode} attempt of ${plan.entry!.display_name}. The timer begins immediately and cannot be paused. ` +
      "This review is not changed.";
    const confirm = button("Confirm and start", "primary");
    confirm.addEventListener("click", () => {
      trap.close();
      callbacks.onRetryStart(plan);
    });
    actions.append(confirm, cancel);
  }
  dialog.append(title, description, notice, actions);
  parent.append(dialog);
  const trap = createDialogFocusTrap(dialog, {
    initialFocus: actions.querySelector("button") as HTMLElement,
  });
  cancel.addEventListener("click", () => trap.close());
  return {
    open: (opener) => trap.open(opener),
    dispose: () => {
      trap.close();
      trap.dispose();
      dialog.remove();
    },
  };
}

function errorBanner(
  error: { title: string; message: string; retryable: boolean },
  callbacks: ReviewCallbacks,
): HTMLElement {
  const section = document.createElement("section");
  section.className = "history-error";
  const title = document.createElement("h2");
  title.textContent = error.title;
  const message = document.createElement("p");
  message.className = "error-message";
  message.setAttribute("role", "alert");
  message.textContent = error.message;
  const actions = document.createElement("div");
  actions.className = "action-group";
  if (error.retryable) {
    const reload = button("Retry loading", "primary", "review-reload");
    reload.addEventListener("click", callbacks.onReload);
    actions.append(reload);
  }
  section.append(title, message, actions);
  return section;
}

function notice(text: string, className: string): HTMLElement {
  const element = document.createElement("p");
  element.className = className;
  element.textContent = text;
  return element;
}

function detail(list: HTMLDListElement, label: string, value: string): void {
  const term = document.createElement("dt");
  term.textContent = label;
  const detail = document.createElement("dd");
  detail.textContent = value;
  list.append(term, detail);
}

function button(label: string, kind: "primary" | "secondary", id = ""): HTMLButtonElement {
  const element = document.createElement("button");
  element.type = "button";
  element.className = kind;
  element.textContent = label;
  if (id) element.id = id;
  return element;
}
