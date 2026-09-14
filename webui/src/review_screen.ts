import {
  abandonAttempt,
  apiGet,
  apiPost,
  describeApiError,
} from "./api";
import { normalizeAttempt, normalizeBootstrap, normalizeTime, type Bootstrap } from "./state";
import { normalizeReview } from "./review_state";
import {
  renderReview,
  type ReviewElements,
  type ReviewScreenState,
  type RetryPlan,
} from "./review_view";

/**
 * Review screen controller. Loads the stored review (and, for an attempt that
 * was never submitted, its saved work through the ordinary source route) and
 * never posts anything except the explicitly confirmed retry, which starts a
 * new attempt and, only when the user chose it, ends the live one first.
 */

export type ReviewScreenOptions = {
  root: HTMLElement;
  bootstrap: Bootstrap;
  attemptId: string;
  isCurrent(): boolean;
  onOpenAttempt(attemptId: string): void;
  onHistory(): void;
  onLibrary(): void;
};

export function mountReview(options: ReviewScreenOptions): { destroy(): void } {
  const state: ReviewScreenState = {
    bootstrap: options.bootstrap,
    attemptId: options.attemptId,
    review: null,
    savedWork: { kind: "none" },
    loading: true,
    error: null,
    message: null,
    busy: false,
  };
  let elements: ReviewElements | null = null;
  let headingFocused = false;
  let requestGeneration = 0;

  const render = (): void => {
    if (!options.isCurrent()) return;
    const active = document.activeElement as HTMLElement | null;
    const activeId = active && options.root.contains(active) ? active.id : "";
    elements?.destroy();
    elements = renderReview(options.root, state, {
      onRetryStart: (plan) => void startRetry(plan, null),
      onResumeLive: (attemptId) => options.onOpenAttempt(attemptId),
      onEndLiveAndStart: (plan) => void startRetry(plan, plan.liveAttemptId),
      onReload: () => void load(),
      onHistory: options.onHistory,
      onLibrary: options.onLibrary,
    });
    const restored = activeId ? options.root.querySelector<HTMLElement>(`#${activeId}`) : null;
    if (restored && !restored.hasAttribute("disabled")) restored.focus();
    // First paint, or the control the user was on is gone or disabled now.
    else if (!headingFocused || activeId) elements.heading.focus();
    headingFocused = true;
  };

  const load = async (): Promise<void> => {
    const generation = ++requestGeneration;
    state.loading = true;
    state.error = null;
    state.message = null;
    render();
    try {
      const document = await apiGet(
        `/api/attempts/${encodeURIComponent(options.attemptId)}/review?include_source=true`,
      );
      const review = normalizeReview(document.data, options.attemptId);
      if (!options.isCurrent() || generation !== requestGeneration) return;
      state.review = review;
      if (review.status !== "submitted") {
        // Saved work of a never-submitted attempt: read by explicit id through
        // the ordinary source route, labelled as saved work, never as submitted.
        try {
          const source = await apiGet(
            `/api/source?attempt_id=${encodeURIComponent(options.attemptId)}`,
          );
          const content = source.data?.content;
          const etag = source.data?.etag;
          state.savedWork = typeof content === "string" && typeof etag === "string"
            ? { kind: "loaded", content, etag }
            : { kind: "unavailable" };
        } catch {
          state.savedWork = { kind: "unavailable" };
        }
        if (!options.isCurrent() || generation !== requestGeneration) return;
      }
    } catch (error) {
      if (!options.isCurrent() || generation !== requestGeneration) return;
      const failure = describeApiError(error, "review");
      state.loading = false;
      state.review = null;
      state.error = {
        title: failure.kind === "unavailable" ? "Attempt not found" : "Review unavailable",
        message: failure.message,
        retryable: failure.recovery !== "none",
      };
      render();
      return;
    }
    state.loading = false;
    render();
  };

  const startRetry = async (plan: RetryPlan, endFirst: string | null): Promise<void> => {
    if (state.busy || !plan.entry || !state.review) return;
    state.busy = true;
    state.message = endFirst
      ? "Ending the active attempt and starting a new one…"
      : "Starting a new attempt…";
    render();
    try {
      if (endFirst) {
        const query = `?attempt_id=${encodeURIComponent(endFirst)}`;
        const time = normalizeTime((await apiGet(`/api/time${query}`)).data);
        if (time.session.attempt_id !== endFirst) throw new Error("time response is invalid");
        if (time.session.status === "active") {
          const revision = time.session.revision;
          if (!Number.isInteger(revision)) throw new Error("session revision is unavailable");
          await abandonAttempt(endFirst, revision as number);
        }
      }
      const body: Record<string, unknown> = {
        assessment: plan.entry.assessment_id,
        mode: state.review.profile.mode,
      };
      if (state.review.profile.mode === "drill") {
        body.drill_duration_seconds = state.review.profile.duration_seconds;
      }
      const payload = normalizeAttempt((await apiPost("/api/attempts", body)).data);
      if (payload.session.status !== "active") throw new Error("start response is invalid");
      if (!options.isCurrent()) return;
      options.onOpenAttempt(payload.session.attempt_id);
    } catch (error) {
      if (!options.isCurrent()) return;
      state.busy = false;
      state.message = describeApiError(error, endFirst ? "ending" : "start").message;
      // The live selection may have changed; refresh what Retry would do next.
      try {
        state.bootstrap = normalizeBootstrap((await apiGet("/api/bootstrap")).data);
      } catch {
        // Keep the previous bootstrap; the message already explains the failure.
      }
      if (!options.isCurrent()) return;
      render();
    }
  };

  void load();
  return { destroy: () => elements?.destroy() };
}
