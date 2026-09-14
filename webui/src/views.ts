import type {
  AttemptState,
  BootingState,
  EntryState,
  BrowserState,
} from "./state";
import {
  buildAttemptShell,
  showEditor,
  showFallback,
  type ShellCallbacks,
  type ShellElements,
} from "./attempt_view";

export type { ShellElements };
export { showEditor, showFallback };

export type Recovery = { label: string; onClick(): void; kind?: "primary" | "secondary" };

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

export function renderReconnect(
  root: HTMLElement,
  state: EntryState,
  title = state.bootstrap.assessment.display_name,
): void {
  root.replaceChildren();
  const main = document.createElement("main");
  main.className = "shell loading-state";
  main.setAttribute("aria-labelledby", "reconnect-title");
  const heading = document.createElement("h1");
  heading.id = "reconnect-title";
  heading.textContent = title;
  const status = document.createElement("p");
  status.className = "status";
  status.setAttribute("role", "status");
  status.textContent = "Reconnecting to the selected session…";
  main.append(heading, status);
  root.append(main);
}

/**
 * Error screen with one or more recovery actions. The first action is the
 * primary one; every action stays keyboard reachable and the heading receives
 * focus so screen readers announce the failure.
 */
export function renderError(
  root: HTMLElement,
  state: BrowserState,
  recovery?: Recovery | Recovery[],
  title = "Assessment unavailable",
): HTMLElement {
  root.replaceChildren();
  const main = document.createElement("main");
  main.className = "shell error-state";
  const heading = document.createElement("h1");
  heading.textContent = title;
  heading.tabIndex = -1;
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
  const actions = recovery === undefined ? [] : Array.isArray(recovery) ? recovery : [recovery];
  if (actions.length > 0) {
    const group = document.createElement("div");
    group.className = "action-group";
    actions.forEach((action, index) => {
      const control = button(action.label, action.kind || (index === 0 ? "primary" : "secondary"));
      control.addEventListener("click", action.onClick);
      group.append(control);
    });
    main.append(group);
  }
  root.append(main);
  return heading;
}

/** A metadata-only screen with a heading, a status line and navigation actions. */
export function renderNotice(
  root: HTMLElement,
  options: {
    className: string;
    title: string;
    message: string;
    actions: Recovery[];
  },
): HTMLElement {
  root.replaceChildren();
  const main = document.createElement("main");
  main.className = `shell notice-state ${options.className}`;
  main.setAttribute("aria-labelledby", "notice-title");
  const heading = document.createElement("h1");
  heading.id = "notice-title";
  heading.tabIndex = -1;
  heading.textContent = options.title;
  const status = document.createElement("p");
  status.className = "status";
  status.setAttribute("role", "status");
  status.textContent = options.message;
  const group = document.createElement("div");
  group.className = "action-group";
  options.actions.forEach((action, index) => {
    const control = button(action.label, action.kind || (index === 0 ? "primary" : "secondary"));
    control.addEventListener("click", action.onClick);
    group.append(control);
  });
  main.append(heading, status, group);
  root.append(main);
  return heading;
}

export function renderAttemptShell(
  root: HTMLElement,
  state: AttemptState,
  callbacks: ShellCallbacks,
): ShellElements {
  return buildAttemptShell(root, state, callbacks);
}

function button(label: string, kind: "primary" | "secondary"): HTMLButtonElement {
  const element = document.createElement("button");
  element.type = "button";
  element.className = kind;
  element.textContent = label;
  return element;
}
