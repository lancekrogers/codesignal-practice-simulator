import { expect, test } from "@playwright/test";
import {
  installOfflineRequestPolicy,
  startFixtureServer,
} from "./browser_harness.mjs";

let harness;
let requestPolicy;

test.beforeEach(async ({ page }) => {
  harness = await startFixtureServer();
  requestPolicy = await installOfflineRequestPolicy(page, harness);
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

test("covers four prompts, tabs, keyboard roving, and source preservation", async ({
  page,
}) => {
  const promptRequests = trackPromptRequests(page);
  await startAttempt(page);
  await expectPrompt(page, 1);
  await appendSource(page, "# navigation-buffer-marker");
  await expect(
    page.locator(".header-meta").getByText("Unsaved local edits", { exact: true }),
  ).toBeVisible();
  await expect(
    page.locator(".header-meta").getByText("Saved snapshot", { exact: true }),
  ).toBeVisible();
  const navigationMutations = trackSourceMutations(page);

  for (const level of [2, 3, 4]) {
    await page.getByRole("button", { name: `Level ${level}: Level ${level}` }).click();
    await expectPrompt(page, level);
  }
  expect(new Set(promptRequests.map((request) => request.pathname)).size).toBe(4);
  await page.getByRole("button", { name: "Level 2: Level 2" }).click();
  await expectPrompt(page, 2);
  expect(promptRequests.filter((request) => request.pathname === "/api/prompts/2"))
    .toHaveLength(1);
  await expect(page.locator(".view-lines")).toContainText("# navigation-buffer-marker");

  await verifyTabRoving(page);
  await page.getByRole("tab", { name: "Description" }).click();
  await page.getByRole("button", { name: "Level 1: Level 1" }).click();
  await expect(page.getByRole("button", { name: "Previous" })).toBeDisabled();
  await expect(page.getByRole("button", { name: "Skip" })).toBeEnabled();
  await expect(page.getByRole("button", { name: "Next" })).toBeEnabled();
  await page.getByRole("button", { name: "Skip" }).click();
  await expect(page.getByRole("button", { name: "Level 2: Level 2" }))
    .toHaveAttribute("aria-current", "step");
  await page.getByRole("button", { name: "Next" }).click();
  await page.getByRole("button", { name: "Next" }).click();
  await expect(page.getByRole("button", { name: "Level 4: Level 4" }))
    .toHaveAttribute("aria-current", "step");
  await expect(page.getByRole("button", { name: "Skip" })).toBeDisabled();
  await expect(page.getByRole("button", { name: "Next" })).toBeDisabled();
  await page.getByRole("button", { name: "Previous" }).click();
  await expect(page.getByRole("button", { name: "Level 3: Level 3" }))
    .toHaveAttribute("aria-current", "step");
  await expect(page.locator(".view-lines")).toContainText("# navigation-buffer-marker");
  expect(navigationMutations).toHaveLength(0);
});

test("renders bootstrap rules and normalized session info safely", async ({
  page,
}) => {
  await page.route("**/api/bootstrap", async (route) => {
    const response = await route.fetch();
    const body = await response.json();
    body.data.assessment.display_name = "Validated Local Practice";
    body.data.rules = [
      "Use the saved candidate source for local checks.",
      "The local timer remains authoritative.",
    ];
    await route.fulfill({ response, body: JSON.stringify(body) });
  });
  await startAttempt(page);

  await page.getByRole("tab", { name: "Rules" }).click();
  await expect(page.locator(".prompt-copy")).toHaveText(
    "Use the saved candidate source for local checks.\n\nThe local timer remains authoritative.",
  );
  await assertPromptIsSafe(page);

  await page.getByRole("tab", { name: "Info" }).click();
  await expect(page.locator(".prompt-copy")).toContainText(
    "Validated Local Practice",
  );
  await expect(page.locator(".prompt-copy")).toContainText("Mode: full");
  await expect(page.locator(".prompt-copy")).toContainText("Selected level: 1 of 4");
  await expect(page.locator(".prompt-copy")).toContainText("Level count: 4");
  await expect(page.locator(".prompt-copy")).toContainText("local practice");
  await assertPromptIsSafe(page);

  await page.getByRole("button", { name: "Level 3: Level 3" }).click();
  await expect(page.locator(".prompt-copy")).toContainText("Selected level: 3 of 4");
});

test("restores each selected tab label and uses history-specific status text", async ({
  page,
}) => {
  await startAttempt(page);
  const attemptId = await page.locator("main").getAttribute("data-attempt-id");
  const panel = page.locator('[role="tabpanel"]');

  for (const tab of ["history", "rules", "info"]) {
    await reloadWithView(page, attemptId, 1, tab);
    await expect(page.getByRole("tab", {
      name: tab[0].toUpperCase() + tab.slice(1),
    })).toHaveAttribute("aria-selected", "true");
    await expect(panel).toHaveAttribute("aria-labelledby", `prompt-tab-${tab}`);
  }

  const historyHeld = requestPolicy.hold("/api/source/history");
  await page.getByRole("tab", { name: "Description" }).click();
  await page.getByRole("tab", { name: "History" }).click();
  await expect(panel).toHaveText("Loading candidate source history…");
  await historyHeld;
  requestPolicy.release("/api/source/history");
  await expect(panel).toHaveText("No saved candidate versions yet.");

  requestPolicy.intercept("/api/source/history", {
    status: 503,
    contentType: "application/json",
    body: JSON.stringify({
      schema_version: "web/v1",
      ok: false,
      error: { code: "temporary_failure", message: "history unavailable" },
    }),
  });
  requestPolicy.expectHttpError({
    method: "GET",
    path: "/api/source/history",
    status: 503,
  });
  await page.getByRole("tab", { name: "Description" }).click();
  await page.getByRole("tab", { name: "History" }).click();
  await expect(panel).toHaveText(
    "Candidate source history unavailable. The session remains unchanged.",
  );
  await assertPromptIsSafe(page);
});

test("reconstructs validated URL view state without lifecycle mutation", async ({
  page,
}) => {
  await startAttempt(page);
  const attemptId = await page.locator("main").getAttribute("data-attempt-id");
  await page.getByRole("button", { name: "Level 3: Level 3" }).click();
  await page.getByRole("tab", { name: "Info" }).click();
  await expect(page.locator(".prompt-copy")).toContainText("local practice");
  const mutations = [];
  page.on("request", (request) => {
    if (["POST", "PUT"].includes(request.method())) mutations.push(request);
  });
  await page.reload();
  await page.getByRole("button", { name: "Reconnect to active session" }).click();
  await expect(page.getByRole("button", { name: "Level 3: Level 3" }))
    .toHaveAttribute("aria-current", "step");
  await expect(page.getByRole("tab", { name: "Info" }))
    .toHaveAttribute("aria-selected", "true");
  expect(mutations).toHaveLength(0);
  const view = new URL(page.url());
  expect(view.pathname).toBe(`/attempt/${attemptId}`);
  expect(view.search).toBe("");
  const fragment = new URLSearchParams(view.hash.slice(1));
  expect(fragment.get("attempt_id")).toBe(attemptId);
  expect(fragment.get("level")).toBe("3");
  expect(fragment.get("tab")).toBe("info");

  const promptPaths = [];
  page.on("request", (request) => {
    const path = new URL(request.url()).pathname;
    if (path.startsWith("/api/prompts/")) promptPaths.push(path);
  });
  await reloadWithDefaultView(page, attemptId, 9, "rules");
  expect(promptPaths).not.toContain("/api/prompts/9");
  await reloadWithDefaultView(
    page,
    "00000000-0000-4000-8000-000000000000",
    2,
    "rules",
  );
});

test("renders reached, completed, and practice-test markers from score data", async ({
  page,
}) => {
  await page.route("**/api/attempts", async (route) => {
    const response = await route.fetch();
    const body = await response.json();
    body.data.session.score = {
      levels: [
        { level: 1, outcome: "passed" },
        { level: 2, outcome: "failed" },
        { level: 3, outcome: "error" },
        { level: 4, outcome: "failed" },
      ],
      passed_levels: 1,
      highest_contiguous_level: 1,
    };
    await route.fulfill({ response, body: JSON.stringify(body) });
  });
  await startAttempt(page);
  const status = (level) => page.locator(`#level-${level}-status`);
  await expect(status(1)).toHaveText(
    "Reached · Completed · Practice test: passed",
  );
  await expect(status(2)).toHaveText(
    "Reached · Completed · Practice test: failed",
  );
  await expect(status(3)).toHaveText(
    "Reached · Completed · Practice test: error",
  );
  await expect(status(4)).toHaveText(
    "Reached · Completed · Practice test: failed",
  );
  const mainText = await page.getByRole("main").innerText();
  expect(mainText).not.toMatch(/official|hidden/iu);
});

test("guards prompt races and disposes the prompt cache on refresh", async ({
  page,
}) => {
  requestPolicy.expectFailedRequest({
    method: "GET",
    path: "/api/prompts/2",
    count: 1,
  });
  const promptHeld = requestPolicy.hold("/api/prompts/2");
  const promptRequests = trackPromptRequests(page);
  await startAttempt(page);
  await page.getByRole("button", { name: "Level 2: Level 2" }).click();
  await page.getByRole("button", { name: "Level 3: Level 3" }).click();
  await expectPrompt(page, 3);
  await promptHeld;
  requestPolicy.release("/api/prompts/2");
  await expectPrompt(page, 3);
  await page.reload();
  await page.getByRole("button", { name: "Reconnect to active session" }).click();
  await page.getByRole("button", { name: "Level 2: Level 2" }).click();
  await expectPrompt(page, 2);
  expect(promptRequests.filter((request) => request.pathname === "/api/prompts/2"))
    .toHaveLength(2);
});

test("can cancel leaving, return to start, and reconnect without resetting the attempt", async ({ page }) => {
  await startAttempt(page);
  const attemptId = await page.locator("main").getAttribute("data-attempt-id");
  const deadline = await page.locator(".server-deadline").innerText();
  await appendSource(page, "# saved-before-leaving");
  await expect(page.locator(".assessment-header .header-status").nth(1).locator("strong"))
    .toHaveText("Saved snapshot");
  await page.getByRole("button", { name: "Level 3: Level 3" }).click();
  await expectPrompt(page, 3);
  const mutations = [];
  page.on("request", (request) => {
    if (["POST", "PUT"].includes(request.method())) mutations.push(request.method());
  });
  await page.getByRole("button", { name: "Back to library" }).click();
  const dialog = page.getByRole("dialog", { name: "Leave assessment?" });
  await expect(dialog).toContainText("The timer keeps running");
  await expect(dialog).toContainText("unsaved local edits will be lost");
  await dialog.getByRole("button", { name: "Cancel" }).click();
  await expect(page.getByRole("button", { name: "Back to library" })).toBeFocused();
  await expect(page.locator(".view-lines")).toContainText("# saved-before-leaving");
  await page.getByRole("button", { name: "Back to library" }).click();
  await dialog.getByRole("button", { name: "Leave assessment", exact: true }).click();
  await page.getByRole("button", { name: "Reconnect to active session" }).click();
  await expect(page.locator("main")).toHaveAttribute("data-attempt-id", attemptId);
  await expect(page.locator(".server-deadline")).toHaveText(deadline);
  await expect(page.locator(".view-lines")).toContainText("# saved-before-leaving");
  await expect(page.getByRole("button", { name: "Level 3: Level 3" }))
    .toHaveAttribute("aria-current", "step");
  expect(mutations).toHaveLength(0);
});

test("cancel preserves a failed-save buffer and leaving requires explicit discard confirmation", async ({ page }) => {
  await startAttempt(page);
  requestPolicy.intercept("/api/source", {
    status: 503,
    contentType: "application/json",
    body: JSON.stringify({
      schema_version: "web/v1", ok: false,
      error: { code: "temporary_failure", message: "temporary save failure" },
    }),
  });
  requestPolicy.expectHttpError({ method: "PUT", path: "/api/source", status: 503 });
  await appendSource(page, "# unsaved-exit-marker");
  await expect(page.locator(".assessment-header .header-status").nth(1).locator("strong"))
    .toHaveText("Save failed — retry");
  await page.getByRole("button", { name: "Back to library" }).click();
  const dialog = page.getByRole("dialog", { name: "Leave assessment?" });
  await expect(dialog).toContainText("unsaved local edits will be lost");
  await dialog.getByRole("button", { name: "Cancel" }).click();
  await expect(page.locator(".view-lines")).toContainText("# unsaved-exit-marker");
  requestPolicy.clearIntercept("/api/source");
  await page.getByRole("button", { name: "Back to library" }).click();
  await dialog.getByRole("button", { name: "Leave assessment", exact: true }).click();
  await page.getByRole("button", { name: "Reconnect to active session" }).click();
  await expect(page.getByText("Python editor ready.", { exact: false })).toBeVisible();
  await expect(page.locator(".view-lines")).not.toContainText("# unsaved-exit-marker");
});

test("waits for an in-flight save before leaving", async ({ page }) => {
  await startAttempt(page);
  const held = requestPolicy.hold("/api/source");
  await appendSource(page, "# pending-exit-marker");
  await held;
  await page.getByRole("button", { name: "Back to library" }).click();
  await expect(page.getByRole("dialog")).not.toBeVisible();
  await expect(page.getByText("Wait for the current operation to finish before leaving.", { exact: true })).toBeVisible();
  requestPolicy.release("/api/source");
  await expect(page.locator(".assessment-header .header-status").nth(1).locator("strong"))
    .toHaveText("Saved snapshot");
  await page.getByRole("button", { name: "Back to library" }).click();
  await expect(page.getByRole("dialog", { name: "Leave assessment?" })).toBeVisible();
});

test("can return to start after submission without another confirmation or mutation", async ({ page }) => {
  await startAttempt(page);
  await page.getByRole("button", { name: "Submit", exact: true }).click();
  await page.getByRole("button", { name: "Submit attempt", exact: true }).click();
  await expect(page.getByRole("button", { name: "Submit", exact: true })).toBeDisabled();
  await expect(page.getByRole("textbox", { name: "Read-only Python source fallback" })).toBeVisible();
  const mutations = [];
  page.on("request", (request) => {
    if (["POST", "PUT"].includes(request.method())) mutations.push(request.method());
  });
  await page.getByRole("button", { name: "Back to library" }).click();
  await expect(page.getByRole("button", { name: "Start practice", exact: true })).toBeVisible();
  await expect(page.getByRole("dialog")).not.toBeVisible();
  expect(mutations).toHaveLength(0);
});

async function startAttempt(page) {
  await page.goto(`${harness.origin}/#token=${harness.token}`);
  await page.getByRole("button", { name: "Start practice" }).click();
  const response = page.waitForResponse((item) =>
    new URL(item.url()).pathname === "/api/attempts" &&
    item.request().method() === "POST",
  );
  await page.getByRole("button", { name: "Confirm and start" }).click();
  await response;
  await expect(page.getByText("Python editor ready.", { exact: false })).toBeVisible();
}

async function expectPrompt(page, level) {
  await expect(page.locator(".prompt-copy")).toContainText(
    `assessment/file_storage/level${level}.md`,
  );
}

async function appendSource(page, value) {
  await page.locator(".monaco-editor").click();
  await page.keyboard.press("Control+End");
  await page.keyboard.type(`\n${value}`);
}

async function verifyTabRoving(page) {
  const tabs = page.getByRole("tab");
  await page.getByRole("tab", { name: "Description" }).focus();
  await assertPromptIsSafe(page);
  await page.keyboard.press("ArrowRight");
  await expect(page.getByRole("tab", { name: "History" })).toBeFocused();
  await expect(page.locator(".prompt-copy")).toContainText("Restore this version");
  await assertPromptIsSafe(page);
  await page.keyboard.press("ArrowRight");
  await expect(page.getByRole("tab", { name: "Rules" })).toBeFocused();
  await expect(page.locator(".prompt-copy")).toContainText("timer is authoritative");
  await assertPromptIsSafe(page);
  await page.keyboard.press("ArrowRight");
  await expect(page.getByRole("tab", { name: "Info" })).toBeFocused();
  await expect(page.locator(".prompt-copy")).toContainText("local practice");
  await assertPromptIsSafe(page);
  await page.keyboard.press("End");
  await expect(page.getByRole("tab", { name: "Info" })).toBeFocused();
  await page.keyboard.press("Home");
  await expect(page.getByRole("tab", { name: "Description" })).toBeFocused();
  await expect(tabs).toHaveCount(4);
}

async function assertPromptIsSafe(page) {
  const text = await page.locator(".prompt-pane .prompt-copy").innerText();
  expect(text).not.toMatch(
    /\.cache|solution|study|vendor|test_simulation\.py|scorer|reference|FETCH_ONLY/iu,
  );
}

async function replaceFragment(page, attemptId, level, tab) {
  await page.evaluate(
    ({ attemptId: id, level: selectedLevel, tab: selectedTab }) => {
      const params = new URLSearchParams();
      params.set("attempt_id", id);
      params.set("level", String(selectedLevel));
      params.set("tab", selectedTab);
      window.history.replaceState(null, "", `#${params.toString()}`);
    },
    { attemptId, level, tab },
  );
}

async function reloadWithDefaultView(page, attemptId, level, tab) {
  await replaceFragment(page, attemptId, level, tab);
  await page.reload();
  await page.getByRole("button", { name: "Reconnect to active session" }).click();
  await expect(page.getByRole("button", { name: "Level 1: Level 1" }))
    .toHaveAttribute("aria-current", "step");
  await expect(page.getByRole("tab", { name: "Description" }))
    .toHaveAttribute("aria-selected", "true");
}

async function reloadWithView(page, attemptId, level, tab) {
  await replaceFragment(page, attemptId, level, tab);
  await page.reload();
  await page.getByRole("button", { name: "Reconnect to active session" }).click();
  await expect(page.getByRole("button", {
    name: `Level ${level}: Level ${level}`,
  })).toHaveAttribute("aria-current", "step");
}

function trackPromptRequests(page) {
  const requests = [];
  page.on("request", (request) => {
    const url = new URL(request.url());
    if (/^\/api\/prompts\/[1-4]$/u.test(url.pathname)) requests.push(url);
  });
  return requests;
}

function trackSourceMutations(page) {
  const requests = [];
  page.on("request", (request) => {
    const path = new URL(request.url()).pathname;
    if (["POST", "PUT"].includes(request.method()) &&
        path.startsWith("/api/source")) {
      requests.push(request);
    }
  });
  return requests;
}
