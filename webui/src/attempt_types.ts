import type { AttemptState, ConnectionState } from "./state";
import type { PromptTab } from "./view_state";
import type { Disposable } from "./a11y";
import type { SourceDocument, SourceHistory } from "./source_api";
import type { SourceSaveStatus } from "./source_state";
import type { LevelNavigation, PromptElements } from "./navigation_view";
import type { OutputElements } from "./attempt_results";
import type { ActionState, PracticeResult, ScoreSummary } from "./state";

export type ShellCallbacks = {
  onLevelSelect(level: number): void;
  onLevelNavigate(direction: "previous" | "next" | "skip"): void;
  onPromptTab(tab: PromptTab): void;
  onSave(): void;
  onLeave(opener: HTMLElement): void;
  onRunTests(opener: HTMLElement): void;
  onSubmit(opener: HTMLElement): void;
  onRestore(snapshotId: string, opener: HTMLElement): void;
  onReset(opener: HTMLElement): void;
  onEnd(opener: HTMLElement): void;
  onRestart(opener: HTMLElement): void;
};

export type ShellElements = {
  editor: HTMLDivElement;
  fallback: HTMLTextAreaElement;
  status: HTMLElement;
  settingsButton: HTMLButtonElement;
  setCountdown(seconds: number): void;
  setConnection(connection: ConnectionState): void;
  setPromptLoading(level: number): void;
  setPrompt(prompt: string): void;
  setPromptError(): void;
  setHistoryLoading(): void;
  setHistoryError(): void;
  setHistory(
    history: SourceHistory,
    onRestore: (snapshotId: string, opener: HTMLElement) => void,
  ): void;
  setSaveState(status: SourceSaveStatus): void;
  setConflict(
    server: SourceDocument,
    choices: { keepLocal(): void; reloadServer(): void },
  ): void;
  clearConflict(): void;
  announce(message: string): void;
  setActionState(state: ActionState): void;
  setOperationBusy(busy: boolean): void;
  setResults(
    score: ScoreSummary | null,
    status: AttemptState["session"]["status"],
    practice: PracticeResult | null,
  ): void;
  focusInitial(): void;
  focusLevel(level: number): void;
  refreshLevelStatus(): void;
  setNavigationLevel(level: number): void;
  setControlsDisabled(disabled: boolean): void;
  setMutationControlsDisabled(disabled: boolean): void;
  setResetEnabled(enabled: boolean): void;
  confirmAction(
    title: string,
    description: string,
    confirmLabel: string,
    opener: HTMLElement,
    onConfirm: () => void,
  ): void;
  destroy(): void;
};

export type HeaderElements = {
  leaveButton: HTMLButtonElement;
  timer: HTMLElement;
  connection: HTMLElement;
  saveState: HTMLElement;
  saveButton: HTMLButtonElement;
  settingsButton: HTMLButtonElement;
};

export type EditorElements = {
  element: HTMLElement;
  editor: HTMLDivElement;
  fallback: HTMLTextAreaElement;
  status: HTMLElement;
  conflict: HTMLElement;
};

export type ShellParts = {
  header: HeaderElements & HTMLElement;
  levelNav: LevelNavigation;
  prompt: PromptElements;
  editor: EditorElements;
  output: OutputElements;
  actions: {
    bar: HTMLElement;
    buttons: HTMLButtonElement[];
    setNavigationLevel(level: number): void;
  };
  disposables: Disposable[];
};
