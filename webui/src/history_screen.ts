import { apiGet, describeApiError } from "./api";
import { normalizeBootstrap, type Bootstrap } from "./state";
import {
  historyRequestPath,
  normalizeHistoryPage,
  readHistoryFragment,
  writeHistoryFragment,
  type HistoryPage,
  type HistoryQuery,
} from "./history_state";
import { renderHistory, type HistoryScreenState } from "./history_view";

/**
 * History screen controller. Every request is the metadata listing only; the
 * screen never touches source, review or lifecycle routes. Filter and cursor
 * changes are written to the fragment so back/forward and a later "Back to
 * history" restore the same page.
 */

export type HistoryScreenOptions = {
  root: HTMLElement;
  bootstrap: Bootstrap;
  isCurrent(): boolean;
  onReview(attemptId: string): void;
  onResume(attemptId: string): void;
  onLibrary(): void;
};

export function mountHistory(options: HistoryScreenOptions): void {
  const fragment = readHistoryFragment(window.location.hash);
  const state: HistoryScreenState = {
    bootstrap: options.bootstrap,
    query: fragment.query,
    page: null,
    loading: true,
    error: null,
    fragmentIssues: fragment.issues,
  };
  if (fragment.issues.length > 0) writeHistoryFragment(state.query);
  let requestGeneration = 0;
  let headingFocused = false;

  // Each render replaces the screen, so keyboard focus is carried across by
  // element id: the heading on first paint, otherwise whichever filter or
  // paging control the user was on.
  const render = (): void => {
    if (!options.isCurrent()) return;
    const active = document.activeElement as HTMLElement | null;
    const activeId = active && options.root.contains(active) ? active.id : "";
    const elements = renderHistory(options.root, state, {
      onFilters: (next) => {
        state.query = { ...state.query, ...next, cursor: null };
        state.fragmentIssues = [];
        writeHistoryFragment(state.query);
        void load();
      },
      onNewest: () => {
        state.query = { ...state.query, cursor: null };
        state.fragmentIssues = [];
        writeHistoryFragment(state.query);
        void load();
      },
      onOlder: (cursor) => {
        state.query = { ...state.query, cursor };
        writeHistoryFragment(state.query);
        void load();
      },
      onRefresh: () => void load(),
      onRetry: () => void load(),
      onReview: options.onReview,
      onResume: options.onResume,
      onLibrary: options.onLibrary,
    });
    const restored = activeId ? options.root.querySelector<HTMLElement>(`#${activeId}`) : null;
    if (restored && !restored.hasAttribute("disabled")) {
      restored.focus();
    } else if (!headingFocused || activeId) {
      // First paint, or the control the user was on is gone or disabled now:
      // the heading is the one stable place to land.
      elements.heading.focus();
    }
    headingFocused = true;
  };

  const load = async (): Promise<void> => {
    const generation = ++requestGeneration;
    state.loading = true;
    state.error = null;
    render();
    let page: HistoryPage;
    try {
      // The listing and the selected-session metadata are refreshed together so
      // the Resume action always reflects the attempt that is selected now.
      const [listing, bootstrap] = await Promise.all([
        apiGet(historyRequestPath(state.query)),
        apiGet("/api/bootstrap"),
      ]);
      page = normalizeHistoryPage(listing.data);
      const nextBootstrap = normalizeBootstrap(bootstrap.data);
      if (!options.isCurrent() || generation !== requestGeneration) return;
      state.bootstrap = nextBootstrap;
    } catch (error) {
      if (!options.isCurrent() || generation !== requestGeneration) return;
      const failure = describeApiError(error, "history");
      state.loading = false;
      state.page = null;
      state.error = { message: failure.message, recoverable: failure.recovery !== "none" };
      render();
      return;
    }
    if (!options.isCurrent() || generation !== requestGeneration) return;
    state.loading = false;
    state.page = page;
    render();
  };

  void load();
}

export type { HistoryQuery };
