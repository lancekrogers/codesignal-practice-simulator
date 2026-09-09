import { apiGet } from "./api";
import { normalizePrompt, type AttemptState, type PromptTab } from "./state";
import type { ShellElements } from "./views";

type PromptRequest = {
  generation: number;
  level: number;
  tab: PromptTab;
};

export type PromptController = {
  selectLevel(level: number): void;
  selectTab(tab: PromptTab): void;
  loadInitial(): void;
  dispose(): void;
};

export function createPromptController(
  elements: ShellElements,
  state: AttemptState,
): PromptController {
  let selectedLevel = state.selectedLevel;
  let selectedTab = state.selectedTab;
  let generation = 0;
  let disposed = false;

  const current = (request: PromptRequest): boolean =>
    !disposed &&
    request.generation === generation &&
    request.level === selectedLevel &&
    request.tab === selectedTab;

  const requestDescription = (level: number, requestGeneration: number): void => {
    const request = {
      generation: requestGeneration,
      level,
      tab: "description" as const,
    };
    elements.setPromptLoading(level);
    void apiGet(
      `/api/prompts/${level}?attempt_id=${encodeURIComponent(state.session.attempt_id)}`,
    )
      .then((response) => {
        const prompt = normalizePrompt(response.data);
        if (
          prompt.attempt_id !== state.session.attempt_id ||
          prompt.level !== level ||
          !current(request)
        ) {
          throw new Error("prompt response is invalid");
        }
        elements.setPrompt(prompt.prompt);
      })
      .catch(() => {
        if (current(request)) elements.setPromptError();
      });
  };

  const renderTab = (): void => {
    const requestGeneration = ++generation;
    if (selectedTab === "description") {
      requestDescription(selectedLevel, requestGeneration);
      return;
    }
    if (selectedTab === "rules") {
      elements.setPrompt(state.bootstrap.rules.join("\n\n"));
    } else if (selectedTab === "history") {
      elements.setPrompt(
        "Source history will be available after history wiring is enabled.",
      );
    } else {
      elements.setPrompt(
        `Assessment: ${state.bootstrap.assessment.display_name}\nMode: ${
          state.session.profile?.mode || "selected"
        }\nLevels: ${state.bootstrap.assessment.level_count}`,
      );
    }
  };

  return {
    selectLevel(level) {
      selectedLevel = level;
      const requestGeneration = ++generation;
      if (selectedTab === "description") {
        requestDescription(level, requestGeneration);
      }
    },
    selectTab(tab) {
      selectedTab = tab;
      renderTab();
    },
    loadInitial() {
      renderTab();
    },
    dispose() {
      disposed = true;
      generation += 1;
    },
  };
}
