import { apiGet } from "./api";
import { initializeEditor, type EditorHandle } from "./editor";
import {
  createCountdown,
  type CountdownController,
} from "./attempt_lifecycle";
import {
  normalizeTime,
  workerUrls,
  type AttemptPayload,
  type Bootstrap,
  type TimeSnapshot,
} from "./state";
import {
  saveSource,
  type SourceDocument,
} from "./source_api";
import { createSourceController } from "./source_controller";
import type { SourceState } from "./source_state";
import type { StaticManifest } from "./api";
import { showEditor, showFallback } from "./views";
import type { AttemptRuntime } from "./attempt_runtime_types";

export function startAttemptRuntime(
  runtime: AttemptRuntime,
  manifest: StaticManifest,
  payload: AttemptPayload,
): void {
  runtime.prompt?.loadInitial();
  if (runtime.state.session.status !== "active" || runtime.state.source === null) {
    return;
  }
  runtime.source = createSource(runtime);
  runtime.editor = startEditor(runtime, manifest);
  runtime.countdown = startAttemptCountdown(runtime, payload);
}

function createSource(runtime: AttemptRuntime) {
  return createSourceController({
    content: runtime.state.source || "",
    etag: runtime.state.sourceEtag || "",
    save: (content, etag, signal) =>
      saveSource(runtime.state.session.attempt_id, content, etag, signal),
    onState: (sourceState) => updateSourceState(runtime, sourceState),
    onConflict: (server) => showSourceConflict(runtime, server),
    onReloadServer: (content) => runtime.editor?.setValue(content),
  });
}

function updateSourceState(
  runtime: AttemptRuntime,
  sourceState: SourceState,
): void {
  runtime.state.sourceState = sourceState;
  runtime.state.source = sourceState.buffer;
  runtime.state.sourceEtag = sourceState.authoritativeEtag;
  runtime.elements.setSaveState(sourceState.status);
  if (sourceState.status !== "conflict") runtime.elements.clearConflict();
}

export function showSourceConflict(
  runtime: AttemptRuntime,
  server: SourceDocument,
): void {
  runtime.elements.setConflict(server, {
    keepLocal: () => void runtime.source?.keepLocal(),
    reloadServer: () => runtime.source?.reloadServer(),
  });
}

function startEditor(
  runtime: AttemptRuntime,
  manifest: StaticManifest,
): EditorHandle | undefined {
  const editorRuntime: EditorRuntime = { active: true, failed: false };
  try {
    editorRuntime.editor = initializeEditor(
      runtime.elements,
      runtime.state.source || "",
      workerUrls(manifest),
      (value) => runtime.source?.change(value),
      () => failEditor(runtime, editorRuntime),
    );
    showEditor(runtime.elements);
    return activeEditorHandle(editorRuntime);
  } catch {
    if (!editorRuntime.failed) failEditor(runtime, editorRuntime);
    return undefined;
  }
}

type EditorRuntime = {
  active: boolean;
  failed: boolean;
  editor?: ReturnType<typeof initializeEditor>;
};

function failEditor(runtime: AttemptRuntime, editor: EditorRuntime): void {
  if (!editor.active || editor.failed) return;
  const currentValue = editor.editor?.getValue() ?? runtime.state.source ?? "";
  const wasSaving = runtime.source?.state.status === "saving";
  const authoritative = runtime.source?.state.authoritativeContent ||
    runtime.state.source || "";
  if (!wasSaving) runtime.source?.change(currentValue);
  editor.failed = true;
  editor.active = false;
  editor.editor?.dispose();
  showFallback(
    runtime.elements,
    "The Python editor worker could not initialize.",
    currentValue,
  );
  const settle = (): void => {
    if (runtime.disposed) return;
    const source = runtime.source;
    source?.lock();
    runtime.elements.setSaveState(
      source?.state.status === "clean" &&
        source.state.authoritativeContent === currentValue
        ? "clean"
        : currentValue === authoritative ? "clean" : "dirty",
    );
  };
  if (wasSaving) void runtime.source?.flush().then(settle);
  else settle();
}

function activeEditorHandle(runtime: EditorRuntime): EditorHandle | undefined {
  const editor = runtime.editor;
  if (!editor) return undefined;
  return {
    getValue: () => editor.getValue(),
    setValue: (value) => {
      if (runtime.active) editor.setValue(value);
    },
    setReadOnly: (readOnly) => {
      if (runtime.active) editor.setReadOnly(readOnly);
    },
    dispose: () => {
      runtime.active = false;
      editor.dispose();
    },
  };
}

function startAttemptCountdown(
  runtime: AttemptRuntime,
  payload: AttemptPayload,
): CountdownController {
  return createCountdown(
    payload.time,
    (update) => {
      runtime.state.session = update.session;
      runtime.state.time = update.time;
      runtime.elements.setCountdown(update.remainingSeconds);
      if (update.session.status !== "active") {
        runtime.terminal(
          update.time,
          authoritativeSource(runtime),
          runtime.state.practice,
        );
      }
    },
    () => resyncTime(payload, runtime),
    () => runtime.elements.setConnection("reconnecting"),
  );
}

function authoritativeSource(runtime: AttemptRuntime): SourceDocument | undefined {
  const source = runtime.source?.state;
  return source
    ? { content: source.authoritativeContent, etag: source.authoritativeEtag }
    : undefined;
}

async function resyncTime(
  payload: AttemptPayload,
  runtime: AttemptRuntime,
): Promise<TimeSnapshot> {
  runtime.elements.setConnection("reconnecting");
  const requestedAttemptId = payload.session.attempt_id;
  assertCurrentAttempt(runtime, requestedAttemptId);
  const query = `?attempt_id=${encodeURIComponent(requestedAttemptId)}`;
  const next = normalizeTime((await apiGet(`/api/time${query}`)).data);
  assertTimeAttempt(next, requestedAttemptId, runtime.state.session.attempt_id);
  if (runtime.disposed) return next;
  runtime.elements.setConnection("connected");
  return next;
}

export async function refreshRuntime(runtime: AttemptRuntime): Promise<void> {
  if (runtime.disposed) return;
  const requestedAttemptId = runtime.state.session.attempt_id;
  const query = `?attempt_id=${encodeURIComponent(requestedAttemptId)}`;
  try {
    const time = normalizeTime((await apiGet(`/api/time${query}`)).data);
    if (runtime.disposed) return;
    assertTimeAttempt(time, requestedAttemptId, runtime.state.session.attempt_id);
    runtime.elements.setConnection("connected");
    if (runtime.countdown) {
      runtime.countdown.applySnapshot(time);
    } else {
      runtime.state.session = time.session;
      runtime.state.time = time;
      if (time.session.status !== "active") {
        runtime.terminal(
          time,
          authoritativeSource(runtime),
          runtime.state.practice,
        );
      }
    }
  } catch {
    if (!runtime.disposed) runtime.elements.setConnection("reconnecting");
  }
}

export function applyRuntimeTime(
  runtime: AttemptRuntime,
  time: TimeSnapshot,
): void {
  if (runtime.disposed) return;
  assertTimeAttempt(time, runtime.state.session.attempt_id, runtime.state.session.attempt_id);
  if (runtime.countdown) {
    runtime.countdown.applySnapshot(time);
    return;
  }
  runtime.state.session = time.session;
  runtime.state.time = time;
}

function assertCurrentAttempt(
  runtime: AttemptRuntime,
  requestedAttemptId: string,
): void {
  if (runtime.state.session.attempt_id !== requestedAttemptId) {
    throw new Error("attempt response is invalid");
  }
}

function assertTimeAttempt(
  time: TimeSnapshot,
  requestedAttemptId: string,
  currentAttemptId: string,
): void {
  if (
    time.session.attempt_id !== requestedAttemptId ||
    time.session.attempt_id !== currentAttemptId
  ) {
    throw new Error("time response is invalid");
  }
}

export function cleanupAttempt(runtime: AttemptRuntime): void {
  if (runtime.disposed) return;
  runtime.disposed = true;
  runtime.operation.cancel();
  runtime.evaluation.cancel();
  runtime.source?.lock();
  runtime.prompt?.dispose();
  runtime.countdown?.stop();
  runtime.editor?.dispose();
  runtime.elements.destroy();
}

