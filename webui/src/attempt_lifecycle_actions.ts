import {
  abandonAttempt as postAbandon,
  apiGet,
  describeApiError,
  restartAttempt as postRestart,
} from "./api";
import type { AttemptRuntime } from "./attempt_runtime_types";
import type { OperationLease } from "./attempt_operation_lock";
import { refreshRuntime } from "./attempt_runtime_lifecycle";
import { normalizeTime } from "./state";
import { openAttempt } from "./router";

/**
 * End attempt and Restart (D001/D004). Both run under the attempt's operation
 * lock, so they never overlap a save, an evaluation or each other; both flush
 * the editor first and, when the latest text cannot be saved, ask for an
 * explicit discard before anything irreversible happens. Saved work on the
 * server is never touched by either action.
 */

const END_COPY =
  "Ending records this attempt as ended without a score. Your saved work is kept " +
  "and stays readable; only this attempt's timer stops. Unsaved local edits are " +
  "saved first when possible.";

const RESTART_COPY =
  "Restart ends this attempt and opens a fresh one for the same exercise and " +
  "format. Your saved work here is kept and stays readable in history; nothing is " +
  "copied into the new attempt, and the timer starts over only there. Unsaved " +
  "local edits are saved first; if they cannot be saved you will be asked before " +
  "they are discarded.";

const DISCARD_COPY =
  "Your latest edits are not saved on the server. Continuing discards those " +
  "unsaved edits; the last saved version of this attempt is kept. Cancel to keep " +
  "editing and retry the save first.";

export function endAttempt(runtime: AttemptRuntime, opener: HTMLElement): void {
  if (!ready(runtime)) return;
  runtime.elements.confirmAction(
    "End attempt?",
    END_COPY,
    "End attempt",
    opener,
    () => void performEnd(runtime, opener, false),
  );
}

export function restartAttempt(runtime: AttemptRuntime, opener: HTMLElement): void {
  if (!ready(runtime)) return;
  runtime.elements.confirmAction(
    "Restart with a new attempt?",
    RESTART_COPY,
    "Restart attempt",
    opener,
    () => void performRestart(runtime, opener, false),
  );
}

function ready(runtime: AttemptRuntime): boolean {
  if (runtime.disposed || runtime.state.session.status !== "active") return false;
  if (runtime.operation.busy || runtime.source?.state.status === "saving") {
    runtime.elements.announce("Wait for the current operation to finish first.");
    return false;
  }
  return true;
}

async function performEnd(
  runtime: AttemptRuntime,
  opener: HTMLElement,
  discardUnsaved: boolean,
): Promise<void> {
  const operation = begin(runtime);
  if (!operation) return;
  try {
    if (!discardUnsaved) {
      const saved = await flushForTransition(runtime, operation);
      if (saved === null) return;
      if (!saved) {
        finish(runtime, operation);
        askDiscard(runtime, opener, "End attempt and discard unsaved edits",
          () => void performEnd(runtime, opener, true));
        return;
      }
    }
    const revision = await currentRevision(runtime, operation);
    if (revision === null) return;
    await postAbandon(runtime.state.session.attempt_id, revision, operation.signal);
    if (!runtime.operation.isCurrent(operation) || runtime.disposed) return;
    runtime.elements.announce("Attempt ended. Saved work remains available read-only.");
    finish(runtime, operation);
    await refreshRuntime(runtime);
  } catch (error) {
    if (!runtime.operation.isCurrent(operation) || runtime.disposed) return;
    finish(runtime, operation);
    await reportFailure(runtime, error, "ending");
  }
}

async function performRestart(
  runtime: AttemptRuntime,
  opener: HTMLElement,
  discardUnsaved: boolean,
): Promise<void> {
  const operation = begin(runtime);
  if (!operation) return;
  try {
    if (!discardUnsaved) {
      const saved = await flushForTransition(runtime, operation);
      if (saved === null) return;
      if (!saved) {
        finish(runtime, operation);
        askDiscard(runtime, opener, "Discard unsaved edits and restart",
          () => void performRestart(runtime, opener, true));
        return;
      }
    }
    const revision = await currentRevision(runtime, operation);
    if (revision === null) return;
    runtime.restartOperationId ??= crypto.randomUUID();
    const document = await postRestart(
      runtime.state.session.attempt_id,
      runtime.restartOperationId,
      revision,
      operation.signal,
    );
    if (!runtime.operation.isCurrent(operation) || runtime.disposed) return;
    const replacement = document.data?.replacement_attempt_id;
    if (typeof replacement !== "string" || replacement === runtime.state.session.attempt_id) {
      throw new Error("restart response is invalid");
    }
    // No live-region announcement here: cleanup disposes the region before it
    // could paint. The replacement's reconnect screen (role=status) and its
    // attempt shell announce the transition instead.
    runtime.cleanup();
    openAttempt(replacement);
  } catch (error) {
    if (!runtime.operation.isCurrent(operation) || runtime.disposed) return;
    finish(runtime, operation);
    const failure = await reportFailure(runtime, error, "restarting");
    // A stale revision means the next request carries different arguments, so
    // it must be a new operation; every other failure retries the same one.
    if (failure.kind === "stale" || failure.kind === "read_only") {
      runtime.restartOperationId = undefined;
    }
  }
}

function begin(runtime: AttemptRuntime): OperationLease | null {
  const operation = runtime.operation.acquire("lifecycle");
  if (!operation) {
    runtime.elements.announce("Wait for the current operation to finish first.");
    return null;
  }
  runtime.editor?.setReadOnly(true);
  return operation;
}

function finish(runtime: AttemptRuntime, operation: OperationLease): void {
  if (!runtime.disposed && runtime.operation.isCurrent(operation)) {
    runtime.editor?.setReadOnly(false);
  }
  runtime.operation.release(operation);
}

/**
 * Flush the editor buffer. Resolves true when the server holds the latest text,
 * false when it does not (failed save or unresolved conflict), and null when
 * the runtime moved on meanwhile.
 */
async function flushForTransition(
  runtime: AttemptRuntime,
  operation: OperationLease,
): Promise<boolean | null> {
  const source = runtime.source;
  if (!source) return true;
  const flushed = await source.flush();
  if (!runtime.operation.isCurrent(operation) || runtime.disposed) return null;
  return flushed.status === "clean";
}

function askDiscard(
  runtime: AttemptRuntime,
  opener: HTMLElement,
  confirmLabel: string,
  onConfirm: () => void,
): void {
  if (runtime.disposed) return;
  runtime.elements.confirmAction(
    "Unsaved edits could not be saved",
    DISCARD_COPY,
    confirmLabel,
    opener,
    onConfirm,
  );
}

/** The attempt's current revision from a fresh time snapshot (metadata only). */
async function currentRevision(
  runtime: AttemptRuntime,
  operation: OperationLease,
): Promise<number | null> {
  const attemptId = runtime.state.session.attempt_id;
  const query = `?attempt_id=${encodeURIComponent(attemptId)}`;
  const time = normalizeTime((await apiGet(`/api/time${query}`, operation.signal)).data);
  if (!runtime.operation.isCurrent(operation) || runtime.disposed) return null;
  if (time.session.attempt_id !== attemptId) throw new Error("time response is invalid");
  const revision = time.session.revision;
  if (!Number.isInteger(revision) || (revision as number) < 0) {
    throw new Error("session revision is unavailable");
  }
  if (time.session.status !== "active") {
    // Expired or ended elsewhere: refresh shows the terminal view instead.
    finish(runtime, operation);
    await refreshRuntime(runtime);
    return null;
  }
  return revision as number;
}

async function reportFailure(
  runtime: AttemptRuntime,
  error: unknown,
  action: "ending" | "restarting",
): Promise<ReturnType<typeof describeApiError>> {
  const failure = describeApiError(error, action);
  runtime.elements.announce(failure.message);
  runtime.elements.status.textContent = failure.message;
  if (failure.recovery === "refresh") await refreshRuntime(runtime);
  return failure;
}
