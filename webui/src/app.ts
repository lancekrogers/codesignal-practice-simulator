import { apiGet, captureCapability, loadManifest } from "./api";
import { initializeEditor } from "./editor";
import { initialState, workerUrls, type Bootstrap } from "./state";
import { renderShell, showEditor, showFallback } from "./views";

async function start(): Promise<void> {
  captureCapability();
  const root = document.getElementById("app");
  if (!root) throw new Error("application mount is missing");

  let manifest = {};
  let bootstrap: Bootstrap | null = null;
  let source = "";
  try {
    manifest = await loadManifest();
    const document = await apiGet("/api/bootstrap");
    bootstrap = (document.data || {}) as Bootstrap;
    const attemptId = bootstrap.session?.attempt_id;
    if (attemptId) {
      const sourceDocument = await apiGet(
        `/api/source?attempt_id=${encodeURIComponent(attemptId)}`,
      );
      source = String(sourceDocument.data?.content || "");
    }
  } catch {
    const elements = renderShell(root, initialState(manifest, bootstrap, source));
    showFallback(elements, "The local editor could not load.");
    return;
  }

  const state = initialState(manifest, bootstrap, source);
  const elements = renderShell(root, state);
  try {
    initializeEditor(elements, source, workerUrls(manifest));
    showEditor(elements);
  } catch {
    showFallback(elements, "The Monaco editor could not initialize.");
  }
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", () => void start(), { once: true });
} else {
  void start();
}
