export type OperationKind = "evaluation" | "source";

export type OperationLease = {
  kind: OperationKind;
  generation: number;
  signal: AbortSignal;
};

export type OperationLock = {
  readonly busy: boolean;
  acquire(kind: OperationKind): OperationLease | null;
  release(lease: OperationLease): void;
  cancel(): void;
  isCurrent(lease: OperationLease): boolean;
};

export function createOperationLock(
  onBusyChange: (busy: boolean) => void,
): OperationLock {
  let generation = 0;
  let controller: AbortController | null = null;
  let lease: OperationLease | null = null;
  return {
    get busy(): boolean {
      return lease !== null;
    },
    acquire(kind) {
      if (lease) return null;
      controller = new AbortController();
      lease = { kind, generation: ++generation, signal: controller.signal };
      onBusyChange(true);
      return lease;
    },
    release(candidate) {
      if (lease !== candidate) return;
      lease = null;
      controller = null;
      onBusyChange(false);
    },
    cancel() {
      generation += 1;
      controller?.abort();
      controller = null;
      lease = null;
      onBusyChange(false);
    },
    isCurrent(candidate) {
      return lease === candidate && candidate.generation === generation;
    },
  };
}
