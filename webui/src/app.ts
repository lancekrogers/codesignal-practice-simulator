import {
  apiGet,
  apiPost,
  ApiError,
  captureCapability,
  describeApiError,
  loadManifest,
  type StaticManifest,
} from "./api";
import { initializeEditor } from "./editor";
import {
  attemptState,
  createCountdown,
  entryState,
  errorState,
  initialState,
  normalizeAttempt,
  normalizeBootstrap,
  normalizeTime,
  workerUrls,
  type Bootstrap,
} from "./state";
import {
  renderAttemptShell,
  renderBooting,
  renderEntry,
  renderError,
  renderReconnect,
  showEditor,
  showFallback,
  type ShellElements,
} from "./views";
import { createPromptController } from "./prompt_controller";

let currentAttemptCleanup: (() => void) | null = null;

async function start(): Promise<void> {
  captureCapability();
  const root = document.getElementById("app");
  if (!root) throw new Error("application mount is missing");
  let manifest: StaticManifest = {};
  renderBooting(root, initialState());
  try {
    const bootstrap = normalizeBootstrap((await apiGet("/api/bootstrap")).data);
    manifest = await loadManifest();
    showEntry(root, manifest, bootstrap);
  } catch (error) {
    renderError(root, errorState(
      manifest,
      describeApiError(error, "bootstrap").message,
    ), { label: "Reload local simulator", onClick: () => window.location.reload() });
  }
}

function showEntry(
  root: HTMLElement,
  manifest: StaticManifest,
  bootstrap: Bootstrap,
): void {
  disposeAttempt();
  let startRequested = false;
  let elements: ReturnType<typeof renderEntry>;
  elements = renderEntry(
    root,
    entryState(manifest, bootstrap),
    async (mode, duration) => {
      if (startRequested) return;
      startRequested = true;
      elements.setBusy(true);
      elements.setMessage("Starting the local practice session…");
      try {
        const body: Record<string, unknown> = {
          assessment: bootstrap.assessment.assessment_id,
          mode,
        };
        if (mode === "drill") body.drill_duration_seconds = duration;
        const payload = normalizeAttempt((await apiPost("/api/attempts", body)).data);
        if (payload.session.status !== "active" || payload.source === null) {
          throw new Error("start response is invalid");
        }
        elements.destroy();
        showAttempt(root, manifest, bootstrap, payload);
      } catch (error) {
        const retryable = error instanceof ApiError &&
          ["session_unavailable", "lifecycle_locked", "invalid_input"]
            .includes(error.code);
        elements.setBusy(!retryable);
        elements.setMessage(describeApiError(error, "start").message);
        if (retryable) startRequested = false;
      }
    },
    bootstrap.session
      ? () => {
          elements.destroy();
          void reconnect(root, manifest, bootstrap);
        }
      : undefined,
  );
}

async function reconnect(
  root: HTMLElement,
  manifest: StaticManifest,
  bootstrap: Bootstrap,
): Promise<void> {
  if (!bootstrap.session) return;
  disposeAttempt();
  renderReconnect(root, entryState(manifest, bootstrap));
  try {
    const query = `?attempt_id=${encodeURIComponent(bootstrap.session.attempt_id)}`;
    const time = normalizeTime((await apiGet(`/api/time${query}`)).data);
    if (time.session.status !== "active") {
      showAttempt(root, manifest, bootstrap, {
        session: time.session,
        source: null,
        time,
      });
      return;
    }
    const sourceDocument = await apiGet(`/api/source${query}`);
    const payload = normalizeAttempt({
      session: time.session,
      source: sourceDocument.data,
      time,
    });
    showAttempt(root, manifest, bootstrap, payload);
  } catch (error) {
    renderError(root, errorState(
      manifest,
      describeApiError(error, "reconnect").message,
    ), {
      label: "Reconnect selected session",
      onClick: () => void reconnect(root, manifest, bootstrap),
    });
  }
}

function showAttempt(
  root: HTMLElement,
  manifest: StaticManifest,
  bootstrap: Bootstrap,
  payload: ReturnType<typeof normalizeAttempt>,
): void {
  disposeAttempt();
  const state = attemptState(manifest, bootstrap, payload);
  let elements: ShellElements;
  let promptController: ReturnType<typeof createPromptController> | null = null;
  elements = renderAttemptShell(root, state, {
    onLevelSelect: (level) => {
      promptController?.selectLevel(level);
    },
    onPromptTab: (tab) => {
      promptController?.selectTab(tab);
    },
  });
  promptController = createPromptController(elements, state);
  let editorHandle: { dispose(): void } | undefined;
  let countdown: { stop(): void } | undefined;
  let disposed = false;
  const cleanup = (): void => {
    if (disposed) return;
    disposed = true;
    promptController?.dispose();
    countdown?.stop();
    editorHandle?.dispose();
    elements.destroy();
    if (currentAttemptCleanup === cleanup) currentAttemptCleanup = null;
  };
  currentAttemptCleanup = cleanup;

  if (state.session.status !== "active" || state.source === null) return;
  editorHandle = startEditor(elements, state.source, manifest);
  countdown = startAttemptCountdown(
    root,
    manifest,
    bootstrap,
    payload,
    elements,
    cleanup,
  );
  promptController.loadInitial();
}

function startEditor(
  elements: ShellElements,
  source: string,
  manifest: StaticManifest,
): { dispose(): void } | undefined {
  try {
    const editor = initializeEditor(
      elements,
      source,
      workerUrls(manifest),
      () => elements.setSaveState(true),
    );
    showEditor(elements);
    return editor;
  } catch {
    showFallback(elements, "The Python editor could not initialize.");
    return undefined;
  }
}

function startAttemptCountdown(
  root: HTMLElement,
  manifest: StaticManifest,
  bootstrap: Bootstrap,
  payload: ReturnType<typeof normalizeAttempt>,
  elements: ShellElements,
  cleanup: () => void,
): { stop(): void } {
  return createCountdown(
    payload.time,
    (update) => {
      elements.setCountdown(update.remainingSeconds);
      if (update.session.status !== "active") {
        cleanup();
        showAttempt(root, manifest, bootstrap, {
          session: update.session,
          source: null,
          time: update.time,
        });
      }
    },
    async () => {
      elements.setConnection("reconnecting");
      const query = `?attempt_id=${encodeURIComponent(payload.session.attempt_id)}`;
      const next = normalizeTime((await apiGet(`/api/time${query}`)).data);
      if (next.session.attempt_id !== payload.session.attempt_id) {
        throw new Error("time response is invalid");
      }
      elements.setConnection("connected");
      return next;
    },
    () => elements.setConnection("reconnecting"),
  );
}

function disposeAttempt(): void {
  currentAttemptCleanup?.();
  currentAttemptCleanup = null;
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", () => void start(), { once: true });
} else {
  void start();
}
