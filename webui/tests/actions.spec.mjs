import { expect, test } from "@playwright/test";
import {
  installOfflineRequestPolicy,
  startFixtureServer,
} from "./browser_harness.mjs";
import { timeResponse } from "./shell_test_support.mjs";

test.describe.configure({ mode: "serial" });

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

test("Run Tests renders passing and candidate-failing practice groups", async ({ page }) => {
  let failing = false;
  await page.route("**/api/test**", (route) =>
    rewriteEvaluation(route, (data) => {
      if (failing) setFailingScore(data);
    }));
  await openAttempt(page);
  await page.getByRole("button", { name: "Run Tests" }).click();
  await expect(page.getByTestId("output-drawer")).toContainText(
    "Practice result · Passed levels: 4 of 4.",
  );
  failing = true;
  await page.getByRole("button", { name: "Run Tests" }).click();
  await expect(page.getByTestId("output-drawer")).toContainText(
    "Practice result · Passed levels: 3 of 4.",
  );
  await expect(page.getByTestId("output-drawer")).toContainText("Needs work");
  await expect(page.locator("#level-2-status")).toHaveText(
    "Reached · Completed · Practice test: failed",
  );
});

test("derives safe score-only evidence when practice is absent", async ({ page }) => {
  await page.route("**/api/test**", (route) =>
    rewriteEvaluation(route, (data) => {
      setFailingScore(data);
      delete data.practice;
    }));
  await openAttempt(page);
  await page.getByRole("button", { name: "Run Tests" }).click();
  await expect(page.getByTestId("output-drawer")).toContainText(
    "The candidate solution did not pass this practice level.",
  );
});

test("candidate failure is distinct from transport and internal failure", async ({ page }) => {
  await page.route("**/api/test**", (route) =>
    rewriteEvaluation(route, (data) => setFailingScore(data)));
  await openAttempt(page);
  await page.getByRole("button", { name: "Run Tests" }).click();
  await expect(page.getByTestId("output-drawer")).toContainText("Needs work");
  await page.unroute("**/api/test**");
  await page.route("**/api/test**", async (route) => {
    requestPolicy.expectHttpError({
      method: "POST",
      path: "/api/test",
      status: 500,
    });
    await route.fulfill({
      status: 500,
      contentType: "application/json",
      body: JSON.stringify({
        schema_version: "web/v1",
        ok: false,
        error: { code: "internal_error", message: "hidden detail" },
      }),
    });
  });
  await page.getByRole("button", { name: "Run Tests" }).click();
  await expect(page.locator(".sr-status")).toContainText(
    "local practice check could not complete safely",
  );
  await expect(page.locator(".sr-status")).not.toContainText("Reconnect");
  await expect(page.getByTestId("output-drawer")).toContainText("Needs work");
});

test("rejects unsupported practice text instead of displaying raw diagnostics", async ({
  page,
}) => {
  await page.route("**/api/test**", (route) =>
    rewriteEvaluation(route, (data) => {
      setFailingScore(data);
      data.practice.levels[0].candidate_output = "😀".repeat(5000);
      data.practice.levels[1].candidate_output = "FETCH_ONLY /tmp/reference";
    }));
  await openAttempt(page);
  await page.getByRole("button", { name: "Run Tests" }).click();
  const output = page.getByTestId("output-drawer");
  await expect(page.locator(".sr-status")).toContainText(
    "local practice check could not complete safely",
  );
  await expect(output).not.toContainText("FETCH_ONLY");
  await expect(output).not.toContainText("SCORER_INTERNAL_SENTINEL");
});

test("rejects missing fixed evidence for a failed practice level", async ({ page }) => {
  await page.route("**/api/test**", (route) =>
    rewriteEvaluation(route, (data) => {
      setFailingScore(data);
      data.practice.levels[1].candidate_output = null;
    }));
  await openAttempt(page);
  await page.getByRole("button", { name: "Run Tests" }).click();
  await expect(page.locator(".sr-status")).toContainText(
    "local practice check could not complete safely",
  );
  await expect(page.getByTestId("output-drawer")).toContainText(
    "Run local practice checks",
  );
});

test("rejects missing fixed evidence for an error practice level", async ({ page }) => {
  await page.route("**/api/test**", (route) =>
    rewriteEvaluation(route, (data) => {
      const outcomes = ["passed", "error", "passed", "passed"];
      data.session.score.levels.forEach((level, index) => {
        level.outcome = outcomes[index];
      });
      data.session.score.passed_levels = 3;
      data.session.score.highest_contiguous_level = 1;
      data.practice.levels.forEach((level, index) => {
        level.outcome = outcomes[index];
        level.candidate_output = null;
        level.candidate_error = null;
      });
    }));
  await openAttempt(page);
  await page.getByRole("button", { name: "Run Tests" }).click();
  await expect(page.locator(".sr-status")).toContainText(
    "local practice check could not complete safely",
  );
});

test("rejects practice results that disagree with the score", async ({ page }) => {
  await page.route("**/api/test**", (route) =>
    rewriteEvaluation(route, (data) => {
      setFailingScore(data);
      data.practice.levels[0].outcome = "failed";
      data.practice.levels[0].candidate_output =
        "The candidate solution did not pass this practice level.";
    }));
  await openAttempt(page);
  await page.getByRole("button", { name: "Run Tests" }).click();
  await expect(page.locator(".sr-status")).toContainText(
    "local practice check could not complete safely",
  );
  await expect(page.getByTestId("output-drawer")).toContainText(
    "Run local practice checks",
  );
});

test("flushes the exact source before one test request", async ({ page }) => {
  const requests = [];
  page.on("request", (request) => {
    const path = new URL(request.url()).pathname;
    if (path === "/api/source" || path === "/api/test") {
      requests.push({ method: request.method(), path, body: request.postData() });
    }
  });
  await openAttempt(page);
  await editSource(page, "print('saved before testing')\n");
  await page.getByRole("button", { name: "Run Tests" }).click();
  await expect.poll(() => requests.some((item) => item.path === "/api/test")).toBe(true);
  expect(requests.map((item) => item.method)).toEqual(["PUT", "POST"]);
  expect(JSON.parse(requests[1].body).content).toContain("saved before testing");
});

test("double-click and competing actions produce one evaluation", async ({ page }) => {
  let tests = 0;
  const testHeld = requestPolicy.hold("/api/test");
  page.on("request", (request) => {
    if (new URL(request.url()).pathname === "/api/test") tests += 1;
  });
  await openAttempt(page);
  const run = page.getByRole("button", { name: "Run Tests" });
  await run.evaluate((button) => {
    button.dispatchEvent(new MouseEvent("click", { bubbles: true, cancelable: true }));
    button.dispatchEvent(new MouseEvent("click", { bubbles: true, cancelable: true }));
  });
  await expect.poll(() => tests).toBe(1);
  await testHeld;
  await page.getByRole("button", { name: "Submit" }).evaluate((button) =>
    button.dispatchEvent(new MouseEvent("click", { bubbles: true, cancelable: true })),
  );
  requestPolicy.release("/api/test");
  await expect(page.getByTestId("output-drawer")).toContainText("Practice result");
  expect(tests).toBe(1);
});

test("shared lock blocks evaluations during delayed restore and reset", async ({ page }) => {
  await openAttempt(page);
  await editSource(page, "print('restore target')\n");
  await expect(saveStatus(page)).toHaveText("Saved snapshot");
  await editSource(page, "print('current source')\n");
  await expect(saveStatus(page)).toHaveText("Saved snapshot");
  await page.getByRole("tab", { name: "History" }).click();
  const restore = page.getByRole("button", { name: "Restore this version" }).first();
  const evaluations = trackRequests(page, (request) => {
    const path = new URL(request.url()).pathname;
    return request.method() === "POST" &&
      ["/api/test", "/api/submit"].includes(path);
  });
  const restoreHeld = requestPolicy.hold("/api/source/restore");
  const restoreRequest = page.waitForRequest(
    (request) => new URL(request.url()).pathname === "/api/source/restore",
  );
  const restoreResponse = page.waitForResponse(
    (response) => new URL(response.url()).pathname === "/api/source/restore",
  );
  await restore.click();
  await page.getByRole("dialog").getByRole("button", { name: "Restore version" }).click();
  await restoreRequest;
  await restoreHeld;
  await tryEvaluationActions(page);
  expect(evaluations).toHaveLength(0);
  requestPolicy.release("/api/source/restore");
  await restoreResponse;
  await expect(page.locator(".monaco-editor .view-lines")).toContainText(
    "restore target",
  );
  await expect(saveStatus(page)).toHaveText("Saved snapshot");

  const resetHeld = requestPolicy.hold("/api/source/reset");
  const resetRequest = page.waitForRequest(
    (request) => new URL(request.url()).pathname === "/api/source/reset",
  );
  const resetResponse = page.waitForResponse(
    (response) => new URL(response.url()).pathname === "/api/source/reset",
  );
  await page.getByRole("button", { name: "Reset" }).click();
  await page.getByRole("dialog").getByRole("button", { name: "Reset source" }).click();
  await resetRequest;
  await resetHeld;
  await tryEvaluationActions(page);
  expect(evaluations).toHaveLength(0);
  requestPolicy.release("/api/source/reset");
  await resetResponse;
  await expect(page.locator(".monaco-editor .view-lines")).not.toContainText(
    "restore target",
  );
  await expect(page.locator(".monaco-editor .view-lines")).not.toContainText(
    "current source",
  );
  await expect(saveStatus(page)).toHaveText("Saved snapshot");
});

test("shared lock blocks reset and restore during delayed testing", async ({ page }) => {
  await openAttempt(page);
  await editSource(page, "print('restore candidate')\n");
  await expect(saveStatus(page)).toHaveText("Saved snapshot");
  await page.getByRole("tab", { name: "History" }).click();
  const restore = page.getByRole("button", { name: "Restore this version" }).first();
  const sourceMutations = trackRequests(page, (request) => {
    const path = new URL(request.url()).pathname;
    return ["PUT", "POST"].includes(request.method()) &&
      path.startsWith("/api/source");
  });
  const testHeld = requestPolicy.hold("/api/test");
  const testRequest = page.waitForRequest(
    (request) => new URL(request.url()).pathname === "/api/test",
  );
  const testResponse = page.waitForResponse(
    (response) => new URL(response.url()).pathname === "/api/test",
  );
  await page.getByRole("button", { name: "Run Tests" }).click();
  await testRequest;
  await testHeld;
  const reset = page.getByRole("button", { name: "Reset" });
  await expect(reset).toBeDisabled();
  await restore.click();
  const dialog = page.getByRole("dialog");
  if (await dialog.isVisible()) {
    await dialog.getByRole("button", { name: "Restore version" }).click();
  }
  expect(sourceMutations).toHaveLength(0);
  requestPolicy.release("/api/test");
  await testResponse;
  await expect(page.getByTestId("output-drawer")).toContainText("Practice result");
  await expect(page.locator(".monaco-editor .view-lines")).toContainText(
    "restore candidate",
  );
  expect(sourceMutations).toHaveLength(0);
  await expect(page.getByRole("button", { name: "Reset" })).toBeEnabled();
  await expect(page.getByRole("button", { name: "Submit" })).toBeEnabled();
});

test("submit cancel restores opener focus and confirm locks the terminal UI", async ({ page }) => {
  await openAttempt(page);
  const submit = page.getByRole("button", { name: "Submit" });
  await submit.click();
  const dialog = page.getByRole("dialog");
  await expect(dialog).toHaveAccessibleName("Submit local practice attempt");
  await expect(dialog).toHaveAccessibleDescription(
    "Submitting ends this timed practice session. Editing, saving, and local checks will be disabled. The stored result cannot be changed.",
  );
  await page.getByRole("button", { name: "Cancel" }).click();
  await expect(submit).toBeFocused();
  await submit.click();
  await page.getByRole("button", { name: "Submit attempt" }).click();
  await expect(page.getByText("Submitted", { exact: true })).toBeVisible();
  await expect(page.getByRole("button", { name: "Run Tests" })).toBeDisabled();
  await expect(page.getByRole("button", { name: "Submit" })).toBeDisabled();
  await expect(page.locator(".fallback")).toHaveAttribute("readonly", "");
});

test("submitted rerender preserves safe candidate failure evidence", async ({ page }) => {
  await page.route("**/api/submit**", (route) =>
    rewriteEvaluation(route, (data) => setFailingScore(data)));
  await openAttempt(page);
  await page.getByRole("button", { name: "Submit" }).click();
  await page.getByRole("button", { name: "Submit attempt" }).click();

  const output = page.getByTestId("output-drawer");
  await expect(page.getByText("Submitted", { exact: true })).toBeVisible();
  await expect(output).toContainText("Final result · Passed levels: 3 of 4.");
  await expect(output).toContainText("Level 2: Needs work");
  await expect(output).toContainText("The candidate solution did not pass this practice level.");
  await expect(output).not.toContainText("SCORER_INTERNAL_SENTINEL");
});

test("flushes the exact source before one submit", async ({ page }) => {
  const requests = [];
  page.on("request", (request) => {
    const path = new URL(request.url()).pathname;
    if (path === "/api/source" || path === "/api/submit") {
      requests.push({ method: request.method(), path, body: request.postData() });
    }
  });
  await openAttempt(page);
  await editSource(page, "print('saved before submit')\n");
  await page.getByRole("button", { name: "Submit" }).click();
  await page.getByRole("button", { name: "Submit attempt" }).click();
  await expect(page.getByText("Submitted", { exact: true })).toBeVisible();
  expect(requests.map(({ method, path }) => ({ method, path }))).toEqual([
    { method: "PUT", path: "/api/source" },
    { method: "POST", path: "/api/submit" },
  ]);
  expect(new Set(requests.map(({ method, path }) => `${method} ${path}`)).size)
    .toBe(2);
  expect(JSON.parse(requests[0].body).content).toContain("saved before submit");
});

test("timer zero resynchronizes active and server-expired sessions", async ({ page }) => {
  await page.clock.install();
  const started = await openAttemptWithResponse(page);
  const activeTime = {
    ...started.data.time,
    remaining_seconds: 30,
  };
  requestPolicy.intercept(
    `/api/time?attempt_id=${started.data.session.attempt_id}`,
    timeResponse(started.data.session, activeTime),
  );
  await page.clock.fastForward("00:31");
  await expect(page.getByText("Active", { exact: true })).toBeVisible();
  await expect(page.getByRole("button", { name: "Submit" })).toBeEnabled();
  await expect(page.getByRole("timer", { name: "Time remaining" }))
    .not.toHaveText("00:00");
  await page.clock.fastForward("01:00");
  requestPolicy.intercept(
    `/api/time?attempt_id=${started.data.session.attempt_id}`,
    timeResponse({ ...started.data.session, status: "expired" }, activeTime),
  );
  await page.clock.fastForward("01:00");
  await expect(page.getByText("Expired", { exact: true })).toBeVisible();
});

test("repeat submit and reload preserve the stored score without rescoring", async ({ page }) => {
  await page.goto(`${harness.origin}/#token=${harness.token}`);
  const first = await submitAttempt(page);
  const repeat = await page.evaluate(async ({ attemptId }) => {
    const response = await fetch(`/api/submit?attempt_id=${attemptId}`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "If-Match": "sha256:" + "f".repeat(64),
        "Origin": location.origin,
        "X-Simulator-Token": sessionStorage.getItem("simulator-token") || "",
      },
      body: JSON.stringify({ content: "ignored after finality\n" }),
    });
    return response.json();
  }, { attemptId: first.data.session.attempt_id });
  expect(repeat.data.newly_submitted).toBe(false);
  expect(repeat.data.session.score).toEqual(first.data.session.score);
  await page.reload();
  await page.getByRole("button", { name: "View final session" }).click();
  await expect(page.getByText("Final result", { exact: false })).toBeVisible();
  await expect(page.getByRole("button", { name: "Run Tests" })).toBeDisabled();
});

test("submitted reconnect reloads authoritative source after a real process restart", async ({
  page,
}) => {
  const first = await submitAttempt(page);
  const expectedSource = first.data.source.content;
  await harness.restart();
  requestPolicy.refreshOrigin();
  await page.goto(`${harness.origin}/#token=${harness.token}`);
  // The library lists the submitted session once the bootstrap resolves; the
  // explicit action opens the read-only view.
  const viewFinal = page.getByRole("button", { name: "View final session" });
  await expect(viewFinal).toBeVisible();
  await viewFinal.click();
  await expect(page.getByText("Submitted", { exact: true })).toBeVisible();
  await expect(page.getByTestId("output-drawer")).toContainText(
    "Final result · Passed levels:",
  );
  await expect(page.locator(".fallback")).toHaveValue(expectedSource);
  await expect(page.locator(".fallback")).toHaveAttribute("readonly", "");
});

async function openAttempt(page) {
  await page.goto(`${harness.origin}/#token=${harness.token}`);
  await page.getByRole("button", { name: "Start practice" }).click();
  await page.getByRole("button", { name: "Confirm and start" }).click();
  await expect(page.getByTestId("editor-pane")).toBeVisible();
}

async function openAttemptWithResponse(page) {
  const response = page.waitForResponse(
    (item) => new URL(item.url()).pathname === "/api/attempts",
  );
  await openAttempt(page);
  return (await response).json();
}

async function submitAttempt(page) {
  await openAttempt(page);
  await page.getByRole("button", { name: "Submit" }).click();
  const response = page.waitForResponse(
    (item) => new URL(item.url()).pathname === "/api/submit",
  );
  await page.getByRole("button", { name: "Submit attempt" }).click();
  return (await response).json();
}

async function editSource(page, content) {
  await page.locator(".editor").click();
  await page.keyboard.press("Meta+A");
  await page.keyboard.type(content);
}

function saveStatus(page) {
  return page.locator(".assessment-header .header-status").nth(1).locator("strong");
}

function trackRequests(page, predicate) {
  const requests = [];
  page.on("request", (request) => {
    if (predicate(request)) requests.push(request);
  });
  return requests;
}

async function tryEvaluationActions(page) {
  for (const name of ["Run Tests", "Submit"]) {
    const control = page.getByRole("button", { name });
    if (await control.isEnabled()) await control.click();
  }
  await expect(page.getByRole("dialog")).toBeHidden();
}

async function rewriteEvaluation(route, change) {
  const response = await route.fetch();
  const body = await response.json();
  change(body.data);
  await route.fulfill({ response, body: JSON.stringify(body) });
}

function setFailingScore(data) {
  const outcomes = ["passed", "failed", "passed", "passed"];
  data.session.score.levels.forEach((level, index) => {
    level.outcome = outcomes[index];
  });
  data.session.score.passed_levels = 3;
  data.session.score.highest_contiguous_level = 1;
  data.practice.levels.forEach((level, index) => {
    level.outcome = outcomes[index];
    level.candidate_output = index === 1
      ? "The candidate solution did not pass this practice level."
      : null;
  });
}
