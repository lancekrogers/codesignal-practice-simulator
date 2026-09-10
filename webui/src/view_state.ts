export type PromptTab = "description" | "history" | "rules" | "info";

export type AttemptViewState = {
  level: number;
  tab: PromptTab;
};

const DEFAULT_VIEW: AttemptViewState = {
  level: 1,
  tab: "description",
};

export function defaultAttemptViewState(): AttemptViewState {
  return { ...DEFAULT_VIEW };
}

export function readAttemptViewState(
  authoritativeAttemptId: string,
): AttemptViewState {
  if (typeof window === "undefined" || !authoritativeAttemptId) {
    return defaultAttemptViewState();
  }
  const params = new URLSearchParams(window.location.hash.slice(1));
  if (params.get("attempt_id") !== authoritativeAttemptId) {
    return defaultAttemptViewState();
  }
  const level = Number(params.get("level"));
  const tab = params.get("tab");
  if (!isLevel(level) || !isPromptTab(tab)) {
    return defaultAttemptViewState();
  }
  return {
    level,
    tab,
  };
}

export function writeAttemptViewState(
  attemptId: string,
  view: AttemptViewState,
): void {
  if (typeof window === "undefined" || !attemptId) return;
  const params = new URLSearchParams();
  params.set("attempt_id", attemptId);
  params.set("level", String(isLevel(view.level) ? view.level : DEFAULT_VIEW.level));
  params.set("tab", isPromptTab(view.tab) ? view.tab : DEFAULT_VIEW.tab);
  window.history.replaceState(
    null,
    "",
    `${window.location.pathname}#${params.toString()}`,
  );
}

function isLevel(value: number): value is 1 | 2 | 3 | 4 {
  return Number.isInteger(value) && value >= 1 && value <= 4;
}

function isPromptTab(value: string | null): value is PromptTab {
  return value === "description" ||
    value === "history" ||
    value === "rules" ||
    value === "info";
}
