import type { ActionState } from "./attempt_state";

export type EvaluationLease = {
  action: Exclude<ActionState, "idle">;
  generation: number;
  signal: AbortSignal;
};

export type EvaluationLock = {
  readonly state: ActionState;
  acquire(action: Exclude<ActionState, "idle">): EvaluationLease | null;
  release(lease: EvaluationLease): void;
  cancel(): void;
  isCurrent(lease: EvaluationLease): boolean;
};

export function createEvaluationLock(
  onState: (state: ActionState) => void,
): EvaluationLock {
  let state: ActionState = "idle";
  let generation = 0;
  let controller: AbortController | null = null;
  let lease: EvaluationLease | null = null;
  return {
    get state(): ActionState {
      return state;
    },
    acquire(action) {
      if (lease) return null;
      controller = new AbortController();
      lease = { action, generation: ++generation, signal: controller.signal };
      state = action;
      onState(state);
      return lease;
    },
    release(candidate) {
      if (!lease || lease !== candidate) return;
      lease = null;
      controller = null;
      state = "idle";
      onState(state);
    },
    cancel() {
      generation += 1;
      controller?.abort();
      controller = null;
      lease = null;
      state = "idle";
      onState(state);
    },
    isCurrent(candidate) {
      return lease === candidate && candidate.generation === generation;
    },
  };
}

