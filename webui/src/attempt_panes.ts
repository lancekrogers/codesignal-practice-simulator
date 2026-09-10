import type { AttemptState, PracticeResult, ScoreSummary } from "./state";
import {
  createOutputPane as createResultsPane,
  type OutputElements,
} from "./attempt_results";
import {
  button,
  disabledButton,
  element,
  lifecycleLabel,
  statusItem,
  terminalEditorMessage,
} from "./attempt_dom";
import type { EditorElements, HeaderElements } from "./attempt_types";

export function createHeader(state: AttemptState): HeaderElements & HTMLElement {
  const header = element("header", "assessment-header");
  const titleGroup = createTitleGroup(state);
  const meta = createHeaderMeta(state);
  header.append(titleGroup, meta.container);
  return Object.assign(header, {
    timer: meta.timer,
    connection: meta.connection,
    saveState: meta.saveState,
    saveButton: meta.saveButton,
    settingsButton: meta.settingsButton,
  });
}

function createTitleGroup(state: AttemptState): HTMLElement {
  const titleGroup = element("div", "title-group");
  const title = element("h1");
  title.id = "assessment-title";
  title.textContent = state.bootstrap.assessment.display_name;
  const mode = element("p", "session-mode");
  mode.textContent = `Local practice session · ${state.session.profile.mode} format`;
  const deadline = element("p", "server-deadline");
  deadline.textContent = `Server deadline: ${state.session.deadline_at}`;
  titleGroup.append(title, mode, deadline);
  return titleGroup;
}

function createHeaderMeta(state: AttemptState): {
  container: HTMLElement;
  timer: HTMLElement;
  connection: HTMLElement;
  saveState: HTMLElement;
  saveButton: HTMLButtonElement;
  settingsButton: HTMLButtonElement;
} {
  const container = element("div", "header-meta");
  const timerGroup = element("div", "timer-group");
  const timerLabel = element("span", "meta-label");
  timerLabel.textContent = "Time remaining";
  const timer = element("strong");
  timer.setAttribute("role", "timer");
  timer.setAttribute("aria-label", "Time remaining");
  timerGroup.append(timerLabel, timer);
  const save = statusItem("Save", "Saved snapshot");
  const connection = statusItem("Connection", "Connected");
  const lifecycle = statusItem("Session", lifecycleLabel(state.session.status));
  const saveButton = button("Save", "secondary");
  saveButton.disabled = true;
  saveButton.dataset.mutation = "true";
  saveButton.setAttribute("aria-label", "Save changes");
  const settingsButton = button("Settings", "secondary");
  settingsButton.disabled = true;
  settingsButton.dataset.mutation = "true";
  settingsButton.dataset.enabled = "true";
  container.append(
    timerGroup,
    lifecycle.container,
    save.container,
    connection.container,
    saveButton,
    settingsButton,
  );
  return {
    container,
    timer,
    connection: connection.value,
    saveState: save.value,
    saveButton,
    settingsButton,
  };
}

export function createEditorPane(state: AttemptState): EditorElements {
  const pane = element("section", "editor-pane");
  pane.dataset.testid = "editor-pane";
  pane.setAttribute("aria-labelledby", "editor-title");
  const heading = createEditorHeading();
  const status = element("p", "status");
  status.setAttribute("role", "status");
  status.textContent = state.session.status === "active"
    ? "Loading the local Python editor…"
    : terminalEditorMessage(state.session.status);
  const editor = element("div", "editor");
  editor.setAttribute("aria-label", "Python source editor");
  const fallback = element("textarea", "fallback") as HTMLTextAreaElement;
  fallback.readOnly = true;
  fallback.setAttribute("aria-label", "Read-only Python source fallback");
  fallback.value = state.source || "";
  const terminal = state.session.status !== "active";
  fallback.hidden = !terminal;
  editor.hidden = terminal;
  const conflict = element("section", "source-conflict");
  conflict.hidden = true;
  conflict.setAttribute("aria-live", "polite");
  pane.append(heading, status, conflict, editor, fallback);
  return { element: pane, editor, fallback, status, conflict };
}

function createEditorHeading(): HTMLElement {
  const heading = element("div", "pane-heading");
  const title = element("h2");
  title.id = "editor-title";
  title.textContent = "Solution";
  const language = element("span", "pane-detail");
  language.textContent = "Python";
  heading.append(title, language);
  return heading;
}

export function createOutputPane(
  score: ScoreSummary | null,
  status: AttemptState["session"]["status"],
  practice: PracticeResult | null,
): OutputElements {
  return createResultsPane(score, status, practice);
}

export function createWorkspace(
  prompt: HTMLElement,
  editor: HTMLElement,
  output: HTMLElement,
): HTMLElement {
  const workspace = element("div", "workspace-grid");
  workspace.append(prompt, editor, output);
  return workspace;
}

export function createActionBar(
  initialLevel: number,
  onReset: (opener: HTMLElement) => void,
  onNavigate: (direction: "previous" | "next" | "skip") => void,
  onRunTests: (opener: HTMLElement) => void,
  onSubmit: (opener: HTMLElement) => void,
  mutationEnabled: boolean,
): {
  bar: HTMLElement;
  buttons: HTMLButtonElement[];
  setNavigationLevel(level: number): void;
} {
  const bar = element("footer", "action-bar");
  bar.setAttribute("role", "toolbar");
  bar.setAttribute("aria-label", "Assessment actions");
  const left = element("div", "action-group");
  const run = button("Run Tests", "secondary");
  run.dataset.mutation = "true";
  run.dataset.enabled = String(mutationEnabled);
  run.disabled = !mutationEnabled;
  run.addEventListener("click", () => onRunTests(run));
  left.append(run);
  const navigation = createNavigationActions(onNavigate);
  const right = element("div", "action-group");
  const reset = disabledButton("Reset", "secondary");
  reset.dataset.mutation = "true";
  reset.addEventListener("click", () => onReset(reset));
  const submit = button("Submit", "submit-action");
  submit.dataset.mutation = "true";
  submit.dataset.enabled = String(mutationEnabled);
  submit.disabled = !mutationEnabled;
  submit.addEventListener("click", () => onSubmit(submit));
  right.append(reset, submit);
  bar.append(left, navigation.element, right);
  navigation.setNavigationLevel(initialLevel);
  return {
    bar,
    buttons: [run, ...navigation.buttons, reset, submit],
    setNavigationLevel: navigation.setNavigationLevel,
  };
}

function createNavigationActions(
  onNavigate: (direction: "previous" | "next" | "skip") => void,
): {
  element: HTMLElement;
  buttons: HTMLButtonElement[];
  setNavigationLevel(level: number): void;
} {
  const element = document.createElement("div");
  element.className = "action-group navigation-actions";
  const previous = button("Previous", "secondary");
  const skip = button("Skip", "secondary");
  const next = button("Next", "secondary");
  previous.addEventListener("click", () => onNavigate("previous"));
  skip.addEventListener("click", () => onNavigate("skip"));
  next.addEventListener("click", () => onNavigate("next"));
  const buttons = [previous, skip, next];
  element.append(...buttons);
  return {
    element,
    buttons,
    setNavigationLevel(level): void {
      previous.disabled = level <= 1;
      skip.disabled = level >= 4;
      next.disabled = level >= 4;
    },
  };
}
