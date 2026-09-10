import type { StaticManifest } from "./api";
import type { EditorHandle } from "./editor";
import type { PromptController } from "./prompt_controller";
import type { SourceController } from "./source_controller";
import type { SourceDocument } from "./source_api";
import type {
  Bootstrap,
  EvaluationLock,
  AttemptPayload,
  PracticeResult,
  AttemptState,
  TimeSnapshot,
} from "./state";
import type { CountdownController } from "./attempt_lifecycle";
import type { ShellElements } from "./attempt_types";
import type { OperationLock } from "./attempt_operation_lock";

export type AttemptRuntime = {
  state: AttemptState;
  elements: ShellElements;
  prompt: PromptController | null;
  source: SourceController | null;
  editor: EditorHandle | undefined;
  cleanup: () => void;
  start(): void;
  evaluation: EvaluationLock;
  operation: OperationLock;
  disposed: boolean;
  terminalTransitioned: boolean;
  countdown?: CountdownController;
  terminal(
    time: TimeSnapshot,
    source?: SourceDocument,
    practice?: PracticeResult | null,
  ): void;
  refresh(): Promise<void>;
};

export type AttemptRuntimeSetup = {
  root: HTMLElement;
  manifest: StaticManifest;
  bootstrap: Bootstrap;
  payload: AttemptPayload;
};

export type RuntimeSource = SourceDocument | undefined;

