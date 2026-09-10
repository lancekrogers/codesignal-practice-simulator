import { SourceConflictError, type SourceDocument } from "./source_api";
import type {
  FlushResult,
  SourceActionLease,
  SourceController,
  SourceControllerOptions,
} from "./source_controller";
import { createSourceState, type SourceState } from "./source_state";

export class SourceControllerRuntime {
  readonly state: SourceState;
  private pending: string | null = null;
  private timer: ReturnType<typeof setTimeout> | undefined;
  private inFlight: Promise<FlushResult> | null = null;
  private abort: AbortController | null = null;
  private actionAbort: AbortController | null = null;
  private actionEdited = false;
  private locked = false;
  private disposed = false;
  private generation = 0;
  private applying = false;

  constructor(private readonly options: SourceControllerOptions) {
    this.state = createSourceState(options.content, options.etag);
  }

  controller(): SourceController {
    return {
      state: this.state,
      change: (content) => this.change(content),
      flush: () => this.flush(),
      retry: () => this.retry(),
      keepLocal: () => this.keepLocal(),
      reloadServer: () => this.reloadServer(),
      reportConflict: (server) => this.reportConflict(server),
      applyAuthoritative: (document) => this.applyAuthoritative(document),
      beginAction: () => this.beginAction(),
      completeAction: (document) => this.completeAction(document),
      cancelAction: () => this.cancelAction(),
      lock: () => this.lock(),
      dispose: () => this.dispose(),
    };
  }

  private notify(): void {
    if (!this.locked && !this.disposed) this.options.onState({ ...this.state });
  }

  private schedule(delay = this.options.debounceMs ?? 450): void {
    if (this.locked || this.timer !== undefined) return;
    this.timer = setTimeout(() => {
      this.timer = undefined;
      void this.drain();
    }, delay);
  }

  private clearTimer(): void {
    if (this.timer !== undefined) clearTimeout(this.timer);
    this.timer = undefined;
  }

  private async drain(): Promise<FlushResult> {
    if (this.locked || this.disposed) return this.notSaved();
    if (this.inFlight) return this.inFlight;
    if (this.pending === null) return this.markCleanIfCurrent();
    const content = this.pending;
    this.pending = null;
    const requestGeneration = this.generation;
    this.state.status = "saving";
    this.notify();
    this.abort = new AbortController();
    this.inFlight = this.options.save(
      content,
      this.state.authoritativeEtag,
      this.abort.signal,
    ).then(
      (document) => this.finishSave(document, content, requestGeneration),
      (error: unknown) => this.finishFailure(error, requestGeneration),
    ).finally(() => {
      this.inFlight = null;
      this.abort = null;
    });
    return this.inFlight;
  }

  private markCleanIfCurrent(): FlushResult {
    if (this.state.buffer === this.state.authoritativeContent) {
      this.state.status = "clean";
      this.notify();
    }
    return this.notSaved();
  }

  private finishSave(
    document: SourceDocument,
    content: string,
    requestGeneration: number,
  ): FlushResult {
    if (!this.isCurrent(requestGeneration)) return this.notSaved();
    this.state.authoritativeContent = document.content;
    this.state.authoritativeEtag = document.etag;
    if (this.state.buffer === content) this.state.buffer = document.content;
    this.state.status = this.state.buffer === this.state.authoritativeContent
      ? "clean"
      : "dirty";
    this.notify();
    if (this.pending !== null) this.schedule(0);
    return { status: this.state.status, saved: true };
  }

  private finishFailure(error: unknown, requestGeneration: number): FlushResult {
    if (!this.isCurrent(requestGeneration)) return this.notSaved();
    this.pending = this.state.buffer;
    if (error instanceof SourceConflictError) {
      this.state.serverContent = error.server.content;
      this.state.serverEtag = error.server.etag;
      this.state.status = "conflict";
      this.notify();
      this.options.onConflict(error.server);
    } else {
      this.state.status = "failed";
      this.notify();
    }
    return this.notSaved();
  }

  private notSaved(): FlushResult {
    return { status: this.state.status, saved: false };
  }

  private isCurrent(requestGeneration: number): boolean {
    return !this.locked &&
      !this.disposed &&
      requestGeneration === this.generation;
  }

  private change(content: string): void {
    if (this.locked) return;
    this.state.buffer = content;
    if (this.state.status === "conflict") {
      this.pending = null;
      this.notify();
      return;
    }
    if (this.actionAbort) {
      this.actionEdited = true;
      this.state.status = "saving";
      this.notify();
      return;
    }
    if (this.applying) {
      this.pending = null;
      this.state.status = "clean";
      this.notify();
      return;
    }
    this.pending = content;
    this.state.status = content === this.state.authoritativeContent ? "clean" : "dirty";
    this.notify();
    this.clearTimer();
    this.schedule();
  }

  private async flush(): Promise<FlushResult> {
    this.clearTimer();
    while (this.inFlight || this.pending !== null) {
      if (this.inFlight) await this.inFlight;
      else await this.drain();
      if (this.state.status === "conflict" || this.state.status === "failed") break;
    }
    return {
      status: this.state.status,
      saved: this.state.status === "clean",
    };
  }

  private async retry(): Promise<FlushResult> {
    if (this.locked) return this.notSaved();
    if (this.state.status === "failed") {
      this.state.status = "dirty";
      this.pending = this.state.buffer;
      this.notify();
    }
    return this.flush();
  }

  private async keepLocal(): Promise<FlushResult> {
    if (this.locked || this.state.status !== "conflict" || !this.state.serverEtag) {
      return this.notSaved();
    }
    this.clearTimer();
    this.state.authoritativeContent = this.state.serverContent || "";
    this.state.authoritativeEtag = this.state.serverEtag;
    this.state.status = "dirty";
    this.pending = this.state.buffer;
    this.notify();
    return this.flush();
  }

  private reloadServer(): void {
    if (this.locked || this.state.status !== "conflict" ||
        this.state.serverEtag === undefined) return;
    this.clearTimer();
    this.pending = null;
    this.state.authoritativeContent = this.state.serverContent || "";
    this.state.authoritativeEtag = this.state.serverEtag;
    this.state.buffer = this.state.authoritativeContent;
    this.state.status = "clean";
    this.notify();
    this.applyEditorValue(this.state.buffer);
  }

  private reportConflict(server: SourceDocument): void {
    if (this.locked || this.disposed) return;
    this.state.serverContent = server.content;
    this.state.serverEtag = server.etag;
    this.pending = null;
    this.state.status = "conflict";
    this.notify();
    this.options.onConflict(server);
  }

  private applyAuthoritative(document: SourceDocument): void {
    if (this.locked || this.disposed) return;
    this.clearTimer();
    this.pending = null;
    this.state.authoritativeContent = document.content;
    this.state.authoritativeEtag = document.etag;
    this.state.buffer = document.content;
    this.state.serverContent = undefined;
    this.state.serverEtag = undefined;
    this.state.status = "clean";
    this.notify();
    this.applyEditorValue(document.content);
  }

  private beginAction(): SourceActionLease | null {
    if (this.locked || this.disposed || this.actionAbort ||
        this.state.status !== "clean") return null;
    this.clearTimer();
    this.pending = null;
    this.actionEdited = false;
    this.actionAbort = new AbortController();
    this.state.status = "saving";
    this.notify();
    return { signal: this.actionAbort.signal };
  }

  private completeAction(document: SourceDocument): void {
    if (!this.actionAbort || this.locked || this.disposed) return;
    this.actionAbort = null;
    this.state.authoritativeContent = document.content;
    this.state.authoritativeEtag = document.etag;
    this.state.serverContent = undefined;
    this.state.serverEtag = undefined;
    if (this.actionEdited) return this.finishEditedAction(document);
    this.state.buffer = document.content;
    this.state.status = "clean";
    this.notify();
    this.applyEditorValue(document.content);
  }

  private finishEditedAction(document: SourceDocument): void {
    this.state.status = this.state.buffer === document.content ? "clean" : "dirty";
    this.pending = this.state.status === "dirty" ? this.state.buffer : null;
    this.notify();
    if (this.pending !== null) this.schedule(0);
  }

  private cancelAction(): void {
    if (!this.actionAbort) return;
    this.actionAbort = null;
    if (this.locked || this.disposed) return;
    this.state.status = this.state.buffer === this.state.authoritativeContent
      ? "clean"
      : "dirty";
    this.pending = this.state.status === "dirty" ? this.state.buffer : null;
    this.notify();
    if (this.pending !== null) this.schedule(0);
  }

  private applyEditorValue(content: string): void {
    this.applying = true;
    try {
      this.options.onReloadServer(content);
    } finally {
      this.applying = false;
    }
  }

  private lock(): void {
    if (this.locked) return;
    this.locked = true;
    this.generation += 1;
    this.clearTimer();
    this.pending = null;
    this.abort?.abort();
    this.actionAbort?.abort();
  }

  private dispose(): void {
    if (this.disposed) return;
    this.disposed = true;
    this.lock();
  }
}
