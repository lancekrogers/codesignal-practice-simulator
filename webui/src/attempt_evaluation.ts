import {
  ApiError,
  describeApiError,
  submitAttempt,
  testAttempt,
} from "./api";
import {
  loadSource,
  SourceConflictError,
  type SourceDocument,
} from "./source_api";
import {
  normalizeEvaluation,
  type AttemptState,
  type EvaluationLock,
  type PracticeResult,
  type TimeSnapshot,
} from "./state";
import type { EditorHandle } from "./editor";
import type { ShellElements } from "./attempt_types";
import type { SourceController } from "./source_controller";
import type { OperationLease } from "./attempt_operation_lock";

export type EvaluationContext = {
  state: AttemptState;
  elements: ShellElements;
  source: SourceController;
  editor: EditorHandle;
  evaluation: EvaluationLock;
  operation: {
    acquire(kind: "evaluation"): OperationLease | null;
    release(lease: OperationLease): void;
    isCurrent(lease: OperationLease): boolean;
  };
  disposed(): boolean;
  terminal(
    time: AttemptState["time"],
    source: SourceDocument,
    practice: PracticeResult | null,
  ): void;
  applyTime(time: TimeSnapshot): void;
  refresh(): Promise<void>;
};

export function runEvaluation(
  context: EvaluationContext,
  action: "testing" | "submitting",
): void {
  const operationLease = context.operation.acquire("evaluation");
  if (!operationLease) return;
  const lease = context.evaluation.acquire(action);
  if (!lease) {
    context.operation.release(operationLease);
    return;
  }
  context.editor.setReadOnly(true);
  void performEvaluation(context, action, lease, operationLease);
}

async function performEvaluation(
  context: EvaluationContext,
  action: "testing" | "submitting",
  lease: ReturnType<EvaluationLock["acquire"]>,
  operationLease: OperationLease,
): Promise<void> {
  if (!lease) return;
  const flushed = await context.source.flush();
  if (!readyForEvaluation(context, lease, operationLease, flushed.status)) {
    finish(context, lease, operationLease);
    return;
  }
  const sourceLease = context.source.beginAction();
  if (!sourceLease) {
    finish(context, lease, operationLease);
    return;
  }
  try {
    const response = await requestEvaluation(context, action, sourceLease.signal);
    const payload = normalizeEvaluation(response.data);
    if (payload.session.attempt_id !== context.state.session.attempt_id) {
      throw new Error("evaluation response is invalid");
    }
    if (!current(context, lease, operationLease)) return;
    const terminal = applyEvaluation(context, payload);
    if (terminal) return;
    if (action === "submitting") {
      context.elements.setMutationControlsDisabled(true);
      if (!context.disposed()) {
        context.terminal(
          evaluationTime(payload),
          evaluationSource(payload),
          payload.practice,
        );
      }
      return;
    }
    context.elements.announce("Local practice results are ready.");
  } catch (error) {
    await handleEvaluationError(
      context,
      action,
      error,
      sourceLease.signal,
      lease,
      operationLease,
    );
  } finally {
    if (current(context, lease, operationLease)) {
      context.editor.setReadOnly(false);
      context.evaluation.release(lease);
    }
    context.operation.release(operationLease);
  }
}

function readyForEvaluation(
  context: EvaluationContext,
  lease: NonNullable<ReturnType<EvaluationLock["acquire"]>>,
  operationLease: OperationLease,
  status: string,
): boolean {
  return status === "clean" && current(context, lease, operationLease);
}

function requestEvaluation(
  context: EvaluationContext,
  action: "testing" | "submitting",
  signal: AbortSignal,
): Promise<Awaited<ReturnType<typeof testAttempt>>> {
  const { attempt_id: attemptId } = context.state.session;
  const { authoritativeContent: content, authoritativeEtag: etag } =
    context.source.state;
  return action === "testing"
    ? testAttempt(attemptId, content, etag, signal)
    : submitAttempt(attemptId, content, etag, signal);
}

function applyEvaluation(
  context: EvaluationContext,
  payload: ReturnType<typeof normalizeEvaluation>,
): boolean {
  context.source.completeAction({
    content: payload.source,
    etag: payload.sourceEtag,
  });
  context.state.session = payload.session;
  context.state.source = payload.source;
  context.state.sourceEtag = payload.sourceEtag;
  context.state.practice = payload.practice;
  context.elements.setResults(
    payload.session.score,
    payload.session.status,
    payload.practice,
  );
  context.elements.refreshLevelStatus();
  const terminal = payload.session.status !== "active";
  if (terminal) context.elements.setMutationControlsDisabled(true);
  context.applyTime(payload.time);
  if (terminal && !context.disposed()) {
    context.terminal(
      evaluationTime(payload),
      evaluationSource(payload),
      payload.practice,
    );
  }
  return terminal;
}

function evaluationSource(
  payload: ReturnType<typeof normalizeEvaluation>,
): SourceDocument {
  return {
    content: payload.source,
    etag: payload.sourceEtag,
  };
}

function evaluationTime(
  payload: ReturnType<typeof normalizeEvaluation>,
): AttemptState["time"] {
  return { ...payload.time, session: payload.session };
}

async function handleEvaluationError(
  context: EvaluationContext,
  action: "testing" | "submitting",
  error: unknown,
  signal: AbortSignal,
  lease: NonNullable<ReturnType<EvaluationLock["acquire"]>>,
  operationLease: OperationLease,
): Promise<void> {
  if (!current(context, lease, operationLease)) return;
  context.source.cancelAction();
  if (error instanceof ApiError && error.status === 409) {
    await recoverConflict(context, signal);
    return;
  }
  if (!signal.aborted) {
    context.elements.announce(describeApiError(error, action).message);
    if (shouldRefreshAfterFailure(action, error)) await context.refresh();
  }
}

function shouldRefreshAfterFailure(
  action: "testing" | "submitting",
  error: unknown,
): boolean {
  if (action === "submitting") return error instanceof ApiError;
  return error instanceof ApiError &&
    ["lifecycle_locked", "session_unavailable"].includes(error.code);
}

async function recoverConflict(
  context: EvaluationContext,
  signal: AbortSignal,
): Promise<void> {
  try {
    const server = await loadSource(context.state.session.attempt_id, signal);
    if (!context.disposed()) {
      context.source.reportConflict(server);
      context.elements.announce(
        "The candidate source changed before evaluation. Choose a source version.",
      );
    }
  } catch {
    if (!context.disposed()) await context.refresh();
  }
}

function current(
  context: EvaluationContext,
  lease: NonNullable<ReturnType<EvaluationLock["acquire"]>>,
  operationLease: OperationLease,
): boolean {
  return !context.disposed() &&
    context.evaluation.isCurrent(lease) &&
    context.operation.isCurrent(operationLease);
}

function finish(
  context: EvaluationContext,
  lease: NonNullable<ReturnType<EvaluationLock["acquire"]>>,
  operationLease: OperationLease,
): void {
  if (current(context, lease, operationLease)) context.editor.setReadOnly(false);
  context.evaluation.release(lease);
  context.operation.release(operationLease);
}
