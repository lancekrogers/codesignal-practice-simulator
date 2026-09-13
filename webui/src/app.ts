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
  renderError,
  renderReconnect,
} from "./views";
import {
  renderAttemptEntry,
  renderLibrary,
  type LibraryElements,
} from "./library_view";
import { mountHistory } from "./history_screen";
import { mountReview } from "./review_screen";
import {
  announceInAttempt,
  disposeAttempt,
  settleAttemptBeforeLeaving,
  showAttempt,
  showTerminalAttempt,
} from "./attempt_runtime";
import {
  currentRoute,
  installRouter,
  navigateTo,
  registerAttemptOpener,
  type Route,
} from "./router";

/**
 * Route-driven application shell (D004). Every route loads metadata only:
 * bootstrap for the library, plus the time snapshot and the attempt's own
 * source for an attempt route. Nothing here creates an attempt; only the
 * confirmed start form posts to /api/attempts.
 */

type Screen = {
  root: HTMLElement;
  manifest: StaticManifest;
  generation: number;
  library: LibraryElements | null;
};

let routeGeneration = 0;
let screen: Screen | null = null;

async function start(): Promise<void> {
  captureCapability();
  const root = document.getElementById("app");
  if (!root) throw new Error("application mount is missing");
  screen = { root, manifest: {}, generation: 0, library: null };
  installRouter((route) => void showRoute(route));
  registerAttemptOpener((attemptId) => void openChosenAttempt(attemptId));
  await showRoute(currentRoute());
}

/** An explicitly chosen attempt (restart replacement): route silently, reconnect. */
async function openChosenAttempt(attemptId: string): Promise<void> {
  if (!screen) return;
  const generation = ++routeGeneration;
  screen.generation = generation;
  screen.library?.destroy();
  screen.library = null;
  disposeAttempt();
  navigateTo({ kind: "attempt", attemptId }, { silent: true });
  const bootstrap = await loadBootstrap(screen.root, generation);
  if (!bootstrap || !screen) return;
  await reconnect(screen.root, screen.manifest, bootstrap, attemptId, generation);
}

async function showRoute(route: Route): Promise<void> {
  if (!screen) return;
  // A live attempt left through the browser's own navigation (back, forward,
  // a typed address) gets the same protection as the Leave dialog: pending
  // saves are flushed first, and text that cannot be saved keeps the attempt
  // open and restores its address instead of being discarded silently.
  const settlement = await settleAttemptBeforeLeaving();
  if (settlement.kind === "unsaved") {
    if (route.kind !== "attempt" || route.attemptId !== settlement.attemptId) {
      navigateTo({ kind: "attempt", attemptId: settlement.attemptId }, { silent: true });
    }
    announceInAttempt(
      "Your latest edits could not be saved, so this attempt stays open. Save them, or use Back to library to discard them explicitly.",
    );
    return;
  }
  if (settlement.kind === "clear" && route.kind === "attempt" && route.attemptId === settlement.attemptId) {
    // Back/forward onto the attempt that is already open: keep it as it is.
    return;
  }
  const generation = ++routeGeneration;
  screen.generation = generation;
  screen.library?.destroy();
  screen.library = null;
  disposeAttempt();
  const root = screen.root;
  switch (route.kind) {
    case "library":
      await showLibrary(root, generation);
      return;
    case "attempt":
      await showAttemptRoute(root, generation, route.attemptId);
      return;
    case "history":
      await showHistoryRoute(root, generation);
      return;
    case "review":
      await showReviewRoute(root, generation, route.attemptId);
      return;
    default:
      showUnknownRoute(root, route.path);
  }
}

function current(generation: number): boolean {
  return screen !== null && screen.generation === generation && routeGeneration === generation;
}

async function loadBootstrap(root: HTMLElement, generation: number): Promise<Bootstrap | null> {
  renderBooting(root, initialState());
  try {
    const bootstrap = normalizeBootstrap((await apiGet("/api/bootstrap")).data);
    if (!current(generation)) return null;
    if (screen && Object.keys(screen.manifest).length === 0) {
      screen.manifest = await loadManifest();
      if (!current(generation)) return null;
    }
    return bootstrap;
  } catch (error) {
    if (!current(generation)) return null;
    focus(renderError(root, errorState(
      screen?.manifest || {},
      describeApiError(error, "bootstrap").message,
    ), {
      label: "Reload local simulator",
      onClick: () => window.location.reload(),
    }));
    return null;
  }
}

async function showLibrary(root: HTMLElement, generation: number): Promise<void> {
  const bootstrap = await loadBootstrap(root, generation);
  if (!bootstrap || !screen) return;
  const manifest = screen.manifest;
  let startRequested = false;
  const elements = renderLibrary(root, entryState(manifest, bootstrap), {
    onStart: async (assessmentId, mode, duration) => {
      if (startRequested || !current(generation)) return;
      startRequested = true;
      elements.setBusy(true);
      elements.setMessage("Starting the local practice session…");
      try {
        const body: Record<string, unknown> = { assessment: assessmentId, mode };
        if (mode === "drill") body.drill_duration_seconds = duration;
        const payload = normalizeAttempt((await apiPost("/api/attempts", body)).data);
        if (payload.session.status !== "active" || payload.source === null) {
          throw new Error("start response is invalid");
        }
        if (!current(generation) || !screen) return;
        elements.destroy();
        screen.library = null;
        navigateTo({ kind: "attempt", attemptId: payload.session.attempt_id }, { silent: true });
        screen.generation = ++routeGeneration;
        showAttempt(root, manifest, bootstrap, payload);
      } catch (error) {
        if (!current(generation)) return;
        const retryable = error instanceof Error &&
          ["session_unavailable", "lifecycle_locked", "invalid_input"]
            .includes((error as { code?: string }).code || "");
        elements.setBusy(!retryable);
        elements.setMessage(describeApiError(error, "start").message);
        if (retryable) startRequested = false;
      }
    },
    onResume: () => {
      // Resume is the explicit action: move to the attempt route and reconnect
      // directly instead of showing the route's continue screen again.
      if (!bootstrap.session || !current(generation) || !screen) return;
      elements.destroy();
      screen.library = null;
      const attemptId = bootstrap.session.attempt_id;
      navigateTo({ kind: "attempt", attemptId }, { silent: true });
      const next = ++routeGeneration;
      screen.generation = next;
      void reconnect(root, manifest, bootstrap, attemptId, next);
    },
    onHistory: () => navigateTo({ kind: "history" }),
  });
  screen.library = elements;
  focus(elements.heading);
}

/**
 * A cold attempt route (reload, back, forward, typed address) shows the
 * continue screen from metadata only. The selected session comes from the
 * bootstrap; any other stored attempt is described by its time snapshot. The
 * attempt's source is requested only after the explicit reconnect action.
 */
async function showAttemptRoute(
  root: HTMLElement,
  generation: number,
  attemptId: string,
): Promise<void> {
  const bootstrap = await loadBootstrap(root, generation);
  if (!bootstrap || !screen) return;
  const manifest = screen.manifest;
  let session = bootstrap.session?.attempt_id === attemptId ? bootstrap.session : null;
  if (!session) {
    try {
      const query = `?attempt_id=${encodeURIComponent(attemptId)}`;
      const time = normalizeTime((await apiGet(`/api/time${query}`)).data);
      if (time.session.attempt_id !== attemptId) {
        throw new Error("time response is invalid");
      }
      session = time.session;
    } catch (error) {
      if (!current(generation)) return;
      showAttemptFailure(root, manifest, bootstrap, attemptId, generation, error, true);
      return;
    }
    if (!current(generation)) return;
  }
  const heading = renderAttemptEntry(root, entryState(manifest, bootstrap), session, {
    onResume: () => {
      if (!current(generation) || !screen) return;
      const next = ++routeGeneration;
      screen.generation = next;
      void reconnect(root, manifest, bootstrap, attemptId, next);
    },
    onLibrary: () => navigateTo({ kind: "library" }),
  });
  focus(heading);
}

function showAttemptFailure(
  root: HTMLElement,
  manifest: StaticManifest,
  bootstrap: Bootstrap,
  attemptId: string,
  generation: number,
  error: unknown,
  addressLookup = false,
): void {
  const failure = describeApiError(error, "reconnect");
  // Only the route's own metadata lookup can say the address names no stored
  // attempt; a 404 while reconnecting a known attempt keeps the existing safe
  // "fixture or selected session is unavailable" message.
  const notFound = addressLookup && error instanceof Error &&
    (error as { status?: number }).status === 404;
  focus(renderError(root, errorState(
    manifest,
    notFound
      ? "No attempt with this address is stored locally. It may have been removed, or the address may be mistyped."
      : failure.message,
  ), [
    { label: "Back to library", onClick: () => navigateTo({ kind: "library" }) },
    {
      label: "Reconnect selected session",
      onClick: () => void reconnect(root, manifest, bootstrap, attemptId, generation),
    },
  ], notFound ? "Attempt not found" : "Assessment unavailable"));
}

async function reconnect(
  root: HTMLElement,
  manifest: StaticManifest,
  bootstrap: Bootstrap,
  attemptId: string,
  generation: number,
): Promise<void> {
  disposeAttempt();
  renderReconnect(root, entryState(manifest, bootstrap));
  try {
    const query = `?attempt_id=${encodeURIComponent(attemptId)}`;
    const time = normalizeTime((await apiGet(`/api/time${query}`)).data);
    if (time.session.attempt_id !== attemptId) {
      throw new Error("time response is invalid");
    }
    if (!current(generation)) return;
    if (time.session.status !== "active") {
      await showTerminalAttempt(root, manifest, bootstrap, time);
      return;
    }
    const source = await apiGet(`/api/source${query}`);
    if (!current(generation)) return;
    showAttempt(root, manifest, bootstrap, normalizeAttempt({
      session: time.session,
      source: source.data,
      time,
    }));
  } catch (error) {
    if (!current(generation)) return;
    showAttemptFailure(root, manifest, bootstrap, attemptId, generation, error);
  }
}

async function showHistoryRoute(root: HTMLElement, generation: number): Promise<void> {
  const bootstrap = await loadBootstrap(root, generation);
  if (!bootstrap) return;
  mountHistory({
    root,
    bootstrap,
    isCurrent: () => current(generation),
    // Review keeps the fragment (filters and cursor) so Back to history
    // restores the same page; it never selects the reviewed attempt.
    onReview: (attemptId) => navigateTo({ kind: "review", attemptId }),
    // Resume is offered only for the selected active attempt, so opening it
    // is the same explicit action as the library's reconnect.
    onResume: (attemptId) => void openChosenAttempt(attemptId),
    onLibrary: () => navigateTo({ kind: "library" }),
  });
}

async function showReviewRoute(
  root: HTMLElement,
  generation: number,
  attemptId: string,
): Promise<void> {
  const bootstrap = await loadBootstrap(root, generation);
  if (!bootstrap || !screen) return;
  const mounted = mountReview({
    root,
    bootstrap,
    attemptId,
    isCurrent: () => current(generation),
    // Retry (after confirmation) and "Resume active attempt" are explicit
    // actions, so the chosen attempt opens directly.
    onOpenAttempt: (chosen) => {
      mounted.destroy();
      void openChosenAttempt(chosen);
    },
    onHistory: () => navigateTo({ kind: "history" }),
    onLibrary: () => navigateTo({ kind: "library" }),
  });
}

function showUnknownRoute(root: HTMLElement, _path: string): void {
  focus(renderError(root, errorState(
    screen?.manifest || {},
    "This address does not match a library, attempt, history, or review screen.",
  ), [
    { label: "Back to library", onClick: () => navigateTo({ kind: "library" }, { replace: true }) },
  ], "Page not found"));
}

function focus(heading: HTMLElement): void {
  heading.focus({ preventScroll: false });
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", () => void start(), { once: true });
} else {
  void start();
}
