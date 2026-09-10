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

test("cancels delayed saves and locks source actions after terminal time", async ({ page }) => {
  requestPolicy.expectFailedRequest({
    method: "PUT",
    path: "/api/source",
    count: 1,
  });
  const started = await startAttempt(page);
  const attemptId = started.data.session.attempt_id;
  await append(page, "\n# persisted before terminal test");
  await expect(saveStatus(page)).toHaveText("Saved snapshot");
  const sourceHeld = requestPolicy.hold("/api/source");
  const requests = trackPuts(page);
  await append(page, "\n# delayed terminal edit");
  await expect.poll(() => requests.length).toBe(1);
  await append(page, "\n# queued terminal edit");

  requestPolicy.intercept(
    `/api/time?attempt_id=${attemptId}`,
    timeResponse({ ...started.data.session, status: "expired" }, started.data.time),
  );
  await page.waitForResponse((response) =>
    new URL(response.url()).pathname === "/api/time" &&
    response.request().method() === "GET",
  );
  await expect(page.getByText("Expired", { exact: true })).toBeVisible();
  await expect(page.getByRole("button", { name: "Save changes" })).toBeDisabled();
  await expect(page.getByRole("button", { name: "Reset" })).toBeDisabled();
  await expect(page.locator(".fallback")).toBeVisible();
  await expect(page.locator(".fallback")).toHaveAttribute("readonly", "");
  await expect(page.locator(".fallback")).toHaveValue(
    `${started.data.source.content}\n# persisted before terminal test`,
  );

  await page.getByRole("tab", { name: "History" }).click();
  await expect(page.getByRole("button", { name: "Restore this version" }))
    .toBeDisabled();
  await sourceHeld;
  requestPolicy.release("/api/source");
  await expect.poll(() => requests.length).toBe(1);
  expect(requests).toHaveLength(1);
  expect((await source(harness, attemptId)).content)
    .toContain("# persisted before terminal test");
  expect((await source(harness, attemptId)).content)
    .not.toContain("delayed terminal edit");
});

test("renders the saved source directly when expiry makes the attempt terminal", async ({ page }) => {
  const started = await startAttempt(page);
  const attemptId = started.data.session.attempt_id;
  await append(page, "\n# authoritative expiry fallback");
  await expect(saveStatus(page)).toHaveText("Saved snapshot");
  const sourceGets = trackSourceGets(page);
  const timeResponsePromise = page.waitForResponse((response) =>
    new URL(response.url()).pathname === "/api/time" &&
    response.request().method() === "GET",
  );
  requestPolicy.intercept(
    `/api/time?attempt_id=${attemptId}`,
    timeResponse({ ...started.data.session, status: "expired" }, started.data.time),
  );
  await timeResponsePromise;
  await expect(page.getByText("Expired", { exact: true })).toBeVisible();
  await expect(page.locator(".fallback")).toBeVisible();
  await expect(page.locator(".fallback")).toHaveAttribute("readonly", "");
  await expect(page.locator(".fallback")).toHaveValue(
    `${started.data.source.content}\n# authoritative expiry fallback`,
  );
  await expect(page.locator(".error-message")).toHaveCount(0);
  for (const name of ["Save changes", "Run Tests", "Reset", "Submit"]) {
    await expect(page.getByRole("button", { name })).toBeDisabled();
  }
  expect(sourceGets).toHaveLength(0);
});

test("reconnects to a terminal attempt with its authoritative source", async ({ page }) => {
  const started = await startAttempt(page);
  const attemptId = started.data.session.attempt_id;
  await append(page, "\n# terminal reconnect source");
  await expect(saveStatus(page)).toHaveText("Saved snapshot");
  requestPolicy.intercept(
    `/api/time?attempt_id=${attemptId}`,
    timeResponse({ ...started.data.session, status: "expired" }, started.data.time),
  );
  await page.reload();
  await page.getByRole("button", { name: "Reconnect to active session" }).click();
  await expect(page.getByText("Expired", { exact: true })).toBeVisible();
  await expect(page.locator(".fallback")).toBeVisible();
  await expect(page.locator(".fallback")).toHaveValue(
    `${started.data.source.content}\n# terminal reconnect source`,
  );
  await expect(page.locator(".fallback")).toHaveAttribute("readonly", "");
});

async function startAttempt(page) {
  await page.goto(`${harness.origin}/#token=${harness.token}`);
  await page.getByRole("button", { name: "Start practice" }).click();
  const responsePromise = page.waitForResponse((response) =>
    new URL(response.url()).pathname === "/api/attempts" &&
    response.request().method() === "POST",
  );
  await page.getByRole("button", { name: "Confirm and start" }).click();
  const started = await (await responsePromise).json();
  await expect(page.getByText("Python editor ready.", { exact: false })).toBeVisible();
  return started;
}

async function append(page, value) {
  await page.locator(".monaco-editor").click();
  await page.keyboard.press("Control+End");
  await page.keyboard.type(value);
}

function saveStatus(page) {
  return page.locator(".assessment-header .header-status").nth(1).locator("strong");
}

function trackPuts(page) {
  const requests = [];
  page.on("request", (request) => {
    if (request.method() === "PUT" &&
        new URL(request.url()).pathname === "/api/source") {
      requests.push(request);
    }
  });
  return requests;
}

function trackSourceGets(page) {
  const requests = [];
  page.on("request", (request) => {
    const url = new URL(request.url());
    if (request.method() === "GET" && url.pathname === "/api/source") {
      requests.push(request);
    }
  });
  return requests;
}

async function source(server, attemptId) {
  const response = await fetch(
    `${server.origin}/api/source?attempt_id=${encodeURIComponent(attemptId)}`,
    { headers: { "X-Simulator-Token": server.token } },
  );
  return (await response.json()).data;
}
