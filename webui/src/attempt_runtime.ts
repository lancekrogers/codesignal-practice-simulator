import { apiGet, describeApiError, type StaticManifest } from "./api";
import {
  attemptState,
  createEvaluationLock,
  normalizeTime,
  practiceFromScore,
  type AttemptPayload,
  type Bootstrap,
  type PracticeResult,
} from "./state";
import {
  loadSource,
  type SourceDocument,
} from "./source_api";
import {
  renderAttemptShell,
  renderError,
} from "./views";
import { createPromptController } from "./prompt_controller";
import { shellCallbacks } from "./attempt_runtime_actions";
import {
  cleanupAttempt,
  refreshRuntime,
  startAttemptRuntime,
} from "./attempt_runtime_lifecycle";
import type { AttemptRuntime } from "./attempt_runtime_types";
import { errorState } from "./state";
import { createOperationLock } from "./attempt_operation_lock";

let currentAttemptCleanup: (() => void) | null = null;
let currentRuntime: AttemptRuntime | null = null;
let attemptGeneration = 0;

export function showAttempt(
  root: HTMLElement,
  manifest: StaticManifest,
  bootstrap: Bootstrap,
  payload: AttemptPayload,
): void {
  disposeAttempt();
  const runtime = createAttemptRuntime(root, manifest, bootstrap, payload);
  currentAttemptCleanup = runtime.cleanup;
  currentRuntime = runtime;
  runtime.start();
}

export function disposeAttempt(): void {
  attemptGeneration += 1;
  currentAttemptCleanup?.();
  currentAttemptCleanup = null;
  currentRuntime = null;
}

export type LeaveSettlement =
  | { kind: "none" }
  | { kind: "clear"; attemptId: string }
  | { kind: "unsaved"; attemptId: string };

/**
 * Before a navigation that did not come from the attempt's own Leave dialog
 * (browser back/forward, a typed address), give the live attempt the chance to
 * finish saving. A pending or in-flight save is flushed; text that still cannot
 * be saved is reported as `unsaved` so the caller can keep the attempt open
 * instead of discarding it silently.
 */
export async function settleAttemptBeforeLeaving(): Promise<LeaveSettlement> {
  const runtime = currentRuntime;
  if (!runtime || runtime.disposed || runtime.state.session.status !== "active") {
    return { kind: "none" };
  }
  const attemptId = runtime.state.session.attempt_id;
  const source = runtime.source;
  if (!source) return { kind: "clear", attemptId };
  let status = source.state.status;
  if (status === "dirty" || status === "saving") {
    status = (await source.flush()).status;
  }
  if (runtime.disposed || currentRuntime !== runtime) return { kind: "none" };
  return status === "clean" ? { kind: "clear", attemptId } : { kind: "unsaved", attemptId };
}

export function announceInAttempt(message: string): void {
  const runtime = currentRuntime;
  if (!runtime || runtime.disposed) return;
  runtime.elements.announce(message);
  runtime.elements.status.textContent = message;
}

export async function showTerminalAttempt(
  root: HTMLElement,
  manifest: StaticManifest,
  bootstrap: Bootstrap,
  time: ReturnType<typeof normalizeTime>,
  fallback?: SourceDocument,
  practice?: PracticeResult | null,
): Promise<void> {
  const terminalPractice = practice ??
    (time.session.score ? practiceFromScore(time.session.score) : null);
  if (fallback) {
    showAttempt(root, manifest, bootstrap, {
      session: time.session,
      practice: terminalPractice,
      source: fallback.content,
      sourceEtag: fallback.etag,
      time,
    });
    return;
  }
  const generation = attemptGeneration;
  try {
    const source = await loadSource(time.session.attempt_id);
    if (generation !== attemptGeneration) return;
    showAttempt(root, manifest, bootstrap, {
      session: time.session,
      practice: terminalPractice,
      source: source.content,
      sourceEtag: source.etag,
      time,
    });
  } catch (error) {
    if (generation !== attemptGeneration) return;
    if (!fallback) {
      showTerminalError(root, manifest, bootstrap, time, generation, error);
    }
  }
}

function createAttemptRuntime(
  root: HTMLElement,
  manifest: StaticManifest,
  bootstrap: Bootstrap,
  payload: AttemptPayload,
): AttemptRuntime {
  const runtime = {} as AttemptRuntime;
  runtime.state = attemptState(manifest, bootstrap, payload);
  runtime.prompt = null;
  runtime.source = null;
  runtime.editor = undefined;
  runtime.disposed = false;
  runtime.terminalTransitioned = false;
  runtime.evaluation = createEvaluationLock((action) => {
    runtime.state.action = action;
    if (!runtime.disposed) runtime.elements.setActionState(action);
  });
  runtime.terminal = (time, source, practice) =>
    transitionTerminal(runtime, time, source, practice);
  runtime.refresh = () => refreshRuntime(runtime);
  runtime.elements = renderAttemptShell(root, runtime.state, shellCallbacks(runtime));
  runtime.operation = createOperationLock((busy) => {
    if (!runtime.disposed) runtime.elements.setOperationBusy(busy);
  });
  runtime.cleanup = () => cleanupAttempt(runtime);
  runtime.prompt = createPromptController(
    runtime.elements,
    runtime.state,
    (snapshotId, opener) =>
      shellCallbacks(runtime).onRestore(snapshotId, opener),
  );
  runtime.start = () => startAttemptRuntime(runtime, manifest, payload);
  return runtime;
}

function transitionTerminal(
  runtime: AttemptRuntime,
  time: ReturnType<typeof normalizeTime>,
  source?: SourceDocument,
  practice?: PracticeResult | null,
): void {
  if (runtime.disposed || runtime.terminalTransitioned) return;
  runtime.terminalTransitioned = true;
  runtime.cleanup();
  void showTerminalAttempt(
    runtimeRoot(runtime),
    runtime.state.manifest,
    runtime.state.bootstrap,
    time,
    source,
    practice,
  );
}

function runtimeRoot(runtime: AttemptRuntime): HTMLElement {
  const root = runtime.elements.editor.closest("#app");
  if (!root) throw new Error("assessment mount is missing");
  return root;
}

function showTerminalError(
  root: HTMLElement,
  manifest: StaticManifest,
  bootstrap: Bootstrap,
  time: ReturnType<typeof normalizeTime>,
  generation: number,
  error: unknown,
): void {
  if (generation !== attemptGeneration) return;
  renderError(root, errorState(
    manifest,
    describeApiError(error, "reconnect").message,
  ), {
    label: "Reload terminal attempt",
    onClick: () => void showTerminalAttempt(root, manifest, bootstrap, time),
  });
}

