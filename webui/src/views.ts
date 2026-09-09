import type {
  AttemptState,
  BootingState,
  EntryState,
  Mode,
  BrowserState,
  PromptTab,
} from "./state";
import {
  buildAttemptShell,
  showEditor,
  showFallback,
  type ShellCallbacks,
  type ShellElements,
} from "./attempt_view";
import { createDialogFocusTrap } from "./a11y";

export type { ShellElements };
export { showEditor, showFallback };

export function renderBooting(root: HTMLElement, _state: BootingState): void {
  root.replaceChildren();
  const main = document.createElement("main");
  main.className = "shell loading-state";
  main.setAttribute("aria-live", "polite");
  const heading = document.createElement("h1");
  heading.textContent = "Practice Simulator";
  const status = document.createElement("p");
  status.className = "status";
  status.textContent = "Loading the local assessment…";
  main.append(heading, status);
  root.append(main);
}

export function renderReconnect(root: HTMLElement, state: EntryState): void {
  root.replaceChildren();
  const main = document.createElement("main");
  main.className = "shell loading-state";
  main.setAttribute("aria-labelledby", "reconnect-title");
  const heading = document.createElement("h1");
  heading.id = "reconnect-title";
  heading.textContent = state.bootstrap.assessment.display_name;
  const status = document.createElement("p");
  status.className = "status";
  status.setAttribute("role", "status");
  status.textContent = "Reconnecting to the selected session…";
  main.append(heading, status);
  root.append(main);
}

export function renderError(
  root: HTMLElement,
  state: BrowserState,
  recovery?: { label: string; onClick(): void },
): void {
  root.replaceChildren();
  const main = document.createElement("main");
  main.className = "shell error-state";
  const heading = document.createElement("h1");
  heading.textContent = "Assessment unavailable";
  const message = document.createElement("p");
  message.className = "error-message";
  message.setAttribute("role", "alert");
  message.id = "assessment-error";
  main.setAttribute("aria-labelledby", "assessment-error-title");
  heading.id = "assessment-error-title";
  message.textContent = state.phase === "error"
    ? state.message
    : "The local assessment could not be loaded.";
  main.append(heading, message);
  if (recovery) {
    const action = button(recovery.label, "primary");
    action.addEventListener("click", recovery.onClick);
    main.append(action);
  }
  root.append(main);
}

export function renderEntry(
  root: HTMLElement,
  state: EntryState,
  onStart: (mode: Mode, duration: number) => void,
  onReconnect: (() => void) | undefined,
): EntryElements {
  root.replaceChildren();
  const main = document.createElement("main");
  main.className = "shell entry";
  main.setAttribute("aria-labelledby", "assessment-title");
  if (state.bootstrap.session) {
    main.dataset.activeAttemptId = state.bootstrap.session.attempt_id;
  }
  main.append(entryHeader(state), outline(state), rules(state));
  const form = createEntryForm(state);
  const dialog = createConfirmation();
  main.append(form.form, form.status, dialog.dialog);
  if (onReconnect && state.bootstrap.session) {
    const reconnect = button(
      state.bootstrap.session.status === "active"
        ? "Reconnect to active session"
        : "View final session",
      "secondary",
    );
    reconnect.addEventListener("click", onReconnect);
    main.append(reconnect);
  }
  root.append(main);
  connectEntryControls(form, dialog, onStart);
  return {
    start: form.start,
    confirm: dialog.confirm,
    cancel: dialog.cancel,
    dialog: dialog.dialog,
    status: form.status,
    setBusy: (busy) => {
      form.start.disabled = busy;
      dialog.confirm.disabled = busy;
      dialog.cancel.disabled = busy;
      form.form.querySelectorAll("input").forEach((input) => {
        input.disabled = busy;
      });
    },
    setMessage: (message) => {
      form.status.textContent = message;
    },
    destroy: () => dialog.focus.dispose(),
  };
}

export function renderAttemptShell(
  root: HTMLElement,
  state: AttemptState,
  callbacks: ShellCallbacks,
): ShellElements {
  return buildAttemptShell(root, state, callbacks);
}

export type EntryElements = {
  start: HTMLButtonElement;
  confirm: HTMLButtonElement;
  cancel: HTMLButtonElement;
  dialog: HTMLDialogElement;
  status: HTMLElement;
  setBusy(busy: boolean): void;
  setMessage(message: string): void;
  destroy(): void;
};

type EntryForm = {
  form: HTMLFormElement;
  start: HTMLButtonElement;
  status: HTMLElement;
  selection(): { mode: Mode; duration: number };
};

type EntryDialog = {
  dialog: HTMLDialogElement;
  confirm: HTMLButtonElement;
  cancel: HTMLButtonElement;
  focus: ReturnType<typeof createDialogFocusTrap>;
};

function createEntryForm(state: EntryState): EntryForm {
  const form = document.createElement("form");
  form.className = "format-form";
  const fieldset = document.createElement("fieldset");
  const legend = document.createElement("legend");
  legend.textContent = "Choose a practice format";
  fieldset.append(legend);
  for (const profile of state.bootstrap.profiles) {
    fieldset.append(profileOption(profile.mode, profile.duration_seconds));
  }
  const start = button("Start practice", "primary");
  start.type = "submit";
  form.append(fieldset, start);
  const status = document.createElement("p");
  status.className = "status";
  status.setAttribute("role", "status");
  status.textContent = state.bootstrap.session
    ? "An existing session is available to reconnect."
    : "No attempt has started.";
  return { form, start, status, selection: () => selectedProfile(form, state) };
}

function createConfirmation(): EntryDialog {
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

function connectEntryControls(
  form: EntryForm,
  dialog: EntryDialog,
  onStart: (mode: Mode, duration: number) => void,
): void {
  form.form.addEventListener("submit", (event) => {
    event.preventDefault();
    dialog.focus.open(form.start);
  });
  dialog.cancel.addEventListener("click", () => dialog.focus.close());
  dialog.confirm.addEventListener("click", () => {
    const selected = form.selection();
    dialog.focus.close();
    onStart(selected.mode, selected.duration);
  });
}

function selectedProfile(
  form: HTMLFormElement,
  state: EntryState,
): { mode: Mode; duration: number } {
  const checked = form.querySelector<HTMLInputElement>("input:checked");
  const mode = checked?.value === "drill" ? "drill" : "full";
  const profile = state.bootstrap.profiles.find((item) => item.mode === mode);
  if (!profile) throw new Error("selected practice format is unavailable");
  return { mode, duration: profile.duration_seconds };
}

function entryHeader(state: EntryState): HTMLElement {
  const header = document.createElement("header");
  const title = document.createElement("h1");
  title.id = "assessment-title";
  title.textContent = state.bootstrap.assessment.display_name;
  const framing = document.createElement("p");
  framing.textContent =
    "A local practice assessment with checks designed to help you rehearse the workflow.";
  header.append(title, framing);
  return header;
}

function outline(state: EntryState): HTMLElement {
  const section = document.createElement("section");
  section.setAttribute("aria-labelledby", "outline-title");
  const title = document.createElement("h2");
  title.id = "outline-title";
  title.textContent = "Four-level outline";
  const list = document.createElement("ol");
  list.className = "outline";
  for (const item of state.bootstrap.levels) {
    const level = document.createElement("li");
    level.textContent = `${item.label} · local practice checks`;
    list.append(level);
  }
  section.append(title, list);
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
