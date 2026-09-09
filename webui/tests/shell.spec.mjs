import { expect, test } from "@playwright/test";
import {
  installOfflineRequestPolicy,
  startFixtureServer,
} from "./browser_harness.mjs";
import { timeResponse, timerSeconds } from "./shell_test_support.mjs";
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
  await expect(page.getByRole("button", { name: "Run Tests" })).toBeDisabled();
  await expect(page.getByRole("button", { name: "Skip" })).toBeDisabled();
  await expect(page.getByRole("button", { name: "Reset" })).toBeDisabled();
  await expect(page.getByRole("button", { name: "Submit" })).toBeDisabled();
  await expect(page.getByRole("timer", { name: "Time remaining" })).toBeVisible();
  await expect(page.getByText("Saved snapshot")).toBeVisible();
  await expect(page.getByText("Connected")).toBeVisible();
  await expect(page.getByRole("heading", { name: "Problem" })).toBeVisible();
  await expect(page.getByTestId("output-drawer")).toContainText(
    "Test output will appear here after test wiring is enabled.",
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
  await expectTabIndices(page.getByRole("navigation", { name: "Assessment levels" }).getByRole("button"), [-1, 0, -1, -1]);
  await page.keyboard.press("End");
  await expect(levelFour).toBeFocused();
  await expectTabIndices(page.getByRole("navigation", { name: "Assessment levels" }).getByRole("button"), [-1, -1, -1, 0]);
  await page.keyboard.press("Home");
  await expect(levelOne).toBeFocused();
  await expectTabIndices(page.getByRole("navigation", { name: "Assessment levels" }).getByRole("button"), [0, -1, -1, -1]);
  await page.keyboard.press("ArrowLeft");
  await expect(levelFour).toBeFocused();
  await expectTabIndices(page.getByRole("navigation", { name: "Assessment levels" }).getByRole("button"), [-1, -1, -1, 0]);

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

test("updates the countdown from monotonic elapsed time without a lifecycle write", async ({
  page,
}) => {
  let mutationRequests = 0;
  page.on("request", (request) => {
    if (request.method() !== "GET") mutationRequests += 1;
  });
  await page.goto(`${harness.origin}/#token=${harness.token}`);
  await confirmStart(page);
  const timer = page.getByRole("timer", { name: "Time remaining" });
  const initial = await timer.innerText();
  await expect.poll(() => timer.innerText(), { timeout: 4000 }).not.toBe(initial);
  expect(mutationRequests).toBe(1);
});

test("guards delayed prompt responses across rapid level and tab changes", async ({
  page,
}) => {
  requestPolicy.delay("/api/prompts/2", 1000);
  await page.goto(`${harness.origin}/#token=${harness.token}`);
  await confirmStart(page);
  await page.getByRole("button", { name: "Level 2: Level 2" }).click();
  await page.getByRole("button", { name: "Level 3: Level 3" }).click();
  await page.getByRole("tab", { name: "History" }).click();
  await expect(page.locator(".prompt-copy")).toHaveText(
    "Source history will be available after history wiring is enabled.",
  );
  await page.getByRole("tab", { name: "Description" }).click();
  await expect(page.locator(".prompt-copy")).toContainText("level3.md");
  await page.waitForTimeout(1100);
  await expect(page.locator(".prompt-copy")).toContainText("level3.md");
});

test("ignores an old attempt prompt after terminal cleanup replaces its shell", async ({
  page,
}) => {
  await page.goto(`${harness.origin}/#token=${harness.token}`);
  await page.clock.install();
  const started = await startWithResponse(page);
  const session = started.data.session;
  const attemptId = session.attempt_id;
  requestPolicy.delay(`/api/prompts/2?attempt_id=${attemptId}`, 1000);
  await page.getByRole("button", { name: "Level 2: Level 2" }).click();
  requestPolicy.intercept(`/api/time?attempt_id=${attemptId}`, timeResponse({
    ...session,
    status: "expired",
  }, started.data.time));
  await page.clock.fastForward("00:15");
  await expect(page.getByText("Expired", { exact: true })).toBeVisible();
  await page.waitForTimeout(1100);
  await expect(page.locator(".prompt-copy")).toHaveText(
    "Loading Level 1 description…",
  );
});

test("removes listeners from controls in a rerendered shell", async ({ page }) => {
  await page.goto(`${harness.origin}/#token=${harness.token}`);
  await page.clock.install();
  const started = await startWithResponse(page);
  await page.evaluate(() => {
    window.__oldLevelButton = document.querySelectorAll(".level-button")[1];
  });
  let stalePromptRequests = 0;
  page.on("request", (request) => {
    if (new URL(request.url()).pathname === "/api/prompts/2") stalePromptRequests += 1;
  });
  const attemptId = started.data.session.attempt_id;
  requestPolicy.intercept(
    `/api/time?attempt_id=${attemptId}`,
    timeResponse({ ...started.data.session, status: "expired" }, started.data.time),
  );
  await page.clock.fastForward("00:15");
  await page.evaluate(() => window.__oldLevelButton.click());
  await page.waitForTimeout(100);
  expect(stalePromptRequests).toBe(0);
});
test("keeps the countdown monotonic across a successful stale resync", async ({
  page,
}) => {
  const timeRequests = [];
  page.on("request", (request) => {
    if (new URL(request.url()).pathname === "/api/time") timeRequests.push(request);
  });
  await page.goto(`${harness.origin}/#token=${harness.token}`);
  await page.clock.install();
  const started = await startWithResponse(page);
  const initial = timerSeconds(await page.getByRole("timer", {
    name: "Time remaining",
  }).innerText());
  const attemptId = started.data.session.attempt_id;
  requestPolicy.intercept(`/api/time?attempt_id=${attemptId}`, timeResponse(
    started.data.session,
    started.data.time,
  ));
  requestPolicy.delay(`/api/time?attempt_id=${attemptId}`, 1000);
  const resyncResponse = page.waitForResponse(
    (response) => new URL(response.url()).pathname === "/api/time",
  );
  await page.clock.fastForward("00:15");
  await page.clock.fastForward("00:02");
  await resyncResponse;
  const afterResync = timerSeconds(await page.getByRole("timer", {
    name: "Time remaining",
  }).innerText());
  await page.clock.fastForward("00:01");
  const afterNextTick = timerSeconds(await page.getByRole("timer", {
    name: "Time remaining",
  }).innerText());
  expect(timeRequests).toHaveLength(1);
  expect(afterResync).toBeLessThan(initial);
  expect(afterNextTick).toBeLessThan(afterResync);
});
test("shows reconnecting after a failed countdown resync", async ({ page }) => {
  const timeRequests = [];
  page.on("request", (request) => {
    if (new URL(request.url()).pathname === "/api/time") timeRequests.push(request);
  });
  await page.goto(`${harness.origin}/#token=${harness.token}`);
  await page.clock.install();
  const started = await startWithResponse(page);
  requestPolicy.intercept(`/api/time?attempt_id=${started.data.session.attempt_id}`, {
    status: 503,
    contentType: "application/json",
    body: JSON.stringify({
      schema_version: "web/v1",
      ok: false,
      error: { code: "reconnect", message: "delayed test failure" },
    }),
  });
  await page.clock.fastForward("00:15");
  await expect(page.getByText("Reconnecting…", { exact: true })).toBeVisible();
  expect(timeRequests).toHaveLength(1);
});
test("coalesces duplicate live announcements and disposes pending frames", async ({
  page,
}) => {
  await page.clock.install();
  await page.goto(`${harness.origin}/#token=${harness.token}`);
  const started = await startWithResponse(page);
  await page.evaluate(() => {
    const frames = new Map();
    let nextId = 0;
    let requested = 0;
    let cancelled = 0;
    window.requestAnimationFrame = (callback) => {
      const id = ++nextId;
      requested += 1;
      frames.set(id, callback);
      return id;
    };
    window.cancelAnimationFrame = (id) => {
      if (frames.delete(id)) cancelled += 1;
    };
    window.__liveTest = {
      counts: () => ({ requested, cancelled }),
      flush: () => {
        const callbacks = [...frames.values()];
        frames.clear();
        callbacks.forEach((callback) => callback(0));
      },
    };
  });
  await page.locator(".editor").click();
  await page.keyboard.type("# live announcement");
  await expect.poll(() => page.evaluate(() => window.__liveTest.counts().requested))
    .toBeGreaterThan(0);
  const first = await page.evaluate(() => window.__liveTest.counts().requested);
  await page.keyboard.type(" duplicate");
  expect(await page.evaluate(() => window.__liveTest.counts().requested)).toBe(first);
  const attemptId = started.data.session.attempt_id;
  requestPolicy.intercept(
    `/api/time?attempt_id=${attemptId}`,
    timeResponse({ ...started.data.session, status: "expired" }, started.data.time),
  );
  await page.clock.fastForward("00:15");
  expect(await page.evaluate(() => window.__liveTest.counts().cancelled))
    .toBeGreaterThan(0);
  await page.evaluate(() => window.__liveTest.flush());
  await expect(page.locator(".sr-status")).toHaveText(
    "Attempt expired. Source is unavailable. Results remain available in read-only mode.",
  );
});

test("accepts expiry as terminal and stops countdown polling", async ({ page }) => {
  const timeRequests = [];
  page.on("request", (request) => {
    if (new URL(request.url()).pathname === "/api/time") timeRequests.push(request);
  });
  await page.goto(`${harness.origin}/#token=${harness.token}`);
  await page.clock.install();
  const started = await startWithResponse(page);
  const attemptId = started.data.session.attempt_id;
  requestPolicy.intercept(`/api/time?attempt_id=${attemptId}`, timeResponse({
    ...started.data.session,
    status: "expired",
  }, started.data.time));

  await page.clock.fastForward("00:15");
  await expect(page.getByText("Expired", { exact: true })).toBeVisible();
  await expect(page.locator(".sr-status")).toHaveText(
    "Attempt expired. Source is unavailable. Results remain available in read-only mode.",
  );
  expect(timeRequests).toHaveLength(1);
  await page.clock.fastForward("01:00");
  expect(timeRequests).toHaveLength(1);
});

test("renders a submitted snapshot as a final state without loading source", async ({ page }) => {
  await page.goto(`${harness.origin}/#token=${harness.token}`);
  await page.getByRole("button", { name: "Start practice" }).click();
  const responsePromise = page.waitForResponse(
    (item) =>
      new URL(item.url()).pathname === "/api/attempts" &&
      item.request().method() === "POST",
  );
  await page.getByRole("button", { name: "Confirm and start" }).click();
  const response = await responsePromise;
  const started = await response.json();
  const session = started.data.session;
  const finalSession = {
    ...session,
    status: "submitted",
    score: {
      levels: [1, 2, 3, 4].map((level) => ({ level, outcome: "passed" })),
      passed_levels: 4,
      highest_contiguous_level: 4,
    },
    submitted_at: session.started_at,
  };
  let sourceRequests = 0;
  page.on("request", (request) => {
    if (new URL(request.url()).pathname === "/api/source") sourceRequests += 1;
  });
  await page.reload();
  requestPolicy.intercept("/api/time", {
    status: 200,
    contentType: "application/json",
    body: JSON.stringify({
      schema_version: "web/v1",
      ok: true,
      data: {
        session: finalSession,
        observed_at: session.started_at,
        elapsed_seconds: 1,
        remaining_seconds: 0,
      },
    }),
  });
  await page.getByRole("button", { name: "Reconnect to active session" }).click();
  await expect(page.getByText("Submitted", { exact: true })).toBeVisible();
  await expect(page.getByText("Final result · Passed levels: 4 of 4.")).toBeVisible();
  await expect(page.locator(".sr-status")).toHaveText(
    "Final result announced. Passed levels: 4 of 4. Source is unavailable. Results are final and read-only.",
  );
  for (const name of ["Save changes", "Run Tests", "Reset", "Submit"]) {
    await expect(page.getByRole("button", { name })).toBeDisabled();
  }
  await expect(page.getByRole("button", { name: "Level 1: Level 1" })).toBeEnabled();
  expect(sourceRequests).toBe(0);
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

async function startWithResponse(page) {
  const responsePromise = page.waitForResponse(
    (item) =>
      new URL(item.url()).pathname === "/api/attempts" &&
      item.request().method() === "POST",
  );
  await confirmStart(page);
  return (await responsePromise).json();
}
