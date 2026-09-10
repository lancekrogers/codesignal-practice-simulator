import { type SourceDocument } from "./source_api";
import type { SourceSaveStatus, SourceState } from "./source_state";
import { SourceControllerRuntime } from "./source_controller_runtime";

export type FlushResult = {
  status: SourceSaveStatus;
  saved: boolean;
};

export type SourceActionLease = {
  signal: AbortSignal;
};

export type SourceController = {
  state: SourceState;
  change(content: string): void;
  flush(): Promise<FlushResult>;
  retry(): Promise<FlushResult>;
  keepLocal(): Promise<FlushResult>;
  reloadServer(): void;
  reportConflict(server: SourceDocument): void;
  applyAuthoritative(document: SourceDocument): void;
  beginAction(): SourceActionLease | null;
  completeAction(document: SourceDocument): void;
  cancelAction(): void;
  lock(): void;
  dispose(): void;
};

export type SourceControllerOptions = {
  content: string;
  etag: string;
  debounceMs?: number;
  save(content: string, etag: string, signal?: AbortSignal): Promise<SourceDocument>;
  onState(state: SourceState): void;
  onConflict(server: SourceDocument): void;
  onReloadServer(content: string): void;
};

export function createSourceController(
  options: SourceControllerOptions,
): SourceController {
  return new SourceControllerRuntime(options).controller();
}
