import type {
  AttemptState,
  ConnectionState,
  PromptTab,
  ScoreSummary,
} from "./state";
import {
  focusFirstAction,
  createLiveRegion,
  type Disposable,
} from "./a11y";
import {
  createLevelNavigation,
  createPromptPane,
  type PromptElements,
  type LevelNavigation,
} from "./navigation_view";

export type ShellCallbacks = {
  onLevelSelect(level: number): void;
  onPromptTab(tab: PromptTab): void;
};

export type ShellElements = {
  editor: HTMLDivElement;
  fallback: HTMLTextAreaElement;
  status: HTMLElement;
  setCountdown(seconds: number): void;
  setConnection(connection: ConnectionState): void;
  setPromptLoading(level: number): void;
  setPrompt(prompt: string): void;
  setPromptError(): void;
  setSaveState(dirty: boolean): void;
  announce(message: string): void;
  focusInitial(): void;
  setControlsDisabled(disabled: boolean): void;
  setMutationControlsDisabled(disabled: boolean): void;
  destroy(): void;
};

export function buildAttemptShell(
  root: HTMLElement,
  state: AttemptState,
  callbacks: ShellCallbacks,
): ShellElements {
  root.replaceChildren();
  const main = element("main", "assessment-shell shell");
  main.dataset.attemptId = state.session.attempt_id;
  main.setAttribute("aria-labelledby", "assessment-title");
  const parts = createShellParts(state, callbacks);
  const live = createLiveRegion(main);
  main.append(
    parts.header,
    parts.levelNav.element,
    createWorkspace(parts.prompt, parts.editor, parts.output),
    parts.actions.bar,
  );
  root.append(main);
  const elements = bindShellElements(state, parts, live);
  elements.focusInitial();
  if (state.session.status !== "active") {
    elements.announce(
      terminalAnnouncement(state.session.status, state.session.score, state.source),
    );
  }
  return elements;
}

type ShellParts = {
  header: HeaderElements & HTMLElement;
  levelNav: LevelNavigation;
  prompt: PromptElements;
  editor: EditorElements;
  output: HTMLElement;
  actions: { bar: HTMLElement; buttons: HTMLButtonElement[] };
  disposables: Disposable[];
};

function createShellParts(
  state: AttemptState,
  callbacks: ShellCallbacks,
): ShellParts {
  const levelNav = createLevelNavigation(state, callbacks.onLevelSelect);
  const prompt = createPromptPane(state, callbacks.onPromptTab);
  return {
    header: createHeader(state),
    levelNav,
    prompt,
    editor: createEditorPane(state),
    output: createOutputPane(state.session.score, state.session.status),
    actions: createActionBar(),
    disposables: [
      { dispose: levelNav.dispose },
      { dispose: prompt.dispose },
    ],
  };
}

function bindShellElements(
  state: AttemptState,
  parts: ShellParts,
  live: ReturnType<typeof createLiveRegion>,
): ShellElements {
  const { header, levelNav, prompt, editor, actions } = parts;
  const controls = [
    ...levelNav.buttons,
    ...prompt.tabButtons,
    ...actions.buttons,
    header.saveButton,
    header.settingsButton,
  ];
  const mutationControls = controls.filter(
    (control) => control.dataset.mutation === "true",
  );
  return createElementApi(
    state,
    header,
    prompt,
    editor,
    levelNav.element,
    controls,
    mutationControls,
    parts.disposables,
    live,
  );
}

function createElementApi(
  state: AttemptState,
  header: HeaderElements & HTMLElement,
  prompt: PromptElements,
  editor: EditorElements,
  levelNav: HTMLElement,
  controls: HTMLButtonElement[],
  mutationControls: HTMLButtonElement[],
  disposables: Disposable[],
  live: ReturnType<typeof createLiveRegion>,
): ShellElements {
  const elements: ShellElements = {
    editor: editor.editor,
    fallback: editor.fallback,
    status: editor.status,
    ...createDisplayApi(state, header, prompt, live),
    ...createControlApi(levelNav, controls, mutationControls, disposables, live),
  };
  initializeShellElements(elements, state);
  return elements;
}

function createDisplayApi(
  state: AttemptState,
  header: HeaderElements & HTMLElement,
  prompt: PromptElements,
  live: ReturnType<typeof createLiveRegion>,
): Pick<
  ShellElements,
  | "setCountdown"
  | "setConnection"
  | "setPromptLoading"
  | "setPrompt"
  | "setPromptError"
  | "setSaveState"
  | "announce"
> {
  return {
    setCountdown: (seconds) => {
      header.timer.textContent = state.session.status === "submitted"
        ? "Final"
        : formatCountdown(seconds);
    },
    setConnection: (connection) => {
      header.connection.textContent =
        connection === "connected" ? "Connected" : "Reconnecting…";
    },
    setPromptLoading: (level) => {
      prompt.body.textContent = `Loading Level ${level} description…`;
      prompt.body.className = "prompt-copy prompt-loading";
    },
    setPrompt: (value) => {
      prompt.body.textContent = value;
      prompt.body.className = "prompt-copy";
    },
    setPromptError: () => {
      prompt.body.textContent =
        "This description is unavailable. The session remains unchanged.";
      prompt.body.className = "prompt-copy prompt-error";
    },
    setSaveState: (dirty) => {
      header.saveState.textContent = dirty ? "Unsaved local edits" : "Saved snapshot";
      if (dirty) live.announce("Unsaved local edits");
    },
    announce: (message) => live.announce(message),
  };
}

function createControlApi(
  levelNav: HTMLElement,
  controls: HTMLButtonElement[],
  mutationControls: HTMLButtonElement[],
  disposables: Disposable[],
  live: ReturnType<typeof createLiveRegion>,
): Pick<
  ShellElements,
  "focusInitial" | "setControlsDisabled" | "setMutationControlsDisabled" | "destroy"
> {
  return {
    focusInitial: () => focusFirstAction(levelNav),
    setControlsDisabled: (disabled) => {
      controls.forEach((control) => {
        control.disabled = disabled || control.dataset.enabled !== "true";
      });
    },
    setMutationControlsDisabled: (disabled) => {
      mutationControls.forEach((control) => {
        control.disabled = disabled || control.dataset.enabled !== "true";
      });
    },
    destroy: () => {
      disposables.forEach((disposable) => disposable.dispose());
      controls.forEach((control) => control.replaceWith(control.cloneNode(true)));
      live.dispose();
    },
  };
}

function initializeShellElements(
  elements: ShellElements,
  state: AttemptState,
): void {
  elements.setCountdown(state.time.remaining_seconds);
  elements.setConnection(state.connection);
  if (state.session.status !== "active") {
    elements.setMutationControlsDisabled(true);
  }
}

export function showEditor(elements: ShellElements): void {
  elements.editor.hidden = false;
  elements.fallback.hidden = true;
  elements.status.textContent = "Python editor ready. Changes stay in this local browser.";
}

export function showFallback(elements: ShellElements, message: string): void {
  elements.editor.hidden = true;
  elements.fallback.hidden = false;
  elements.fallback.readOnly = true;
  elements.setControlsDisabled(true);
  elements.status.textContent = `${message} Editing is disabled in the read-only fallback.`;
}

type HeaderElements = {
  timer: HTMLElement;
  connection: HTMLElement;
  saveState: HTMLElement;
  saveButton: HTMLButtonElement;
  settingsButton: HTMLButtonElement;
};

function createHeader(state: AttemptState): HeaderElements & HTMLElement {
  const header = element("header", "assessment-header");
  const titleGroup = element("div", "title-group");
  const title = element("h1");
  title.id = "assessment-title";
  title.textContent = state.bootstrap.assessment.display_name;
  const mode = element("p", "session-mode");
  mode.textContent = `Local practice session · ${state.session.profile?.mode || "selected"} format`;
  const deadline = element("p", "server-deadline");
  deadline.textContent = `Server deadline: ${state.session.deadline_at}`;
  titleGroup.append(title, mode, deadline);

  const meta = element("div", "header-meta");
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
  meta.append(
    timerGroup,
    lifecycle.container,
    save.container,
    connection.container,
    saveButton,
    settingsButton,
  );
  header.append(titleGroup, meta);
  return Object.assign(header, {
    timer,
    connection: connection.value,
    saveState: save.value,
    saveButton,
    settingsButton,
  });
}

type EditorElements = {
  element: HTMLElement;
  editor: HTMLDivElement;
  fallback: HTMLTextAreaElement;
  status: HTMLElement;
};

function createEditorPane(state: AttemptState): EditorElements {
  const pane = element("section", "editor-pane");
  pane.dataset.testid = "editor-pane";
  pane.setAttribute("aria-labelledby", "editor-title");
  const heading = element("div", "pane-heading");
  const title = element("h2");
  title.id = "editor-title";
  title.textContent = "Solution";
  const language = element("span", "pane-detail");
  language.textContent = "Python";
  heading.append(title, language);
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
  fallback.hidden = true;
  if (state.session.status !== "active") editor.hidden = true;
  pane.append(heading, status, editor, fallback);
  return { element: pane, editor, fallback, status };
}

function createOutputPane(
  score: ScoreSummary | null,
  status: AttemptState["session"]["status"],
): HTMLElement {
  const pane = element("aside", "output-drawer");
  pane.dataset.testid = "output-drawer";
  pane.setAttribute("aria-labelledby", "output-title");
  const heading = element("div", "pane-heading");
  const title = element("h2");
  title.id = "output-title";
  title.textContent = "Output";
  const limit = element("span", "pane-detail");
  limit.textContent = "Bounded preview";
  heading.append(title, limit);
  const content = element("p", "output-copy");
  content.textContent = score
    ? `${resultLabel(status)} · Passed levels: ${score.passed_levels} of ${score.levels.length}.`
    : status === "expired"
      ? "This attempt has expired. The server snapshot is final for this view."
      : "Test output will appear here after test wiring is enabled.";
  pane.append(heading, content);
  return pane;
}

function createWorkspace(
  prompt: PromptElements,
  editor: EditorElements,
  output: HTMLElement,
): HTMLElement {
  const workspace = element("div", "workspace-grid");
  workspace.append(prompt.element, editor.element, output);
  return workspace;
}

function createActionBar(): {
  bar: HTMLElement;
  buttons: HTMLButtonElement[];
} {
  const bar = element("footer", "action-bar");
  bar.setAttribute("role", "toolbar");
  bar.setAttribute("aria-label", "Assessment actions");
  const left = element("div", "action-group");
  const run = disabledButton("Run Tests", "secondary");
  left.append(run);
  const navigation = element("div", "action-group navigation-actions");
  const previous = disabledButton("Previous", "secondary");
  const skip = disabledButton("Skip", "secondary");
  const next = disabledButton("Next", "secondary");
  navigation.append(previous, skip, next);
  const right = element("div", "action-group");
  const reset = disabledButton("Reset", "secondary");
  const submit = disabledButton("Submit", "submit-action");
  right.append(reset, submit);
  bar.append(left, navigation, right);
  return { bar, buttons: [run, previous, skip, next, reset, submit] };
}

function statusItem(label: string, valueText: string): {
  container: HTMLElement;
  value: HTMLElement;
} {
  const container = element("div", "header-status");
  const labelElement = element("span", "meta-label");
  labelElement.textContent = label;
  const value = element("strong");
  value.textContent = valueText;
  container.append(labelElement, value);
  return { container, value };
}

function disabledButton(label: string, className: string): HTMLButtonElement {
  const result = button(label, className);
  result.disabled = true;
  if (["Run Tests", "Reset", "Submit"].includes(label)) {
    result.dataset.mutation = "true";
  }
  return result;
}

function button(label: string, className: string): HTMLButtonElement {
  const result = document.createElement("button");
  result.type = "button";
  result.className = className;
  result.textContent = label;
  return result;
}

function element<K extends keyof HTMLElementTagNameMap>(
  tag: K,
  className = "",
): HTMLElementTagNameMap[K] {
  const result = document.createElement(tag);
  if (className) result.className = className;
  return result;
}

function terminalEditorMessage(status: AttemptState["session"]["status"]): string {
  return status === "submitted"
    ? "This attempt is submitted. Editing is unavailable."
    : "This attempt is expired. Editing is unavailable.";
}

function lifecycleLabel(status: AttemptState["session"]["status"]): string {
  return status === "active" ? "Active" : status === "expired" ? "Expired" : "Submitted";
}

function resultLabel(status: AttemptState["session"]["status"]): string {
  return status === "submitted" ? "Final result" : "Practice result";
}

function terminalAnnouncement(
  status: AttemptState["session"]["status"],
  score: ScoreSummary | null,
  source: string | null,
): string {
  const sourceMessage = source === null
    ? "Source is unavailable."
    : "Source remains available.";
  if (status === "expired") {
    return `Attempt expired. ${sourceMessage} Results remain available in read-only mode.`;
  }
  if (score) {
    return `Final result announced. Passed levels: ${score.passed_levels} of ${score.levels.length}. ${sourceMessage} Results are final and read-only.`;
  }
  return `Attempt submitted. ${sourceMessage} Results are final and read-only.`;
}

function formatCountdown(seconds: number): string {
  const safeSeconds = Math.max(0, Math.floor(seconds));
  const hours = Math.floor(safeSeconds / 3600);
  const minutes = Math.floor((safeSeconds % 3600) / 60);
  const remainder = safeSeconds % 60;
  if (hours > 0) return `${hours}:${pad(minutes)}:${pad(remainder)}`;
  return `${pad(minutes)}:${pad(remainder)}`;
}

function pad(value: number): string {
  return String(value).padStart(2, "0");
}
