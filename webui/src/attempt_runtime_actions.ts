import {
  resetSource,
  restoreSource,
  SourceConflictError,
  type SourceDocument,
} from "./source_api";
import type { AttemptState, PracticeResult } from "./state";
import type { ShellCallbacks } from "./attempt_types";
import type { AttemptRuntime } from "./attempt_runtime_types";
import { runEvaluation } from "./attempt_evaluation";
import type { EvaluationContext } from "./attempt_evaluation";
import type { OperationLease } from "./attempt_operation_lock";
import { applyRuntimeTime } from "./attempt_runtime_lifecycle";

export function shellCallbacks(runtime: AttemptRuntime): ShellCallbacks {
  return {
    onLevelSelect: (level) => selectLevel(runtime, level),
    onLevelNavigate: (direction) => navigateLevel(runtime, direction),
    onPromptTab: (tab) => runtime.prompt?.selectTab(tab),
    onSave: () => retrySave(runtime),
    onRunTests: (opener) => runTests(runtime, opener),
    onSubmit: (opener) => confirmSubmit(runtime, opener),
    onRestore: (snapshotId, opener) =>
      restoreSnapshot(runtime, snapshotId, opener),
    onReset: (opener) => resetSnapshot(runtime, opener),
  };
}

function selectLevel(runtime: AttemptRuntime, level: number): void {
  runtime.prompt?.selectLevel(level);
  runtime.elements.setNavigationLevel(level);
}

function navigateLevel(
  runtime: AttemptRuntime,
  direction: "previous" | "next" | "skip",
): void {
  const delta = direction === "previous" ? -1 : 1;
  const level = runtime.state.selectedLevel + delta;
  if (level < 1 || level > 4) return;
  selectLevel(runtime, level);
  runtime.elements.focusLevel(level);
}

function runTests(runtime: AttemptRuntime, _opener: HTMLElement): void {
  if (!canEvaluate(runtime)) return;
  runEvaluation(evaluationContext(runtime), "testing");
}

function confirmSubmit(runtime: AttemptRuntime, opener: HTMLElement): void {
  if (!canEvaluate(runtime)) return;
  runtime.elements.confirmAction(
    "Submit local practice attempt",
    "Submitting ends this timed practice session. Editing, saving, and local checks will be disabled. The stored result cannot be changed.",
    "Submit attempt",
    opener,
    () => {
      if (canEvaluate(runtime)) {
        runEvaluation(evaluationContext(runtime), "submitting");
      }
    },
  );
}

function canEvaluate(runtime: AttemptRuntime): boolean {
  return Boolean(
    runtime.source &&
      runtime.editor &&
      runtime.state.session.status === "active" &&
      !runtime.operation.busy &&
      !runtime.disposed,
  );
}

function retrySave(runtime: AttemptRuntime): void {
  if (!canMutate(runtime)) return;
  const operation = runtime.operation.acquire("source");
  if (!operation) return;
  runtime.editor!.setReadOnly(true);
  void performRetrySave(runtime, operation);
}

async function performRetrySave(
  runtime: AttemptRuntime,
  operation: OperationLease,
): Promise<void> {
  try {
    await runtime.source!.retry();
  } finally {
    if (!runtime.disposed && runtime.operation.isCurrent(operation)) {
      runtime.editor?.setReadOnly(false);
    }
    runtime.operation.release(operation);
  }
}

function evaluationContext(runtime: AttemptRuntime): EvaluationContext {
  return {
    state: runtime.state,
    elements: runtime.elements,
    source: runtime.source!,
    editor: runtime.editor!,
    evaluation: runtime.evaluation,
    operation: runtime.operation,
    disposed: () => runtime.disposed,
    terminal: (time, source, practice) =>
      runtimeTerminal(runtime, time, source, practice),
    applyTime: (time) => applyRuntimeTime(runtime, time),
    refresh: () => runtimeRefresh(runtime),
  };
}

function runtimeTerminal(
  runtime: AttemptRuntime,
  time: AttemptState["time"],
  source: SourceDocument | undefined,
  practice?: PracticeResult | null,
): void {
  runtime.terminal?.(time, source, practice);
}

function runtimeRefresh(runtime: AttemptRuntime): Promise<void> {
  return runtime.refresh?.() || Promise.resolve();
}

function restoreSnapshot(
  runtime: AttemptRuntime,
  snapshotId: string,
  opener: HTMLElement,
): void {
  if (!canMutate(runtime)) return;
  runtime.elements.confirmAction(
    "Restore candidate version",
    "This replaces the current server source with the selected candidate version. Your current source must be saved first.",
    "Restore version",
    opener,
    () => enqueueSourceAction(runtime, (signal) =>
      restoreSource(
        runtime.state.session.attempt_id,
        snapshotId,
        runtime.source?.state.authoritativeEtag || "",
        signal,
      )),
  );
}

function resetSnapshot(runtime: AttemptRuntime, opener: HTMLElement): void {
  if (!canMutate(runtime)) return;
  runtime.elements.confirmAction(
    "Reset candidate source",
    "This permanently replaces the current source with the attempt baseline. Your current source must be saved first.",
    "Reset source",
    opener,
    () => enqueueSourceAction(runtime, (signal) =>
      resetSource(
        runtime.state.session.attempt_id,
        runtime.source?.state.authoritativeEtag || "",
        signal,
      )),
  );
}

function canMutate(runtime: AttemptRuntime): boolean {
  return Boolean(
    runtime.source &&
      runtime.editor &&
      runtime.state.session.status === "active" &&
      !runtime.operation.busy &&
      !runtime.disposed,
  );
}

function enqueueSourceAction(
  runtime: AttemptRuntime,
  action: (signal: AbortSignal) => Promise<SourceDocument>,
): void {
  if (runtime.disposed) return;
  const operation = runtime.operation.acquire("source");
  if (!operation) return;
  void performSourceAction(runtime, action, operation);
}

async function performSourceAction(
  runtime: AttemptRuntime,
  action: (signal: AbortSignal) => Promise<SourceDocument>,
  operation: OperationLease,
): Promise<void> {
  const source = runtime.source;
  const editor = runtime.editor;
  if (!source || !editor || runtime.disposed) {
    runtime.operation.release(operation);
    return;
  }
  editor.setReadOnly(true);
  try {
    const flushed = await source.flush();
    if (
      !runtime.operation.isCurrent(operation) ||
      runtime.disposed ||
      flushed.status !== "clean"
    ) return;
    const lease = source.beginAction();
    if (!lease) return;
    try {
      const document = await action(lease.signal);
      if (runtime.operation.isCurrent(operation) && !runtime.disposed) {
        source.completeAction(document);
        runtime.elements.announce("Candidate source updated.");
      }
    } catch (error) {
      source.cancelAction();
      if (runtime.disposed) return;
      if (error instanceof SourceConflictError) {
        source.reportConflict(error.server);
      } else {
        runtime.elements.announce(
          "The candidate source action could not be applied safely.",
        );
      }
    }
  } finally {
    if (!runtime.disposed) editor.setReadOnly(false);
    runtime.operation.release(operation);
  }
}
