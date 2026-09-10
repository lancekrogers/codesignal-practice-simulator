import { expect, test } from "@playwright/test";
import {
  installOfflineRequestPolicy,
  startFixtureServer,
} from "./browser_harness.mjs";

test.describe.configure({ mode: "serial" });

let harness;
let requestPolicy;

test.beforeEach(async ({ page }) => {
  harness = await startFixtureServer({
    clockStart: "2030-01-01T00:00:00+00:00",
  });
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

test("real server expiry locks every browser mutation", async ({ page }) => {
  const mutations = [];
  const timeSessions = [];
  page.on("request", (request) => {
    if (request.method() !== "GET" && new URL(request.url()).pathname.startsWith("/api/")) {
      mutations.push(request);
    }
  });
  page.on("response", (response) => {
    if (new URL(response.url()).pathname !== "/api/time") return;
    void response.json().then((document) => timeSessions.push(document.data.session));
  });

  await page.goto(`${harness.origin}/#token=${harness.token}`);
  await page.clock.install();
  const started = await startAttempt(page);
  await harness.setClock(started.data.session.deadline_at);
  await page.clock.fastForward("31:00");

  await expect(page.getByText("Expired", { exact: true })).toBeVisible();
  await expect.poll(() => timeSessions.some((session) => session.status === "expired"))
    .toBe(true);
  for (const name of ["Save changes", "Run Tests", "Reset", "Submit"]) {
    const control = page.getByRole("button", { name });
    await expect(control).toBeDisabled();
    await control.evaluate((button) =>
      button.dispatchEvent(new MouseEvent("click", { bubbles: true })),
    );
  }
  await expect(page.locator(".fallback")).toHaveAttribute("readonly", "");
  const settledMutations = mutations.length;
  await expect.poll(() => mutations.length).toBe(settledMutations);
});

test("expired attempt accepts one timeout submission and stays immutable", async ({
  page,
}) => {
  await page.goto(`${harness.origin}/#token=${harness.token}`);
  await page.clock.install();
  const started = await startAttempt(page);
  const attemptId = started.data.session.attempt_id;

  await harness.setClock(started.data.session.deadline_at);
  await page.clock.fastForward("31:00");
  await expect(page.getByText("Expired", { exact: true })).toBeVisible();
  for (const name of ["Save changes", "Run Tests", "Reset", "Submit"]) {
    await expect(page.getByRole("button", { name })).toBeDisabled();
  }

  const first = await retrySubmit(page, harness, attemptId, started.data.source);
  expect(first.status).toBe(200);
  expect(first.document.data.newly_submitted).toBe(true);
  expect(first.document.data.session.status).toBe("submitted");
  expect(first.document.data.score).toEqual(first.document.data.session.score);
  expect(await harness.scoreCalls()).toBe(1);
  expect(await harness.attemptEvents(attemptId)).toEqual([
    "started",
    "expired",
    "submitted",
  ]);

  const beforeRepeatContext = await harness.cliContext(attemptId);
  const beforeRepeatStatus = await harness.readStatus(attemptId);
  expect(beforeRepeatContext.lifecycle.status).toBe("submitted");
  expect(beforeRepeatContext.score).toEqual(first.document.data.session.score);

  const repeated = await retrySubmit(
    page,
    harness,
    attemptId,
    first.document.data.source,
  );
  expect(repeated.status).toBe(200);
  expect(repeated.document.data.newly_submitted).toBe(false);
  expect(repeated.document.data.session).toEqual(first.document.data.session);
  expect(repeated.document.data.score).toEqual(first.document.data.score);
  expect(repeated.document.data.source).toEqual(first.document.data.source);
  expect(await harness.scoreCalls()).toBe(1);
  expect(await harness.cliContext(attemptId)).toEqual(beforeRepeatContext);
  expect(await harness.readStatus(attemptId)).toBe(beforeRepeatStatus);

  await harness.restart();
  requestPolicy.refreshOrigin();
  await page.reload();
  const viewFinal = page.getByRole("button", { name: "View final session" });
  // Reload finishes before bootstrap resolves. Wait for either valid final
  // presentation before deciding whether an explicit reconnect is required.
  await expect.poll(async () =>
    await viewFinal.isVisible() ||
    await page.getByText("Submitted", { exact: true }).isVisible()
  ).toBe(true);
  if (await viewFinal.isVisible()) await viewFinal.click();
  await expect(page.getByText("Submitted", { exact: true })).toBeVisible();
  await expect(page.getByTestId("output-drawer")).toContainText(
    "Final result · Passed levels: 4 of 4.",
  );
  expect(await harness.scoreCalls()).toBe(1);
  expect(await harness.cliContext(attemptId)).toEqual(beforeRepeatContext);
  expect(await harness.readStatus(attemptId)).toBe(beforeRepeatStatus);
});

test("lost submit response recovers terminal state and retries idempotently", async ({
  page,
}) => {
  const terminalTimes = [];
  page.on("response", (response) => {
    if (new URL(response.url()).pathname !== "/api/time") return;
    void response.json().then((document) => {
      if (document.data.session.status === "submitted") terminalTimes.push(document.data);
    });
  });
  await page.goto(`${harness.origin}/#token=${harness.token}`);
  const started = await startAttempt(page);
  const { attempt_id: attemptId } = started.data.session;

  requestPolicy.expectConsoleError({
    message: "Failed to load resource: net::ERR_CONNECTION_CLOSED",
    count: 1,
  });
  requestPolicy.expectFailedRequest({
    method: "POST",
    path: "/api/submit",
    count: 1,
  });
  await page.route("**/api/submit*", async (route) => {
    await route.fetch();
    await route.abort("connectionclosed");
  });
  await page.getByRole("button", { name: "Submit" }).click();
  await page.getByRole("button", { name: "Submit attempt" }).click();
  await expect(page.getByText("Submitted", { exact: true })).toBeVisible();
  await expect(page.getByTestId("output-drawer")).toContainText(
    "Final result · Passed levels: 4 of 4.",
  );
  await expect.poll(() => terminalTimes.length).toBeGreaterThan(0);
  await expect.poll(() => harness.scoreCalls()).toBe(1);
  await page.unroute("**/api/submit*");

  const retry = await retrySubmit(page, harness, attemptId, started.data.source);
  expect(retry.status).toBe(200);
  expect(retry.document.data.newly_submitted).toBe(false);
  expect(retry.document.data.session.status).toBe("submitted");
  expect(retry.document.data.score).toEqual(retry.document.data.session.score);
  expect(await harness.scoreCalls()).toBe(1);
  expect(await harness.attemptEvents(attemptId)).toEqual(["started", "submitted"]);
});

test("stored failed and error scores stay safe after a real process restart", async ({
  page,
}) => {
  await page.goto(`${harness.origin}/#token=${harness.token}`);
  const started = await startAttempt(page);
  await replaceSource(
    page,
    `def evaluate(group): return "wrong" if group == 2 else 1 / 0 if group == 3 else "ok"\n`,
  );
  await page.getByRole("button", { name: "Submit" }).click();
  await page.getByRole("button", { name: "Submit attempt" }).click();
  await expect(page.getByText("Submitted", { exact: true })).toBeVisible();
  const output = page.getByTestId("output-drawer");
  await expect(output).toContainText(
    "The candidate solution did not pass this practice level.",
  );
  await expect(output).toContainText(
    "The local practice check could not be completed.",
  );
  await expect(output).not.toContainText("SCORER_INTERNAL_SENTINEL");
  await expect(output).not.toContainText(".scoring");
  await expect(output).not.toContainText("ZeroDivisionError");
  expect(await harness.scoreCalls()).toBe(1);

  await harness.restart();
  requestPolicy.refreshOrigin();
  await page.reload();
  await page.getByRole("button", { name: "View final session" }).click();
  await expect(page.getByText("Submitted", { exact: true })).toBeVisible();
  const reconnectedOutput = page.getByTestId("output-drawer");
  await expect(reconnectedOutput).toContainText(
    "The candidate solution did not pass this practice level.",
  );
  await expect(reconnectedOutput).toContainText(
    "The local practice check could not be completed.",
  );
  await expect(reconnectedOutput).not.toContainText("SCORER_INTERNAL_SENTINEL");
  await expect(reconnectedOutput).not.toContainText(".scoring");
  await expect(reconnectedOutput).not.toContainText("ZeroDivisionError");
  expect(await harness.scoreCalls()).toBe(1);
  expect(started.data.session.attempt_id).toBe(
    await page.locator(".assessment-shell").getAttribute("data-attempt-id"),
  );
});

async function startAttempt(page) {
  const response = page.waitForResponse((item) =>
    new URL(item.url()).pathname === "/api/attempts" &&
    item.request().method() === "POST");
  await page.getByRole("button", { name: "Start practice" }).click();
  await page.getByRole("button", { name: "Confirm and start" }).click();
  await expect(page.getByTestId("editor-pane")).toBeVisible();
  return (await response).json();
}

async function replaceSource(page, content) {
  await page.locator(".editor").click();
  await page.keyboard.press("Meta+A");
  await page.keyboard.insertText(content);
}

async function retrySubmit(page, server, attemptId, source) {
  return page.evaluate(async ({ attemptId, source, token }) => {
    const response = await fetch(`/api/submit?attempt_id=${attemptId}`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "If-Match": source.etag,
        "X-Simulator-Token": token,
      },
      body: JSON.stringify({ content: source.content }),
    });
    return { status: response.status, document: await response.json() };
  }, { attemptId, source, token: server.token });
}
