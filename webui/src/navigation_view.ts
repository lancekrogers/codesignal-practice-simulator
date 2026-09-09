import { createRovingNavigation } from "./a11y";
import type { AttemptState, PromptTab } from "./state";

export type LevelNavigation = {
  element: HTMLElement;
  buttons: HTMLButtonElement[];
  dispose: () => void;
};

export type PromptElements = {
  element: HTMLElement;
  tabButtons: HTMLButtonElement[];
  body: HTMLElement;
  dispose: () => void;
};

export function createLevelNavigation(
  state: AttemptState,
  onSelect: (level: number) => void,
): LevelNavigation {
  const nav = element("nav", "level-navigation");
  nav.setAttribute("aria-label", "Assessment levels");
  const title = element("span", "nav-label");
  title.textContent = "Levels";
  const list = element("ol", "level-list");
  const buttons: HTMLButtonElement[] = [];
  const clickHandlers: Array<() => void> = [];
  let roving: ReturnType<typeof createRovingNavigation>;
  const selectLevel = (level: number): void => updateLevelSelection(state, buttons, roving, level);
  state.bootstrap.levels.forEach((item) => {
    const listItem = element("li");
    const levelButton = button(`${item.level}. ${item.label}`, "level-button");
    levelButton.setAttribute("aria-label", `Level ${item.level}: ${item.label}`);
    levelButton.setAttribute(
      "aria-current",
      item.level === state.selectedLevel ? "step" : "false",
    );
    levelButton.dataset.enabled = "true";
    const onClick = (): void => { selectLevel(item.level); onSelect(item.level); };
    levelButton.addEventListener("click", onClick);
    clickHandlers.push(onClick);
    buttons.push(levelButton);
    listItem.append(levelButton);
    list.append(listItem);
  });
  roving = createRovingNavigation(buttons, {
    activate: (index) => {
      const item = state.bootstrap.levels[index];
      if (!item) return;
      selectLevel(item.level);
      onSelect(item.level);
    },
  });
  nav.append(title, list);
  return {
    element: nav,
    buttons,
    dispose: () => {
      roving.dispose();
      removeClickHandlers(buttons, clickHandlers);
    },
  };

}

function updateLevelSelection(
  state: AttemptState,
  buttons: HTMLButtonElement[],
  roving: ReturnType<typeof createRovingNavigation>,
  level: number,
): void {
  buttons.forEach((candidate, index) => {
    const selected = state.bootstrap.levels[index]?.level === level;
    candidate.setAttribute("aria-current", selected ? "step" : "false");
  });
  roving.setActive(state.bootstrap.levels.findIndex((item) => item.level === level));
}

export function createPromptPane(
  state: AttemptState,
  onTabSelect: (tab: PromptTab) => void,
): PromptElements {
  const pane = element("aside", "prompt-pane");
  pane.dataset.testid = "prompt-pane";
  pane.setAttribute("aria-labelledby", "prompt-title");
  const title = element("h2");
  title.id = "prompt-title";
  title.textContent = "Problem";
  const tabs = element("div", "prompt-tabs");
  tabs.setAttribute("role", "tablist");
  tabs.setAttribute("aria-label", "Problem information");
  const tabLabels: Array<[PromptTab, string]> = [
    ["description", "Description"],
    ["history", "History"],
    ["rules", "Rules"],
    ["info", "Info"],
  ];
  const body = element("div", "prompt-copy");
  body.id = "prompt-content";
  body.setAttribute("role", "tabpanel");
  body.tabIndex = 0;
  body.setAttribute("aria-live", "polite");
  body.textContent = "Loading Level 1 description…";
  const controls = createPromptTabs(
    state,
    body,
    tabs,
    tabLabels,
    onTabSelect,
  );
  body.setAttribute("aria-labelledby", "prompt-tab-description");
  pane.append(title, tabs, body);
  return {
    element: pane,
    tabButtons: controls.tabButtons,
    body,
    dispose: () => {
      controls.roving.dispose();
      removeClickHandlers(controls.tabButtons, controls.clickHandlers);
    },
  };
}

function updateTabSelection(
  tabLabels: Array<[PromptTab, string]>,
  tabButtons: HTMLButtonElement[],
  body: HTMLElement,
  roving: ReturnType<typeof createRovingNavigation>,
  selected: PromptTab,
): void {
  tabButtons.forEach((candidate, index) => {
    const current = tabLabels[index]?.[0] === selected;
    candidate.setAttribute("aria-selected", current ? "true" : "false");
    candidate.tabIndex = current ? 0 : -1;
    if (current) body.setAttribute("aria-labelledby", candidate.id);
  });
  roving.setActive(tabLabels.findIndex(([value]) => value === selected));
}

function createPromptTabs(
  state: AttemptState,
  body: HTMLElement,
  tabs: HTMLElement,
  tabLabels: Array<[PromptTab, string]>,
  onTabSelect: (tab: PromptTab) => void,
): {
  tabButtons: HTMLButtonElement[];
  clickHandlers: Array<() => void>;
  roving: ReturnType<typeof createRovingNavigation>;
} {
  const tabButtons: HTMLButtonElement[] = [];
  const clickHandlers: Array<() => void> = [];
  let roving: ReturnType<typeof createRovingNavigation>;
  const selectTab = (selected: PromptTab): void =>
    updateTabSelection(tabLabels, tabButtons, body, roving, selected);
  tabLabels.forEach(([tab, label]) => {
    const tabButton = button(label, "tab-button");
    tabButton.id = `prompt-tab-${tab}`;
    tabButton.setAttribute("role", "tab");
    tabButton.setAttribute("aria-selected", String(tab === state.selectedTab));
    tabButton.tabIndex = tab === state.selectedTab ? 0 : -1;
    tabButton.setAttribute("aria-controls", body.id);
    tabButton.dataset.enabled = "true";
    const onClick = (): void => {
      selectTab(tab);
      onTabSelect(tab);
    };
    tabButton.addEventListener("click", onClick);
    clickHandlers.push(onClick);
    tabButtons.push(tabButton);
    tabs.append(tabButton);
  });
  roving = createRovingNavigation(tabButtons, {
    activate: (index) => {
      const selected = tabLabels[index]?.[0];
      if (!selected) return;
      selectTab(selected);
      onTabSelect(selected);
    },
  });
  return { tabButtons, clickHandlers, roving };
}

function button(label: string, className: string): HTMLButtonElement {
  const result = document.createElement("button");
  result.type = "button";
  result.className = className;
  result.textContent = label;
  return result;
}

function element<K extends keyof HTMLElementTagNameMap>(
  tag: K,
  className = "",
): HTMLElementTagNameMap[K] {
  const result = document.createElement(tag);
  if (className) result.className = className;
  return result;
}

function removeClickHandlers(
  buttons: HTMLButtonElement[],
  handlers: Array<() => void>,
): void {
  buttons.forEach((button, index) => {
    const handler = handlers[index];
    if (handler) button.removeEventListener("click", handler);
  });
}
