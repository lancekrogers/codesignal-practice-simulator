import type { Session, TimeSnapshot } from "./attempt_state";

export type CountdownUpdate = {
  session: Session;
  time: TimeSnapshot;
  remainingSeconds: number;
};

export type CountdownController = {
  applySnapshot(snapshot: TimeSnapshot): void;
  stop(): void;
};

type CountdownRuntime = {
  current: TimeSnapshot;
  anchor: number;
  displayedRemaining: number;
  stopped: boolean;
  resyncInFlight: boolean;
  zeroRefreshRequested: boolean;
  tickTimer?: ReturnType<typeof setTimeout>;
  resyncTimer?: ReturnType<typeof setTimeout>;
};

export function createCountdown(
  initial: TimeSnapshot,
  onUpdate: (update: CountdownUpdate) => void,
  onResync: () => Promise<TimeSnapshot>,
  onResyncError: () => void,
): CountdownController {
  const receivedAt = monotonicNow();
  const runtime: CountdownRuntime = {
    current: initial,
    anchor: receivedAt,
    displayedRemaining: displayCountdown(initial, receivedAt, receivedAt),
    stopped: false,
    resyncInFlight: false,
    zeroRefreshRequested: false,
  };
  const emit = (): void => emitCountdown(runtime, onUpdate);
  const resync = (): Promise<void> => resyncCountdown(
    runtime,
    onResync,
    onResyncError,
    emit,
    resync,
  );
  const tick = (): void => {
    if (runtime.stopped) return;
    emit();
    if (runtime.displayedRemaining === 0 && !runtime.zeroRefreshRequested) {
      runtime.zeroRefreshRequested = true;
      void resync();
    }
    if (!runtime.stopped) runtime.tickTimer = setTimeout(tick, 1000);
  };
  emit();
  runtime.tickTimer = setTimeout(tick, 1000);
  runtime.resyncTimer = setTimeout(resync, 15000);
  return {
    applySnapshot: (snapshot) =>
      applyAuthoritativeSnapshot(runtime, snapshot, emit),
    stop: () => stopCountdown(runtime),
  };
}

function emitCountdown(
  runtime: CountdownRuntime,
  onUpdate: (update: CountdownUpdate) => void,
): void {
  const candidate = runtime.current.session.status === "active"
    ? displayCountdown(runtime.current, runtime.anchor, monotonicNow())
    : 0;
  runtime.displayedRemaining = Math.min(runtime.displayedRemaining, candidate);
  onUpdate({
    session: runtime.current.session,
    time: runtime.current,
    remainingSeconds: runtime.displayedRemaining,
  });
  if (runtime.current.session.status !== "active") stopCountdown(runtime);
}

async function resyncCountdown(
  runtime: CountdownRuntime,
  onResync: () => Promise<TimeSnapshot>,
  onResyncError: () => void,
  emit: () => void,
  schedule: () => Promise<void>,
): Promise<void> {
  if (runtime.stopped || runtime.resyncInFlight) return;
  runtime.resyncInFlight = true;
  try {
    const next = await onResync();
    if (!runtime.stopped) {
      applyAuthoritativeSnapshot(runtime, next, emit);
    }
  } catch {
    if (!runtime.stopped) onResyncError();
  } finally {
    runtime.resyncInFlight = false;
    if (!runtime.stopped) runtime.resyncTimer = setTimeout(schedule, 15000);
  }
}

function applyAuthoritativeSnapshot(
  runtime: CountdownRuntime,
  snapshot: TimeSnapshot,
  emit: () => void,
): void {
  if (runtime.stopped) return;
  const receivedAt = monotonicNow();
  const recoverFromZero =
    runtime.displayedRemaining === 0 && snapshot.session.status === "active";
  const elapsedAtReceipt = recoverFromZero
    ? 0
    : Math.max(0, snapshot.remaining_seconds - runtime.displayedRemaining);
  runtime.current = snapshot;
  runtime.anchor = receivedAt - elapsedAtReceipt * 1000;
  if (recoverFromZero) {
    runtime.displayedRemaining = displayCountdown(snapshot, receivedAt, receivedAt);
  }
  runtime.zeroRefreshRequested = false;
  emit();
}

function stopCountdown(runtime: CountdownRuntime): void {
  runtime.stopped = true;
  if (runtime.tickTimer !== undefined) clearTimeout(runtime.tickTimer);
  if (runtime.resyncTimer !== undefined) clearTimeout(runtime.resyncTimer);
}

export function displayCountdown(
  snapshot: TimeSnapshot,
  anchor: number,
  now: number,
): number {
  const elapsed = Math.max(0, Math.floor((now - anchor) / 1000));
  const observedRemaining = Math.max(0, snapshot.remaining_seconds - elapsed);
  const deadline = Date.parse(snapshot.session.deadline_at);
  const observed = Date.parse(snapshot.observed_at);
  if (!Number.isFinite(deadline) || !Number.isFinite(observed)) {
    return observedRemaining;
  }
  const deadlineRemaining = Math.max(
    0,
    Math.ceil((deadline - observed) / 1000) - elapsed,
  );
  return Math.min(observedRemaining, deadlineRemaining);
}

function monotonicNow(): number {
  return typeof performance !== "undefined" ? performance.now() : Date.now();
}

