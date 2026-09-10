import { apiGet } from "./api";
import {
  normalizePrompt,
  type AttemptState,
} from "./state";
import {
  writeAttemptViewState,
  type PromptTab,
} from "./view_state";
import type { ShellElements } from "./views";
import { loadSourceHistory } from "./source_api";

type PromptRequest = {
  generation: number;
  level: number;
  tab: PromptTab;
};

export type PromptController = {
  selectLevel(level: number): void;
  selectTab(tab: PromptTab): void;
  loadInitial(): void;
  dispose(): void;
};

export function createPromptController(
  elements: ShellElements,
  state: AttemptState,
  onRestore: (snapshotId: string, opener: HTMLElement) => void,
): PromptController {
  const runtime = createPromptRuntime(elements, state, onRestore);
  return {
    selectLevel: (level) => selectLevel(runtime, level),
    selectTab: (tab) => selectTab(runtime, tab),
    loadInitial: () => {
      writeAttemptViewState(
        state.session.attempt_id,
        { level: runtime.selectedLevel, tab: runtime.selectedTab },
      );
      renderTab(runtime);
    },
    dispose: () => disposePrompt(runtime),
  };
}

type PromptRuntime = {
  elements: ShellElements;
  state: AttemptState;
  onRestore: (snapshotId: string, opener: HTMLElement) => void;
  selectedLevel: number;
  selectedTab: PromptTab;
  generation: number;
  disposed: boolean;
  requestAbort: AbortController | null;
  promptCache: Map<number, string>;
};

const LOCAL_PRACTICE_INFO = [
  "This is a local practice session for rehearsing the assessment workflow.",
  "Use the visible prompt and candidate source to guide your work.",
];

function createPromptRuntime(
  elements: ShellElements,
  state: AttemptState,
  onRestore: (snapshotId: string, opener: HTMLElement) => void,
): PromptRuntime {
  return {
    elements,
    state,
    onRestore,
    selectedLevel: state.selectedLevel,
    selectedTab: state.selectedTab,
    generation: 0,
    disposed: false,
    requestAbort: null,
    promptCache: new Map(),
  };
}

function selectLevel(runtime: PromptRuntime, level: number): void {
  if (!Number.isInteger(level) || level < 1 || level > 4) return;
  runtime.selectedLevel = level;
  runtime.state.selectedLevel = level;
  writeAttemptViewState(
    runtime.state.session.attempt_id,
    { level, tab: runtime.selectedTab },
  );
  if (runtime.selectedTab === "description") {
    renderDescription(runtime);
  } else {
    abortPromptRequest(runtime);
    runtime.generation += 1;
    if (runtime.selectedTab === "rules" || runtime.selectedTab === "info") {
      renderStaticTab(runtime);
    }
  }
}

function selectTab(runtime: PromptRuntime, tab: PromptTab): void {
  if (!isPromptTab(tab)) return;
  runtime.selectedTab = tab;
  runtime.state.selectedTab = tab;
  writeAttemptViewState(
    runtime.state.session.attempt_id,
    { level: runtime.selectedLevel, tab },
  );
  renderTab(runtime);
}

function renderTab(runtime: PromptRuntime): void {
  abortPromptRequest(runtime);
  const requestGeneration = ++runtime.generation;
  if (runtime.selectedTab === "description") {
    requestDescription(runtime, requestGeneration);
  } else if (runtime.selectedTab === "history") {
    requestHistory(runtime, requestGeneration);
  } else {
    renderStaticTab(runtime);
  }
}

function renderDescription(runtime: PromptRuntime): void {
  abortPromptRequest(runtime);
  requestDescription(runtime, ++runtime.generation);
}

function requestDescription(
  runtime: PromptRuntime,
  requestGeneration: number,
): void {
  const level = runtime.selectedLevel;
  const request = { generation: requestGeneration, level, tab: "description" as const };
  runtime.elements.setPromptLoading(level);
  const cached = runtime.promptCache.get(level);
  if (cached !== undefined) {
    if (isCurrent(runtime, request)) runtime.elements.setPrompt(cached);
    return;
  }
  runtime.requestAbort = new AbortController();
  void apiGet(promptPath(runtime.state, level), runtime.requestAbort.signal)
    .then((response) => applyDescription(runtime, request, normalizePrompt(response.data)))
    .catch(() => {
      if (isCurrent(runtime, request)) runtime.elements.setPromptError();
    });
}

function requestHistory(
  runtime: PromptRuntime,
  requestGeneration: number,
): void {
  runtime.elements.setHistoryLoading();
  runtime.requestAbort = new AbortController();
  const request = {
    generation: requestGeneration,
    level: runtime.selectedLevel,
    tab: "history" as const,
  };
  void loadSourceHistory(runtime.state.session.attempt_id, runtime.requestAbort.signal)
    .then((history) => {
      if (isCurrent(runtime, request)) {
        runtime.elements.setHistory(history, runtime.onRestore);
      }
    })
    .catch(() => {
      if (isCurrent(runtime, request)) runtime.elements.setHistoryError();
    });
}

function applyDescription(
  runtime: PromptRuntime,
  request: PromptRequest,
  prompt: ReturnType<typeof normalizePrompt>,
): void {
  if (
    prompt.attempt_id !== runtime.state.session.attempt_id ||
    prompt.level !== request.level ||
    !isCurrent(runtime, request)
  ) {
    return;
  }
  runtime.promptCache.set(request.level, prompt.prompt);
  runtime.elements.setPrompt(prompt.prompt);
}

function isCurrent(runtime: PromptRuntime, request: PromptRequest): boolean {
  return !runtime.disposed &&
    request.generation === runtime.generation &&
    request.level === runtime.selectedLevel &&
    request.tab === runtime.selectedTab;
}

function abortPromptRequest(runtime: PromptRuntime): void {
  runtime.requestAbort?.abort();
  runtime.requestAbort = null;
}

function renderStaticTab(runtime: PromptRuntime): void {
  if (runtime.selectedTab === "rules") {
    runtime.elements.setPrompt(runtime.state.bootstrap.rules.join("\n\n"));
    return;
  }
  runtime.elements.setPrompt(renderInfo(runtime));
}

function renderInfo(runtime: PromptRuntime): string {
  const { assessment } = runtime.state.bootstrap;
  const mode = runtime.state.session.profile?.mode || "unavailable";
  return [
    ...LOCAL_PRACTICE_INFO,
    `Assessment: ${assessment.display_name}`,
    `Mode: ${mode}`,
    `Selected level: ${runtime.selectedLevel} of ${assessment.level_count}`,
    `Level count: ${assessment.level_count}`,
  ].join("\n\n");
}

function disposePrompt(runtime: PromptRuntime): void {
  runtime.disposed = true;
  runtime.generation += 1;
  abortPromptRequest(runtime);
  runtime.promptCache.clear();
}

function promptPath(state: AttemptState, level: number): string {
  return `/api/prompts/${level}?attempt_id=${encodeURIComponent(state.session.attempt_id)}`;
}

function isPromptTab(value: unknown): value is PromptTab {
  return value === "description" ||
    value === "history" ||
    value === "rules" ||
    value === "info";
}
