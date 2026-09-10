import { expect, test } from "@playwright/test";
import {
  installOfflineRequestPolicy,
  startFixtureServer,
} from "./browser_harness.mjs";
import { timeResponse, timerSeconds } from "./shell_test_support.mjs";

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
  await expect(page.locator(".prompt-copy")).toHaveText("No saved candidate versions yet.");
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
  const stalePromptRequest = page.waitForRequest(
    (request) =>
      new URL(request.url()).pathname === "/api/prompts/2" &&
      request.method() === "GET",
  );
  await page.getByRole("button", { name: "Level 2: Level 2" }).click();
  await stalePromptRequest;
  requestPolicy.intercept(`/api/time?attempt_id=${attemptId}`, timeResponse({
    ...session,
    status: "expired",
  }, started.data.time));
  await page.clock.fastForward("00:15");
  await expect(page.getByText("Expired", { exact: true })).toBeVisible();
  await expect(page.locator(".prompt-copy")).toHaveText(
    "synthetic prompt for assessment/file_storage/level1.md\n",
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

test("ignores a valid resync after terminal cleanup replaces its shell", async ({
  page,
}) => {
  await page.goto(`${harness.origin}/#token=${harness.token}`);
  await page.clock.install();
  const started = await startWithResponse(page);
  const attemptId = started.data.session.attempt_id;
  const timePath = `/api/time?attempt_id=${attemptId}`;
  const resyncRequest = page.waitForRequest(
    (request) => request.url().endsWith(timePath),
  );
  const resyncResponse = page.waitForResponse(
    (response) => response.url().endsWith(timePath),
  );
  requestPolicy.intercept(timePath, timeResponse(
    started.data.session,
    started.data.time,
  ));
  requestPolicy.delay(timePath, 1000);
  await page.evaluate(() => {
    window.__detachedShell = document.querySelector(".assessment-shell");
  });
  await page.clock.fastForward("00:15");
  await resyncRequest;

  await page.getByRole("button", { name: "Submit" }).click();
  await page.getByRole("button", { name: "Submit attempt" }).click();
  await expect(page.getByText("Submitted", { exact: true })).toBeVisible();
  await resyncResponse;
  await page.waitForTimeout(50);

  expect(await page.evaluate(() => ({
    replacement: document.querySelector(".assessment-shell")
      ?.querySelectorAll(".header-status strong")[2]?.textContent,
    detached: window.__detachedShell
      ?.querySelectorAll(".header-status strong")[2]?.textContent,
  }))).toEqual({
    replacement: "Connected",
    detached: "Reconnecting…",
  });
});

test("keeps an active countdown monotonic across an explicit stale refresh", async ({
  page,
}) => {
  await page.clock.install();
  await page.goto(`${harness.origin}/#token=${harness.token}`);
  const started = await startWithResponse(page);
  const attemptId = started.data.session.attempt_id;
  const timer = page.getByRole("timer", { name: "Time remaining" });
  await page.clock.fastForward("00:10");
  const beforeRefresh = timerSeconds(await timer.innerText());
  requestPolicy.expectHttpError(500);
  await page.route("**/api/submit**", (route) =>
    route.fulfill({
      status: 500,
      contentType: "application/json",
      body: JSON.stringify({
        schema_version: "web/v1",
        ok: false,
        error: { code: "internal_error", message: "temporary failure" },
      }),
    }));
  requestPolicy.intercept(
    `/api/time?attempt_id=${attemptId}`,
    timeResponse(started.data.session, started.data.time),
  );
  const refreshResponse = page.waitForResponse(
    (response) => new URL(response.url()).pathname === "/api/time",
  );
  await page.getByRole("button", { name: "Submit" }).click();
  await page.getByRole("button", { name: "Submit attempt" }).click();
  await refreshResponse;
  await expect(page.getByText("Active", { exact: true })).toBeVisible();
  expect(timerSeconds(await timer.innerText())).toBeLessThanOrEqual(beforeRefresh);
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
    "Attempt expired. Source remains available. Results remain available in read-only mode.",
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
    "Attempt expired. Source remains available. Results remain available in read-only mode.",
  );
  expect(timeRequests).toHaveLength(1);
  await page.clock.fastForward("01:00");
  expect(timeRequests).toHaveLength(1);
});

test("reloads authoritative source for a submitted final state", async ({ page }) => {
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
  const expectedSource = started.data.source.content;
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
    "Final result announced. Passed levels: 4 of 4. Source remains available. Results are final and read-only.",
  );
  for (const name of ["Save changes", "Run Tests", "Reset", "Submit"]) {
    await expect(page.getByRole("button", { name })).toBeDisabled();
  }
  await expect(page.getByRole("button", { name: "Level 1: Level 1" })).toBeEnabled();
  await expect(page.locator(".fallback")).toHaveValue(expectedSource);
  await expect(page.locator(".fallback")).toHaveAttribute("readonly", "");
  expect(sourceRequests).toBe(1);
});

async function confirmStart(page) {
  await expect(page.locator(".entry")).toBeVisible();
  await page.getByRole("button", { name: "Start practice" }).click();
  await page.getByRole("button", { name: "Confirm and start" }).click();
  await expect(page.getByTestId("editor-pane")).toBeVisible();
  await expect(page.locator(".status")).toHaveText(/Python editor ready/);
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
