import {
  apiGet,
  apiPost,
  captureCapability,
  describeApiError,
  loadManifest,
  type StaticManifest,
} from "./api";
import {
  entryState,
  errorState,
  initialState,
  normalizeAttempt,
  normalizeBootstrap,
  normalizeTime,
  type Bootstrap,
} from "./state";
import {
  renderBooting,
  renderEntry,
  renderError,
  renderReconnect,
} from "./views";
import {
  disposeAttempt,
  showAttempt,
  showTerminalAttempt,
} from "./attempt_runtime";

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
    ), {
      label: "Reload local simulator",
      onClick: () => window.location.reload(),
    });
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
        const retryable = error instanceof Error &&
          ["session_unavailable", "lifecycle_locked", "invalid_input"]
            .includes((error as { code?: string }).code || "");
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
    if (time.session.attempt_id !== bootstrap.session.attempt_id) {
      throw new Error("time response is invalid");
    }
    if (time.session.status !== "active") {
      await showTerminalAttempt(root, manifest, bootstrap, time);
      return;
    }
    const source = await apiGet(`/api/source${query}`);
    showAttempt(root, manifest, bootstrap, normalizeAttempt({
      session: time.session,
      source: source.data,
      time,
    }));
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

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", () => void start(), { once: true });
} else {
  void start();
}
