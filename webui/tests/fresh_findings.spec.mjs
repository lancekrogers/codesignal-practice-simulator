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

test("active evaluation snapshots update countdown without wall-clock age", async ({
  page,
}) => {
  await page.clock.install();
  await openAttempt(page);
  await page.route("**/api/test**", (route) =>
    rewriteEvaluation(route, (data) => {
      data.time.remaining_seconds = 30;
      data.time.observed_at = "2000-01-01T00:00:00.000Z";
    }));
  await page.getByRole("button", { name: "Run Tests" }).click();
  await expect(page.getByRole("timer", { name: "Time remaining" }))
    .toHaveText("00:30");
  await expect(page.getByText("Active", { exact: true })).toBeVisible();
});

test("refresh rejects a time snapshot for another attempt", async ({ page }) => {
  await page.clock.install();
  const started = await startWithResponse(page);
  const before = await shellSnapshot(page);
  const otherSession = {
    ...started.data.session,
    attempt_id: "different-attempt",
  };
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
    `/api/time?attempt_id=${started.data.session.attempt_id}`,
    timeResponse(otherSession, started.data.time),
  );
  await page.getByRole("button", { name: "Submit" }).click();
  await page.getByRole("button", { name: "Submit attempt" }).click();
  await expect(page.getByText("Reconnecting…", { exact: true })).toBeVisible();
  await expect(page.getByText("Active", { exact: true })).toBeVisible();
  expect(await shellSnapshot(page)).toEqual(before);
});

test("countdown resync rejects a time snapshot for another attempt", async ({
  page,
}) => {
  await page.clock.install();
  const started = await startWithResponse(page);
  const before = await shellSnapshot(page);
  const otherSession = {
    ...started.data.session,
    attempt_id: "different-attempt",
  };
  requestPolicy.intercept(
    `/api/time?attempt_id=${started.data.session.attempt_id}`,
    timeResponse(otherSession, started.data.time),
  );
  await page.clock.fastForward("00:15");
  await expect(page.getByText("Reconnecting…", { exact: true })).toBeVisible();
  await expect(page.getByText("Active", { exact: true })).toBeVisible();
  const after = await shellSnapshot(page);
  expect(timerSeconds(after.timer)).toBe(timerSeconds(before.timer) - 15);
  expect(after.source).toBe(before.source);
  expect(after.output).toBe(before.output);
  expect(after.mutationControls).toEqual(before.mutationControls);
});

test("evaluation rejects a response for another attempt", async ({ page }) => {
  await openAttempt(page);
  const before = await shellSnapshot(page);
  await page.route("**/api/test**", (route) =>
    rewriteEvaluation(route, (data) => {
      data.session.attempt_id = "different-attempt";
      data.time.session.attempt_id = "different-attempt";
    }));
  await page.getByRole("button", { name: "Run Tests" }).click();
  await expect(page.getByText("Active", { exact: true })).toBeVisible();
  await expect(page.getByTestId("output-drawer")).toContainText(
    "Run local practice checks",
  );
  await expect(page.getByRole("button", { name: "Run Tests" })).toBeEnabled();
  expect(await shellSnapshot(page)).toEqual(before);
});

test("terminal evaluation transitions once with payload evidence", async ({ page }) => {
  await page.route("**/api/submit**", (route) =>
    rewriteEvaluation(route, (data) => setFailureAndError(data)));
  await openAttempt(page);
  await page.evaluate(() => {
    window.__terminalShells = 0;
    new MutationObserver((records) => {
      window.__terminalShells += records
        .flatMap((record) => [...record.addedNodes])
        .filter((node) => node instanceof HTMLElement &&
          node.classList.contains("assessment-shell"))
        .length;
    }).observe(document.getElementById("app"), { childList: true });
  });
  await page.getByRole("button", { name: "Submit" }).click();
  await page.getByRole("button", { name: "Submit attempt" }).click();
  await expect(page.getByText("Submitted", { exact: true })).toBeVisible();
  await expect.poll(() => page.evaluate(() => window.__terminalShells)).toBe(1);
  const output = page.getByTestId("output-drawer");
  await expect(output).toContainText(
    "The candidate solution did not pass this practice level.",
  );
  await expect(output).toContainText(
    "The local practice check could not be completed.",
  );
  await expect(page.locator("#level-2-status")).toHaveText(
    "Reached · Completed · Practice test: failed",
  );
  await expect(page.locator("#level-3-status")).toHaveText(
    "Reached · Completed · Practice test: error",
  );
  await expect(output).not.toContainText("SCORER_INTERNAL_SENTINEL");
});

test("rejects a terminal evaluation without authoritative source", async ({
  page,
}) => {
  await page.route("**/api/submit**", (route) =>
    rewriteEvaluation(route, (data) => {
      data.source = null;
    }));
  await openAttempt(page);
  const sourceBefore = await page.locator(".fallback").inputValue();

  await page.getByRole("button", { name: "Submit" }).click();
  await page.getByRole("button", { name: "Submit attempt" }).click();
  await expect(page.getByText("Active", { exact: true })).toBeVisible();
  await expect(page.locator(".sr-status")).toContainText(
    "submission could not complete safely",
  );
  await expect(page.getByText("Submitted", { exact: true })).toHaveCount(0);
  await expect(page.locator(".monaco-editor .view-lines")).toContainText(
    "def evaluate(group):",
  );
  await expect(page.locator(".fallback")).toHaveValue(sourceBefore);
});

test("reconnect rejects a time snapshot for another attempt", async ({ page }) => {
  await page.goto(`${harness.origin}/#token=${harness.token}`);
  await page.getByRole("button", { name: "Start practice" }).click();
  await page.getByRole("button", { name: "Confirm and start" }).click();
  await page.reload();
  const attemptId = await page.locator(".entry").getAttribute("data-active-attempt-id");
  const session = {
    attempt_id: "different-attempt",
    status: "active",
    profile: { mode: "full", profile_id: "full-90m", duration_seconds: 5400 },
    started_at: "2030-01-01T00:00:00+00:00",
    deadline_at: "2030-01-01T01:30:00+00:00",
    score: null,
    submitted_at: null,
  };
  requestPolicy.intercept(
    `/api/time?attempt_id=${attemptId}`,
    timeResponse(session, {
      observed_at: session.started_at,
      elapsed_seconds: 0,
      remaining_seconds: 5400,
    }),
  );
  await page.getByRole("button", { name: "Reconnect to active session" }).click();
  await expect(page.locator(".error-message")).toContainText(
    "selected session could not be restored safely",
  );
  await expect(page.getByTestId("editor-pane")).toHaveCount(0);
});

test("terminal reload derives fixed evidence from the stored score", async ({
  page,
}) => {
  await page.goto(`${harness.origin}/#token=${harness.token}`);
  await page.getByRole("button", { name: "Start practice" }).click();
  await page.getByRole("button", { name: "Confirm and start" }).click();
  await page.route("**/api/submit**", (route) =>
    rewriteEvaluation(route, (data) => setFailureAndError(data)));
  await page.getByRole("button", { name: "Submit" }).click();
  const response = page.waitForResponse(
    (item) => new URL(item.url()).pathname === "/api/submit",
  );
  await page.getByRole("button", { name: "Submit attempt" }).click();
  const submitted = await (await response).json();
  const terminal = submitted.data.session.attempt_id;
  const finalSession = submitted.data.session;
  await page.reload();
  requestPolicy.intercept(
    `/api/time?attempt_id=${terminal}`,
    timeResponse(finalSession, {
      observed_at: finalSession.started_at,
      elapsed_seconds: 5400,
      remaining_seconds: 0,
    }),
  );
  await page.getByRole("button", { name: "View final session" }).click();
  const output = page.getByTestId("output-drawer");
  await expect(output).toContainText(
    "The candidate solution did not pass this practice level.",
  );
  await expect(output).toContainText(
    "The local practice check could not be completed.",
  );
  await expect(output).not.toContainText("SCORER_INTERNAL_SENTINEL");
});

async function openAttempt(page) {
  await page.goto(`${harness.origin}/#token=${harness.token}`);
  await page.getByRole("button", { name: "Start practice" }).click();
  await page.getByRole("button", { name: "Confirm and start" }).click();
  await expect(page.getByTestId("editor-pane")).toBeVisible();
}

async function startWithResponse(page) {
  const response = page.waitForResponse(
    (item) =>
      new URL(item.url()).pathname === "/api/attempts" &&
      item.request().method() === "POST",
  );
  await openAttempt(page);
  return (await response).json();
}

async function rewriteEvaluation(route, change) {
  const response = await route.fetch();
  const body = await response.json();
  change(body.data);
  await route.fulfill({ response, body: JSON.stringify(body) });
}

function setFailureAndError(data) {
  const outcomes = ["passed", "failed", "error", "passed"];
  data.session.score.levels.forEach((level, index) => {
    level.outcome = outcomes[index];
  });
  data.session.score.passed_levels = 2;
  data.session.score.highest_contiguous_level = 1;
  data.practice.levels.forEach((level, index) => {
    level.outcome = outcomes[index];
    level.candidate_output = index === 1
      ? "The candidate solution did not pass this practice level."
      : null;
    level.candidate_error = index === 2
      ? "The local practice check could not be completed."
      : null;
  });
}

async function shellSnapshot(page) {
  return {
    timer: await page.getByRole("timer", { name: "Time remaining" }).innerText(),
    source: await page.locator(".monaco-editor .view-lines").innerText(),
    output: await page.getByTestId("output-drawer").innerText(),
    mutationControls: await page.locator("[data-mutation='true']").evaluateAll(
      (controls) => controls.map((control) => ({
        text: control.textContent,
        disabled: control.disabled,
      })),
    ),
  };
}
