import { createRovingNavigation } from "./a11y";
import type { AttemptState } from "./state";
import type { PromptTab } from "./view_state";
import type { SourceHistory } from "./source_api";

export type LevelNavigation = {
  element: HTMLElement;
  buttons: HTMLButtonElement[];
  focusLevel(level: number): void;
  refreshStatus(): void;
  dispose: () => void;
};

export type PromptElements = {
  element: HTMLElement;
  tabButtons: HTMLButtonElement[];
  body: HTMLElement;
  setHistory(
    history: SourceHistory,
    onRestore: (snapshotId: string, opener: HTMLElement) => void,
  ): void;
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
  const buttons: HTMLButtonElement[] = [];
  const markers: HTMLElement[] = [];
  const clickHandlers: Array<() => void> = [];
  let roving: ReturnType<typeof createRovingNavigation>;
  const selectLevel = (level: number): void => {
    state.selectedLevel = level;
    updateLevelSelection(state, buttons, roving, level);
    onSelect(level);
  };
  const list = createLevelList(
    state,
    selectLevel,
    buttons,
    markers,
    clickHandlers,
  );
  roving = createLevelRoving(state, buttons, selectLevel);
  nav.append(title, list);
  return createLevelNavigationApi(
    nav,
    state,
    buttons,
    markers,
    clickHandlers,
    roving,
  );
}

function createLevelList(
  state: AttemptState,
  selectLevel: (level: number) => void,
  buttons: HTMLButtonElement[],
  markers: HTMLElement[],
  clickHandlers: Array<() => void>,
): HTMLOListElement {
  const list = element("ol", "level-list");
  state.bootstrap.levels.forEach((item) => {
    const listItem = element("li");
    const levelButton = button(`${item.level}. ${item.label}`, "level-button");
    levelButton.setAttribute("aria-label", `Level ${item.level}: ${item.label}`);
    levelButton.setAttribute(
      "aria-current",
      item.level === state.selectedLevel ? "step" : "false",
    );
    const marker = element("span", "level-status");
    marker.id = `level-${item.level}-status`;
    levelButton.setAttribute("aria-describedby", marker.id);
    renderLevelStatus(state, item.level, marker);
    markers.push(marker);
    levelButton.dataset.enabled = "true";
    const onClick = (): void => selectLevel(item.level);
    levelButton.addEventListener("click", onClick);
    clickHandlers.push(onClick);
    buttons.push(levelButton);
    listItem.append(levelButton, marker);
    list.append(listItem);
  });
  return list;
}

function createLevelRoving(
  state: AttemptState,
  buttons: HTMLButtonElement[],
  selectLevel: (level: number) => void,
): ReturnType<typeof createRovingNavigation> {
  return createRovingNavigation(buttons, {
    activate: (index) => {
      const item = state.bootstrap.levels[index];
      if (!item) return;
      selectLevel(item.level);
    },
  });
}

function createLevelNavigationApi(
  nav: HTMLElement,
  state: AttemptState,
  buttons: HTMLButtonElement[],
  markers: HTMLElement[],
  clickHandlers: Array<() => void>,
  roving: ReturnType<typeof createRovingNavigation>,
): LevelNavigation {
  return {
    element: nav,
    buttons,
    refreshStatus: () => {
      state.bootstrap.levels.forEach((item, index) => {
        const marker = markers[index];
        if (marker) renderLevelStatus(state, item.level, marker);
      });
    },
    focusLevel: (level) => {
      const index = state.bootstrap.levels.findIndex((item) => item.level === level);
      if (index < 0) return;
      state.selectedLevel = level;
      updateLevelSelection(state, buttons, roving, level);
      roving.setActive(index, true);
    },
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

function renderLevelStatus(
  state: AttemptState,
  level: number,
  marker: HTMLElement,
): void {
  const score = state.session.score;
  const result = score?.levels.find((item) => item.level === level);
  const reached = level === 1 || Boolean(result) || Boolean(
    score && level <= Math.max(1, score.highest_contiguous_level),
  );
  const completed = Boolean(result);
  const practiceTest = result?.outcome || "not run";
  marker.textContent = [
    reached ? "Reached" : "Not reached",
    ...(completed ? ["Completed"] : []),
    `Practice test: ${practiceTest}`,
  ].join(" · ");
  marker.dataset.reached = String(reached);
  marker.dataset.completed = String(completed);
  marker.dataset.practiceTest = practiceTest;
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
  body.textContent = `Loading Level ${state.selectedLevel} description…`;
  const controls = createPromptTabs(
    state,
    body,
    tabs,
    tabLabels,
    onTabSelect,
  );
  const setHistory = (
    history: SourceHistory,
    onRestore: (snapshotId: string, opener: HTMLElement) => void,
  ): void =>
    renderHistory(body, history, onRestore, state.session.status !== "active");
  body.setAttribute("aria-labelledby", `prompt-tab-${state.selectedTab}`);
  pane.append(title, tabs, body);
  return {
    element: pane,
    tabButtons: controls.tabButtons,
    body,
    setHistory,
    dispose: () => {
      controls.roving.dispose();
      removeClickHandlers(controls.tabButtons, controls.clickHandlers);
    },
  };
}

function renderHistory(
  body: HTMLElement,
  history: SourceHistory,
  onRestore: (snapshotId: string, opener: HTMLElement) => void,
  locked: boolean,
): void {
  body.replaceChildren();
  body.className = "prompt-copy history-list";
  if (history.snapshots.length === 0) {
    body.textContent = "No saved candidate versions yet.";
    return;
  }
  history.snapshots.forEach((snapshot) => {
    const item = document.createElement("article");
    item.className = "history-item";
    const heading = document.createElement("strong");
    heading.textContent = `${snapshot.operation} · ${snapshot.created_at}`;
    const preview = document.createElement("pre");
    preview.textContent = snapshot.content_preview.slice(0, 512);
    const restore = button("Restore this version", "secondary");
    restore.disabled = locked;
    restore.addEventListener("click", () => onRestore(snapshot.snapshot_id, restore));
    item.append(heading, preview, restore);
    body.append(item);
  });
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
  const selectTab = (selected: PromptTab): void => {
    state.selectedTab = selected;
    updateTabSelection(tabLabels, tabButtons, body, roving, selected);
  };
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
