import { expect, test } from "@playwright/test";
import {
  installOfflineRequestPolicy,
  startFixtureServer,
} from "./browser_harness.mjs";

test.describe.configure({ mode: "serial" });

let harness;
let requestPolicy;

test.beforeEach(async ({ page }) => {
  harness = await startFixtureServer();
  requestPolicy = installOfflineRequestPolicy(page, harness);
});

test.afterEach(async () => {
  const currentHarness = harness;
  const currentPolicy = requestPolicy;
  harness = undefined;
  requestPolicy = undefined;
  try {
    if (currentPolicy) await currentPolicy.assert();
  } finally {
    if (currentHarness) await currentHarness.close();
  }
});

test("renders the desktop assessment shell with semantic regions", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.goto(`${harness.origin}/#token=${harness.token}`);
  await confirmStart(page);
  await expect(page.getByRole("navigation", { name: "Assessment levels" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Level 1: Level 1" })).toHaveAttribute(
    "aria-current",
    "step",
  );
  await expect(page.getByTestId("prompt-pane")).toBeVisible();
  await expect(page.getByTestId("editor-pane")).toBeVisible();
  await expect(page.getByTestId("output-drawer")).toBeVisible();
  await expect(page.getByRole("tab", { name: "Description" })).toBeVisible();
  await expect(page.getByRole("tab", { name: "History" })).toBeVisible();
  await expect(page.getByRole("tab", { name: "Rules" })).toBeVisible();
  await expect(page.getByRole("tab", { name: "Info" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Run Tests" })).toBeEnabled();
  await expect(page.getByRole("button", { name: "Skip" })).toBeEnabled();
  await expect(page.getByRole("button", { name: "Reset" })).toBeEnabled();
  await expect(page.getByRole("button", { name: "Submit" })).toBeEnabled();
  await expect(page.getByRole("timer", { name: "Time remaining" })).toBeVisible();
  await expect(page.getByText("Saved snapshot")).toBeVisible();
  await expect(page.getByText("Connected")).toBeVisible();
  await expect(page.getByRole("heading", { name: "Problem" })).toBeVisible();
  await expect(page.getByTestId("output-drawer")).toContainText(
    "Run local practice checks to see bounded per-level results.",
  );
  await expect(page.getByTestId("output-drawer")).not.toContainText("Final result");
});

test("labels an active score as a Practice result", async ({ page }) => {
  await page.route("**/api/attempts", async (route) => {
    const response = await route.fetch();
    const body = await response.json();
    body.data.session.score = {
      levels: [1, 2, 3, 4].map((level) => ({ level, outcome: "passed" })),
      passed_levels: 4,
      highest_contiguous_level: 4,
    };
    await route.fulfill({ response, body: JSON.stringify(body) });
  });
  await page.goto(`${harness.origin}/#token=${harness.token}`);
  await confirmStart(page);
  await expect(page.getByTestId("output-drawer")).toContainText(
    "Practice result · Passed levels: 4 of 4.",
  );
  await expect(page.getByTestId("output-drawer")).not.toContainText("Final result");
});

test("keeps confirmation focus contained and restores the opener by keyboard", async ({
  page,
}) => {
  await page.goto(`${harness.origin}/#token=${harness.token}`);
  const start = page.getByRole("button", { name: "Start practice" });
  await start.focus();
  await page.keyboard.press("Enter");
  const dialog = page.getByRole("dialog");
  await expect(dialog).toBeVisible();
  await expect(page.getByRole("button", { name: "Confirm and start" })).toBeFocused();
  await page.keyboard.press("Tab");
  await expect(page.getByRole("button", { name: "Cancel" })).toBeFocused();
  await page.keyboard.press("Tab");
  await expect(page.getByRole("button", { name: "Confirm and start" })).toBeFocused();
  await page.keyboard.press("Shift+Tab");
  await expect(page.getByRole("button", { name: "Cancel" })).toBeFocused();
  await page.keyboard.press("Shift+Tab");
  await expect(page.getByRole("button", { name: "Confirm and start" })).toBeFocused();
  await page.keyboard.press("Escape");
  await expect(dialog).toBeHidden();
  await expect(start).toBeFocused();
  await start.press("Enter");
  await page.getByRole("button", { name: "Cancel" }).click();
  await expect(dialog).toBeHidden();
  await expect(start).toBeFocused();
});

test("does not restore focus to a removed dialog opener", async ({ page }) => {
  await page.goto(`${harness.origin}/#token=${harness.token}`);
  const start = page.getByRole("button", { name: "Start practice" });
  await start.click();
  await page.evaluate(() => {
    document.querySelector("form .primary")?.remove();
  });
  await page.keyboard.press("Escape");
  await expect(page.getByRole("dialog")).toBeHidden();
  expect(await page.evaluate(() => document.activeElement?.isConnected)).toBe(true);
});

test("roves levels and problem tabs with arrows and Home/End", async ({ page }) => {
  await page.goto(`${harness.origin}/#token=${harness.token}`);
  await keyboardStart(page);

  const levelOne = page.getByRole("button", { name: "Level 1: Level 1" });
  const levelTwo = page.getByRole("button", { name: "Level 2: Level 2" });
  const levelFour = page.getByRole("button", { name: "Level 4: Level 4" });
  await levelOne.focus();
  await page.keyboard.press("ArrowRight");
  await expect(levelTwo).toBeFocused();
  await expect(levelTwo).toHaveAttribute("aria-current", "step");
  await expectTabIndices(
    page.getByRole("navigation", { name: "Assessment levels" }).getByRole("button"),
    [-1, 0, -1, -1],
  );
  await page.keyboard.press("End");
  await expect(levelFour).toBeFocused();
  await expectTabIndices(
    page.getByRole("navigation", { name: "Assessment levels" }).getByRole("button"),
    [-1, -1, -1, 0],
  );
  await page.keyboard.press("Home");
  await expect(levelOne).toBeFocused();
  await expectTabIndices(
    page.getByRole("navigation", { name: "Assessment levels" }).getByRole("button"),
    [0, -1, -1, -1],
  );
  await page.keyboard.press("ArrowLeft");
  await expect(levelFour).toBeFocused();
  await expectTabIndices(
    page.getByRole("navigation", { name: "Assessment levels" }).getByRole("button"),
    [-1, -1, -1, 0],
  );

  const description = page.getByRole("tab", { name: "Description" });
  const history = page.getByRole("tab", { name: "History" });
  const info = page.getByRole("tab", { name: "Info" });
  await description.focus();
  await expectTabIndices(page.getByRole("tab"), [0, -1, -1, -1]);
  await page.keyboard.press("ArrowRight");
  await expect(history).toBeFocused();
  await expect(history).toHaveAttribute("aria-selected", "true");
  await expectTabIndices(page.getByRole("tab"), [-1, 0, -1, -1]);
  await page.keyboard.press("End");
  await expect(info).toBeFocused();
  await expectTabIndices(page.getByRole("tab"), [-1, -1, -1, 0]);
  await expect(info).toHaveAttribute("aria-controls", "prompt-content");
  await page.keyboard.press("Home");
  await expect(description).toBeFocused();
  await expect(description).toHaveAttribute("aria-selected", "true");
  await page.keyboard.press("ArrowLeft");
  await expect(info).toBeFocused();
  await expectTabIndices(page.getByRole("tab"), [-1, -1, -1, 0]);
});

test("collapses the shell into a narrow, scrollable layout", async ({ page }) => {
  await page.setViewportSize({ width: 760, height: 900 });
  await page.goto(`${harness.origin}/#token=${harness.token}`);
  await confirmStart(page);

  const layout = await page.getByTestId("editor-pane").evaluate((editor) => {
    const grid = editor.parentElement;
    const actionBar = document.querySelector(".action-bar");
    return {
      columns: getComputedStyle(grid).gridTemplateColumns,
      editorWidth: editor.getBoundingClientRect().width,
      viewport: window.innerWidth,
      actionPosition: getComputedStyle(actionBar).position,
    };
  });
  expect(layout.columns.split(" ").length).toBe(1);
  expect(layout.editorWidth).toBeGreaterThan(layout.viewport * 0.8);
  expect(layout.actionPosition).toBe("sticky");
  await expect(page.getByRole("button", { name: "Submit" })).toBeVisible();
});

test("keeps keyboard focus reachable at a narrow viewport", async ({ page }) => {
  await page.setViewportSize({ width: 760, height: 900 });
  await page.goto(`${harness.origin}/#token=${harness.token}`);
  await keyboardStart(page);
  const level = page.getByRole("button", { name: "Level 1: Level 1" });
  await level.focus();
  await page.keyboard.press("End");
  const box = await page.evaluate(() => {
    const active = document.activeElement.getBoundingClientRect();
    return {
      left: active.left,
      right: active.right,
      width: window.innerWidth,
    };
  });
  expect(box.left).toBeGreaterThanOrEqual(0);
  expect(box.right).toBeLessThanOrEqual(box.width);
});

test("keeps the narrow viewport Tab order on the active controls", async ({ page }) => {
  await page.setViewportSize({ width: 760, height: 900 });
  await page.goto(`${harness.origin}/#token=${harness.token}`);
  await keyboardStart(page);
  await page.keyboard.press("Tab");
  await expect(page.getByRole("tab", { name: "Description" })).toBeFocused();
  await page.keyboard.press("Tab");
  await expect(page.locator("#prompt-content")).toBeFocused();
});

async function confirmStart(page) {
  await expect(page.locator(".entry")).toBeVisible();
  await page.getByRole("button", { name: "Start practice" }).click();
  await page.getByRole("button", { name: "Confirm and start" }).click();
  await expect(page.getByTestId("editor-pane")).toBeVisible();
  await expect(page.locator(".status")).toHaveText(/Python editor ready/);
}

async function expectTabIndices(locator, expected) {
  await expect.poll(() => locator.evaluateAll((items) =>
    items.map((item) => item.tabIndex),
  )).toEqual(expected);
}

async function keyboardStart(page) {
  await expect(page.locator(".entry")).toBeVisible();
  const start = page.getByRole("button", { name: "Start practice" });
  await start.focus();
  await page.keyboard.press("Enter");
  await expect(page.getByRole("dialog")).toBeVisible();
  await page.keyboard.press("Enter");
  await expect(page.getByTestId("editor-pane")).toBeVisible();
  await expect(page.locator(".status")).toHaveText(/Python editor ready/);
  await expect(
    page.getByRole("button", { name: "Level 1: Level 1" }),
  ).toBeFocused();
}
