import type { CatalogEntry, EntryState, Mode, Session } from "./state";
import { createDialogFocusTrap } from "./a11y";
import { lifecycleLabel } from "./attempt_dom";

/**
 * Library screen (D004): exercise cards with readiness, one start form for the
 * selected exercise, the active session summary with an explicit resume action,
 * and the History entry. Rendering never starts a timer; start is a confirmed
 * POST that the caller performs.
 */

export type LibraryCallbacks = {
  onStart(assessmentId: string, mode: Mode, duration: number): void;
  onResume(): void;
  onHistory(): void;
};

export type LibraryElements = {
  heading: HTMLElement;
  start: HTMLButtonElement;
  confirm: HTMLButtonElement;
  cancel: HTMLButtonElement;
  dialog: HTMLDialogElement;
  status: HTMLElement;
  setBusy(busy: boolean): void;
  setMessage(message: string): void;
  destroy(): void;
};

type Selection = {
  entry: CatalogEntry;
};

export function renderLibrary(
  root: HTMLElement,
  state: EntryState,
  callbacks: LibraryCallbacks,
): LibraryElements {
  root.replaceChildren();
  const main = document.createElement("main");
  main.className = "shell entry library";
  main.setAttribute("aria-labelledby", "library-title");
  const session = state.bootstrap.session;
  if (session) main.dataset.activeAttemptId = session.attempt_id;
  const selection: Selection = { entry: initialSelection(state) };
  const heading = libraryHeader(main, callbacks.onHistory);
  if (session) {
    main.append(activeSessionSummary(state, callbacks.onResume));
  }
  const outlineSection = outline(selection.entry);
  const form = createStartForm(state, selection);
  const catalog = exerciseCards(state, selection, (entry) => {
    selection.entry = entry;
    form.setExercise(entry);
    outlineSection.replaceWith(outline(entry));
    form.status.textContent = `${entry.display_name} selected. Choose a format and start when ready.`;
  });
  const dialog = createConfirmation();
  main.append(catalog, outlineSection, rules(state), form.form, form.status, dialog.dialog);
  root.append(main);
  connectStartControls(form, dialog, selection, callbacks.onStart);
  return {
    heading,
    start: form.start,
    confirm: dialog.confirm,
    cancel: dialog.cancel,
    dialog: dialog.dialog,
    status: form.status,
    setBusy: (busy) => {
      form.start.disabled = busy || !selection.entry.available;
      dialog.confirm.disabled = busy;
      dialog.cancel.disabled = busy;
      form.form.querySelectorAll("input").forEach((input) => {
        input.disabled = busy;
      });
      main.querySelectorAll<HTMLButtonElement>("button.select-exercise").forEach((select) => {
        select.disabled = busy || select.dataset.available !== "true";
      });
    },
    setMessage: (message) => {
      form.status.textContent = message;
    },
    destroy: () => dialog.focus.dispose(),
  };
}

/** Primary exercise first (the bootstrap's own), then the registry order. */
function orderedCatalog(state: EntryState): CatalogEntry[] {
  const primaryId = state.bootstrap.assessment.assessment_id;
  const catalog = state.bootstrap.catalog;
  return [
    ...catalog.filter((entry) => entry.assessment_id === primaryId),
    ...catalog.filter((entry) => entry.assessment_id !== primaryId),
  ];
}

function initialSelection(state: EntryState): CatalogEntry {
  const ordered = orderedCatalog(state);
  return ordered.find((entry) => entry.available) || ordered[0];
}

function libraryHeader(main: HTMLElement, onHistory: () => void): HTMLElement {
  const header = document.createElement("header");
  header.className = "library-header";
  const title = document.createElement("h1");
  title.id = "library-title";
  title.tabIndex = -1;
  title.textContent = "Practice library";
  const framing = document.createElement("p");
  framing.textContent =
    "Local practice assessments with checks designed to help you rehearse the workflow. Choose an exercise, pick a format, and confirm before the timer begins.";
  const nav = document.createElement("nav");
  nav.setAttribute("aria-label", "Library navigation");
  const history = button("History", "secondary");
  history.addEventListener("click", onHistory);
  nav.append(history);
  header.append(title, framing, nav);
  main.append(header);
  return title;
}

function activeSessionSummary(state: EntryState, onResume: () => void): HTMLElement {
  const session = state.bootstrap.session!;
  const section = document.createElement("section");
  section.className = "active-session";
  section.setAttribute("aria-labelledby", "active-session-title");
  const title = document.createElement("h2");
  title.id = "active-session-title";
  title.textContent = session.status === "active" ? "Active session" : "Selected session";
  const summary = sessionSummary(session, sessionDisplayName(state, session));
  section.append(title, summary, resumeButton(session, onResume));
  return section;
}

/**
 * The attempt route's cold screen (reload, back, forward, or a typed address):
 * metadata only, no source request, and the attempt opens only after the
 * explicit reconnect action. Rendering it never changes lifecycle state.
 */
export function renderAttemptEntry(
  root: HTMLElement,
  state: EntryState,
  session: Session,
  callbacks: { onResume(): void; onLibrary(): void },
): HTMLElement {
  root.replaceChildren();
  const main = document.createElement("main");
  main.className = "shell entry attempt-entry";
  main.setAttribute("aria-labelledby", "attempt-entry-title");
  main.dataset.activeAttemptId = session.attempt_id;
  const header = document.createElement("header");
  const title = document.createElement("h1");
  title.id = "attempt-entry-title";
  title.tabIndex = -1;
  title.textContent = sessionDisplayName(state, session);
  const framing = document.createElement("p");
  framing.textContent = session.status === "active"
    ? "This attempt is in progress. The server timer keeps running whether or not you reconnect."
    : "This attempt is final. Its saved work opens read-only.";
  header.append(title, framing);
  const status = document.createElement("p");
  status.className = "status";
  status.setAttribute("role", "status");
  status.textContent = session.status === "active"
    ? "An existing session is available to reconnect."
    : "A final session is available to view.";
  const actions = document.createElement("div");
  actions.className = "action-group";
  const library = button("Back to library", "secondary");
  library.addEventListener("click", callbacks.onLibrary);
  actions.append(resumeButton(session, callbacks.onResume), library);
  main.append(header, sessionSummary(session, sessionDisplayName(state, session)), status, actions);
  root.append(main);
  return title;
}

function resumeButton(session: Session, onResume: () => void): HTMLButtonElement {
  const resume = button(
    session.status === "active" ? "Reconnect to active session" : "View final session",
    "primary",
  );
  resume.addEventListener("click", onResume);
  return resume;
}

function sessionSummary(session: Session, displayName: string): HTMLDListElement {
  const summary = document.createElement("dl");
  summary.className = "session-summary";
  addDetail(summary, "Exercise", displayName);
  addDetail(summary, "Status", lifecycleLabel(session.status));
  addDetail(summary, "Format", `${session.profile.mode} format`);
  addDetail(summary, "Server deadline", session.deadline_at);
  return summary;
}

function sessionDisplayName(state: EntryState, session: Session): string {
  const stored = session.assessment;
  const name = stored && typeof stored === "object"
    ? (stored as { display_name?: unknown }).display_name
    : undefined;
  if (typeof name === "string" && name) return name;
  return state.bootstrap.assessment.display_name;
}

function addDetail(list: HTMLDListElement, label: string, value: string): void {
  const term = document.createElement("dt");
  term.textContent = label;
  const detail = document.createElement("dd");
  detail.textContent = value;
  list.append(term, detail);
}

function exerciseCards(
  state: EntryState,
  selection: Selection,
  onSelect: (entry: CatalogEntry) => void,
): HTMLElement {
  const section = document.createElement("section");
  section.className = "exercises";
  section.setAttribute("aria-labelledby", "exercises-title");
  const title = document.createElement("h2");
  title.id = "exercises-title";
  title.textContent = "Exercises";
  const list = document.createElement("ul");
  list.className = "exercise-list";
  const cards = new Map<string, HTMLElement>();
  for (const entry of orderedCatalog(state)) {
    const card = exerciseCard(entry, () => {
      cards.forEach((item, id) => {
        item.dataset.selected = String(id === entry.assessment_id);
        item.querySelector("button.select-exercise")
          ?.setAttribute("aria-pressed", String(id === entry.assessment_id));
      });
      onSelect(entry);
    });
    card.dataset.selected = String(entry.assessment_id === selection.entry.assessment_id);
    card.querySelector("button.select-exercise")
      ?.setAttribute("aria-pressed", card.dataset.selected);
    cards.set(entry.assessment_id, card);
    list.append(card);
  }
  section.append(title, list);
  return section;
}

function exerciseCard(entry: CatalogEntry, onSelect: () => void): HTMLElement {
  const item = document.createElement("li");
  item.className = "exercise-card";
  item.dataset.assessmentId = entry.assessment_id;
  const heading = document.createElement("h3");
  heading.textContent = entry.display_name;
  const badge = document.createElement("span");
  badge.className = `readiness readiness-${entry.available ? "ready" : "setup"}`;
  badge.textContent = entry.available ? "Ready" : "Setup required";
  const description = document.createElement("p");
  description.className = "exercise-description";
  description.textContent = entry.description || "Four-level local practice assessment.";
  const meta = document.createElement("p");
  meta.className = "exercise-meta";
  meta.textContent = entry.content_version
    ? `Content ${entry.content_version} · ${providerLabel(entry.provider_kind)}`
    : providerLabel(entry.provider_kind);
  item.append(heading, badge, description, meta);
  const select = button(`Select ${entry.display_name}`, "secondary");
  select.classList.add("select-exercise");
  select.dataset.available = String(entry.available);
  if (!entry.available) {
    const setup = document.createElement("p");
    setup.className = "setup-message";
    setup.id = `setup-${entry.assessment_id}`;
    setup.textContent = entry.setup_message ||
      "This exercise needs local setup before it can start.";
    item.append(setup);
    select.disabled = true;
    select.setAttribute("aria-describedby", setup.id);
  } else {
    select.addEventListener("click", onSelect);
  }
  item.append(select);
  return item;
}

function providerLabel(kind: string): string {
  return kind === "packaged-original" ? "Packaged original exercise" : "Locally prepared exercise";
}

type StartForm = {
  form: HTMLFormElement;
  start: HTMLButtonElement;
  status: HTMLElement;
  setExercise(entry: CatalogEntry): void;
  selection(): { mode: Mode; duration: number };
};

type StartDialog = {
  dialog: HTMLDialogElement;
  confirm: HTMLButtonElement;
  cancel: HTMLButtonElement;
  focus: ReturnType<typeof createDialogFocusTrap>;
};

function createStartForm(state: EntryState, selection: Selection): StartForm {
  const form = document.createElement("form");
  form.className = "format-form";
  const selected = document.createElement("p");
  selected.className = "selected-exercise";
  const fieldset = document.createElement("fieldset");
  const legend = document.createElement("legend");
  legend.textContent = "Choose a practice format";
  const start = button("Start practice", "primary");
  start.type = "submit";
  form.append(selected, fieldset, start);
  const status = document.createElement("p");
  status.className = "status";
  status.setAttribute("role", "status");
  status.textContent = state.bootstrap.session
    ? "An existing session is available to reconnect."
    : "No attempt has started.";
  let current = selection.entry;
  const setExercise = (entry: CatalogEntry): void => {
    current = entry;
    selected.textContent = `Selected exercise: ${entry.display_name}`;
    fieldset.replaceChildren(legend);
    for (const profile of entry.profiles) {
      fieldset.append(profileOption(profile.mode, profile.duration_seconds));
    }
    start.disabled = !entry.available;
  };
  setExercise(current);
  return {
    form,
    start,
    status,
    setExercise,
    selection: () => selectedProfile(form, current),
  };
}

function createConfirmation(): StartDialog {
  const dialog = document.createElement("dialog");
  dialog.className = "confirmation";
  dialog.setAttribute("aria-labelledby", "confirmation-title");
  dialog.setAttribute("aria-describedby", "confirmation-description");
  const title = document.createElement("h2");
  title.id = "confirmation-title";
  title.textContent = "Confirm start";
  const copy = document.createElement("p");
  copy.id = "confirmation-description";
  copy.textContent =
    "Starting creates one local practice attempt. The timer begins immediately and cannot be paused.";
  const confirm = button("Confirm and start", "primary");
  const cancel = button("Cancel", "secondary");
  dialog.append(title, copy, confirm, cancel);
  return {
    dialog,
    confirm,
    cancel,
    focus: createDialogFocusTrap(dialog, { initialFocus: confirm }),
  };
}

function connectStartControls(
  form: StartForm,
  dialog: StartDialog,
  selection: Selection,
  onStart: LibraryCallbacks["onStart"],
): void {
  form.form.addEventListener("submit", (event) => {
    event.preventDefault();
    if (!selection.entry.available) return;
    const copy = dialog.dialog.querySelector("#confirmation-description");
    if (copy) {
      copy.textContent =
        `Starting creates one local practice attempt of ${selection.entry.display_name}. ` +
        "The timer begins immediately and cannot be paused.";
    }
    dialog.focus.open(form.start);
  });
  dialog.cancel.addEventListener("click", () => dialog.focus.close());
  dialog.confirm.addEventListener("click", () => {
    const selected = form.selection();
    dialog.focus.close();
    onStart(selection.entry.assessment_id, selected.mode, selected.duration);
  });
}

function selectedProfile(
  form: HTMLFormElement,
  entry: CatalogEntry,
): { mode: Mode; duration: number } {
  const checked = form.querySelector<HTMLInputElement>("input:checked");
  const mode = checked?.value === "drill" ? "drill" : "full";
  const profile = entry.profiles.find((item) => item.mode === mode);
  if (!profile) throw new Error("selected practice format is unavailable");
  return { mode, duration: profile.duration_seconds };
}

function outline(entry: CatalogEntry): HTMLElement {
  const section = document.createElement("section");
  section.className = "exercise-outline";
  section.setAttribute("aria-labelledby", "outline-title");
  const title = document.createElement("h2");
  title.id = "outline-title";
  title.textContent = "Four-level outline";
  const intro = document.createElement("p");
  intro.textContent = `${entry.display_name} builds up over four levels; each level adds local practice checks.`;
  const list = document.createElement("ol");
  list.className = "outline";
  for (const item of entry.levels) {
    const level = document.createElement("li");
    level.textContent = `${item.label} · local practice checks`;
    list.append(level);
  }
  section.append(title, intro, list);
  return section;
}

function rules(state: EntryState): HTMLElement {
  const section = document.createElement("section");
  section.setAttribute("aria-labelledby", "rules-title");
  const title = document.createElement("h2");
  title.id = "rules-title";
  title.textContent = "Before you start";
  const list = document.createElement("ul");
  for (const rule of state.bootstrap.rules) {
    const item = document.createElement("li");
    item.textContent = rule;
    list.append(item);
  }
  const warning = document.createElement("p");
  warning.className = "warning";
  warning.textContent =
    "No pause: the server timer starts with your confirmed choice and remains authoritative.";
  section.append(title, list, warning);
  return section;
}

function profileOption(mode: Mode, duration: number): HTMLElement {
  const label = document.createElement("label");
  label.className = "format-option";
  const input = document.createElement("input");
  input.type = "radio";
  input.name = "practice-format";
  input.value = mode;
  input.checked = mode === "full";
  const text = document.createElement("span");
  text.textContent = `${mode === "full" ? "Full assessment" : "Focused drill"} · ${formatDuration(duration)}`;
  label.append(input, text);
  return label;
}

function button(label: string, kind: "primary" | "secondary"): HTMLButtonElement {
  const element = document.createElement("button");
  element.type = "button";
  element.className = kind;
  element.textContent = label;
  return element;
}

function formatDuration(seconds: number): string {
  const minutes = Math.floor(seconds / 60);
  return `${minutes} minutes`;
}
