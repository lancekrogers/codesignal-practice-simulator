import { createLiveRegion } from "./a11y";
import { createConfirmationDialog, type ConfirmationDialog } from "./confirmation_dialog";
import type { AttemptState } from "./state";
import {
  createLevelNavigation,
  createPromptPane,
} from "./navigation_view";
import {
  createActionBar,
  createEditorPane,
  createHeader,
  createOutputPane,
  createWorkspace,
} from "./attempt_panes";
import { createControlApi } from "./attempt_controls";
import { createDisplayApi } from "./attempt_display";
import type {
  ShellCallbacks,
  ShellElements,
  ShellParts,
} from "./attempt_types";
import { terminalAnnouncement } from "./attempt_dom";

export function buildAttemptShell(
  root: HTMLElement,
  state: AttemptState,
  callbacks: ShellCallbacks,
): ShellElements {
  root.replaceChildren();
  const main = createShellMain(state);
  const parts = createShellParts(state, callbacks);
  const live = createLiveRegion(main);
  const confirmation = createConfirmationDialog(main);
  main.append(
    parts.header,
    parts.levelNav.element,
    createWorkspace(parts.prompt.element, parts.editor.element, parts.output),
    parts.actions.bar,
  );
  root.append(main);
  const elements = bindShellElements(state, parts, live, confirmation);
  elements.focusInitial();
  announceTerminalState(state, elements);
  return elements;
}

function createShellMain(state: AttemptState): HTMLElement {
  const main = document.createElement("main");
  main.className = "assessment-shell shell";
  main.dataset.attemptId = state.session.attempt_id;
  main.setAttribute("aria-labelledby", "assessment-title");
  return main;
}

function createShellParts(
  state: AttemptState,
  callbacks: ShellCallbacks,
): ShellParts {
  const levelNav = createLevelNavigation(state, callbacks.onLevelSelect);
  const prompt = createPromptPane(state, callbacks.onPromptTab);
  const header = createHeader(state);
  header.saveButton.addEventListener("click", callbacks.onSave);
  return {
    header,
    levelNav,
    prompt,
    editor: createEditorPane(state),
    output: createOutputPane(
      state.session.score,
      state.session.status,
      state.practice,
    ),
    actions: createActionBar(
      state.selectedLevel,
      callbacks.onReset,
      callbacks.onLevelNavigate,
      callbacks.onRunTests,
      callbacks.onSubmit,
      state.session.status === "active",
    ),
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
  confirmation: ConfirmationDialog,
): ShellElements {
  const controls = collectControls(parts);
  const mutationControls = controls.filter(
    (control) => control.dataset.mutation === "true",
  );
  return createElementApi(
    state,
    parts,
    controls,
    mutationControls,
    live,
    confirmation,
  );
}

function collectControls(parts: ShellParts): HTMLButtonElement[] {
  return [
    ...parts.levelNav.buttons,
    ...parts.prompt.tabButtons,
    ...parts.actions.buttons,
    parts.header.saveButton,
    parts.header.settingsButton,
  ];
}

function createElementApi(
  state: AttemptState,
  parts: ShellParts,
  controls: HTMLButtonElement[],
  mutationControls: HTMLButtonElement[],
  live: ReturnType<typeof createLiveRegion>,
  confirmation: ConfirmationDialog,
): ShellElements {
  const { header, prompt, editor, levelNav } = parts;
  const display = createDisplayApi(
    state,
    header,
    prompt,
    editor,
    parts.output,
    live,
  );
  const control = createControlApi(
    state,
    levelNav,
    parts.actions,
    controls,
    mutationControls,
    parts.disposables,
    live,
    confirmation,
    editor,
  );
  const elements = {
    editor: editor.editor,
    fallback: editor.fallback,
    status: editor.status,
    settingsButton: header.settingsButton,
    ...display,
    ...control,
  };
  initializeShellElements(elements, state);
  return elements;
}

function initializeShellElements(
  elements: ShellElements,
  state: AttemptState,
): void {
  elements.setCountdown(state.time.remaining_seconds);
  elements.setConnection(state.connection);
  elements.setNavigationLevel(state.selectedLevel);
  elements.setActionState(state.action);
  if (state.session.status !== "active") {
    elements.setMutationControlsDisabled(true);
  } else {
    elements.setResetEnabled(true);
  }
}

function announceTerminalState(
  state: AttemptState,
  elements: ShellElements,
): void {
  if (state.session.status !== "active") {
    elements.announce(
      terminalAnnouncement(state.session.status, state.session.score, state.source),
    );
  }
}

export function showEditor(elements: ShellElements): void {
  elements.editor.hidden = false;
  elements.fallback.hidden = true;
  elements.settingsButton.disabled = false;
  elements.status.textContent = "Python editor ready. Changes stay in this local browser.";
}

export function showFallback(
  elements: ShellElements,
  message: string,
  source?: string,
): void {
  elements.editor.hidden = true;
  elements.fallback.hidden = false;
  elements.fallback.readOnly = true;
  if (source !== undefined) elements.fallback.value = source;
  elements.setMutationControlsDisabled(true);
  elements.status.textContent =
    `${message} Reload the local simulator to retry; editing is disabled in the ` +
    "read-only fallback.";
}
