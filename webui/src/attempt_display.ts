import type {
  AttemptState,
  ConnectionState,
  PracticeResult,
  ScoreSummary,
} from "./state";
import type { SourceDocument, SourceHistory } from "./source_api";
import { createLiveRegion } from "./a11y";
import type { EditorElements, HeaderElements, ShellElements } from "./attempt_types";
import type { SourceSaveStatus } from "./source_state";
import { formatCountdown, element } from "./attempt_dom";

export function createDisplayApi(
  state: AttemptState,
  header: HeaderElements & HTMLElement,
  prompt: {
    setHistoryLoading(): void;
    setHistoryError(): void;
    setHistory(
      history: SourceHistory,
      onRestore: (snapshotId: string, opener: HTMLElement) => void,
    ): void;
    body: HTMLElement;
  },
  editor: EditorElements,
  output: HTMLElement & {
    render?(
      score: ScoreSummary | null,
      status: AttemptState["session"]["status"],
      practice: PracticeResult | null,
    ): void;
  },
  live: ReturnType<typeof createLiveRegion>,
): Pick<
  ShellElements,
  | "setCountdown"
  | "setConnection"
  | "setPromptLoading"
  | "setPrompt"
  | "setPromptError"
  | "setHistoryLoading"
  | "setHistoryError"
  | "setHistory"
  | "setSaveState"
  | "setConflict"
  | "clearConflict"
  | "setResults"
  | "announce"
> {
  return {
    setCountdown: (seconds) => {
      header.timer.textContent = state.session.status === "submitted"
        ? "Final"
        : formatCountdown(seconds);
    },
    setConnection: (connection) => setConnectionStatus(header, connection),
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
    setHistoryLoading: () => {
      prompt.body.textContent = "Loading candidate source history…";
      prompt.body.className = "prompt-copy prompt-loading";
    },
    setHistoryError: () => {
      prompt.body.textContent =
        "Candidate source history unavailable. The session remains unchanged.";
      prompt.body.className = "prompt-copy prompt-error";
    },
    setHistory: (history, onRestore) => prompt.setHistory(history, onRestore),
    setSaveState: (status) => setSaveStatus(header, live, status),
    setConflict: (server, choices) =>
      showConflict(editor, server, choices),
    clearConflict: () => clearConflict(editor),
    setResults: (score, status, practice) =>
      output.render?.(score, status, practice),
    announce: (message) => live.announce(message),
  };
}

function setConnectionStatus(
  header: HeaderElements,
  connection: ConnectionState,
): void {
  header.connection.textContent =
    connection === "connected" ? "Connected" : "Reconnecting…";
}

function setSaveStatus(
  header: HeaderElements,
  live: ReturnType<typeof createLiveRegion>,
  status: SourceSaveStatus,
): void {
  const labels = {
    clean: "Saved snapshot",
    dirty: "Unsaved local edits",
    saving: "Saving…",
    conflict: "Conflict — choose a version",
    failed: "Save failed — retry",
  } as const;
  header.saveState.textContent = labels[status];
  header.saveButton.disabled = status !== "failed";
  live.announce(labels[status]);
}

function showConflict(
  editor: EditorElements,
  server: SourceDocument,
  choices: { keepLocal(): void; reloadServer(): void },
): void {
  editor.conflict.replaceChildren();
  const title = element("strong");
  title.textContent = "Server version (bounded preview)";
  const preview = element("pre");
  preview.textContent = server.content.slice(0, 512);
  const keep = button("Copy local version", "secondary");
  const reload = button("Reload server version", "secondary");
  keep.addEventListener("click", choices.keepLocal);
  reload.addEventListener("click", choices.reloadServer);
  editor.conflict.append(title, preview, keep, reload);
  editor.conflict.hidden = false;
}

function clearConflict(editor: EditorElements): void {
  editor.conflict.hidden = true;
  editor.conflict.replaceChildren();
}

function button(label: string, className: string): HTMLButtonElement {
  const result = document.createElement("button");
  result.type = "button";
  result.className = className;
  result.textContent = label;
  return result;
}
