const worker = globalThis as typeof globalThis & {
  onmessage: ((event: MessageEvent) => void) | null;
};

worker.onmessage = () => {
  // Python syntax and indentation run in the main Monaco model. This explicit
  // same-origin entry keeps the worker policy closed for future language work.
};
