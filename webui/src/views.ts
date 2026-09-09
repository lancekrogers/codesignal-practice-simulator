import type { BrowserState } from "./state";

export type ShellElements = {
  editor: HTMLDivElement;
  fallback: HTMLTextAreaElement;
  status: HTMLElement;
};

export function renderShell(root: HTMLElement, state: BrowserState): ShellElements {
  root.replaceChildren();
  const main = document.createElement("main");
  main.className = "shell";
  main.setAttribute("aria-live", "polite");
  main.append(header(state), editorHeading(state));

  const status = document.createElement("p");
  status.className = "status";
  status.textContent = "Loading the local Python editor…";
  main.append(status);

  const editor = document.createElement("div");
  editor.className = "editor";
  editor.setAttribute("aria-label", "Python source editor");
  main.append(editor);

  const fallback = document.createElement("textarea");
  fallback.className = "fallback";
  fallback.readOnly = true;
  fallback.setAttribute("aria-label", "Read-only Python source fallback");
  fallback.value = state.source || "# Start an attempt to load candidate source.\n";
  fallback.hidden = true;
  main.append(fallback);
  root.append(main);
  return { editor, fallback, status };
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
  elements.status.textContent = `${message} Editing is disabled in the read-only fallback.`;
}

function header(state: BrowserState): HTMLElement {
  const header = document.createElement("header");
  const title = document.createElement("h1");
  title.textContent = state.bootstrap?.assessment?.display_name || "Practice Simulator";
  const note = document.createElement("p");
  note.textContent = state.bootstrap?.session
    ? `Attempt ${state.bootstrap.session.attempt_id}`
    : "Offline local assessment shell";
  header.append(title, note);
  return header;
}

function editorHeading(state: BrowserState): HTMLElement {
  const heading = document.createElement("div");
  heading.className = "editor-heading";
  const title = document.createElement("h2");
  title.textContent = "Python source";
  const detail = document.createElement("span");
  detail.textContent = state.bootstrap?.session ? "Candidate file" : "No attempt selected";
  heading.append(title, detail);
  return heading;
}
