import { expect, test } from "@playwright/test";
import {
  installOfflineRequestPolicy,
  startFixtureServer,
} from "./browser_harness.mjs";
import { EntryPage } from "./pages/entry_page.mjs";

// Library, route model and metadata-only navigation (D004, 005/01/01). Every
// journey runs against the synthetic fixture server; the packaged original
// exercises come from the source checkout's resources directory.

let harness;
let requestPolicy;

test.beforeEach(async () => {
  harness = await startFixtureServer();
});

test.beforeEach(async ({ page }) => {
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

const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/u;

function trackMutations(page) {
  const mutations = [];
  page.on("request", (request) => {
    if (["POST", "PUT", "DELETE"].includes(request.method())) {
      mutations.push(`${request.method()} ${new URL(request.url()).pathname}`);
    }
  });
  return mutations;
}

function sourceRequests(records) {
  return records.filter(({ url }) => new URL(url).pathname.startsWith("/api/source"));
}

test("library lists catalog readiness and starts only the selected exercise after confirmation", async ({ page }) => {
  const entry = new EntryPage(page);
  const mutations = trackMutations(page);
  await page.goto(`${harness.origin}/#token=${harness.token}`);
  await entry.expectLoaded();
  const heading = page.getByRole("heading", { name: "Practice library", level: 1 });
  await expect(heading).toBeFocused();
  await expect(page.getByRole("button", { name: "History" })).toBeVisible();
  const cards = page.locator(".exercise-card");
  await expect(cards).toHaveCount(3);
  const card = (name) => cards.filter({ has: page.getByRole("heading", { name, exact: true }) });
  for (const name of ["File Storage", "In-Memory Records", "Account Ledger"]) {
    await expect(card(name).locator(".readiness")).toHaveText("Ready");
    await expect(card(name).getByRole("button", { name: `Select ${name}` })).toBeEnabled();
  }
  // The bootstrap's primary exercise is listed and selected first.
  await expect(cards.first()).toHaveAttribute("data-assessment-id", "file_storage");
  await expect(cards.first()).toHaveAttribute("data-selected", "true");
  await expect(card("File Storage").locator(".exercise-meta"))
    .toHaveText(/^Content upstream-[0-9a-f]+ · Locally prepared exercise$/u);
  await expect(card("In-Memory Records").locator(".exercise-meta"))
    .toHaveText("Content records-1 · Packaged original exercise");
  await expect(card("Account Ledger").locator(".exercise-meta"))
    .toHaveText("Content ledger-1 · Packaged original exercise");
  const mainText = await page.getByRole("main").innerText();
  expect(mainText).not.toMatch(/\/Users|\/tmp|\.cache|sha256/u);

  await page.getByRole("button", { name: "Select Account Ledger" }).click();
  await expect(page.locator(".selected-exercise")).toHaveText("Selected exercise: Account Ledger");
  await expect(page.getByRole("status")).toContainText("Account Ledger selected");
  await expect(page.getByRole("heading", { name: "Four-level outline" })).toBeVisible();
  await expect(page.locator(".exercise-outline p")).toContainText("Account Ledger");
  expect(mutations).toEqual([]);

  await entry.choose("drill");
  await entry.openStartDialog();
  await expect(page.getByRole("dialog", { name: "Confirm start" }))
    .toContainText("attempt of Account Ledger");
  expect(mutations).toEqual([]);
  await entry.cancelStart();
  await expect(page.getByRole("button", { name: "Start practice" })).toBeFocused();
  expect(mutations).toEqual([]);

  await entry.openStartDialog();
  const started = entry.confirmStartResponse();
  await entry.confirmStart();
  const response = await started;
  expect(response.request().postDataJSON()).toEqual({
    assessment: "account_ledger",
    mode: "drill",
    drill_duration_seconds: 1800,
  });
  const attemptId = (await response.json()).data.session.attempt_id;
  expect(attemptId).toMatch(UUID);
  await expect(page.locator(".status")).toHaveText(/Python editor ready/);
  await expect(page.getByRole("heading", { name: "Account Ledger", level: 1 })).toBeVisible();
  await expect(page.locator("main")).toHaveAttribute("data-attempt-id", attemptId);
  expect(new URL(page.url()).pathname).toBe(`/attempt/${attemptId}`);
  expect(mutations).toEqual(["POST /api/attempts"]);
});

test("back and forward reconstruct library and attempt without creating attempts", async ({ page }) => {
  const entry = new EntryPage(page);
  await page.goto(`${harness.origin}/#token=${harness.token}`);
  await entry.expectLoaded();
  await entry.start("full");
  await expect(page.locator(".status")).toHaveText(/Python editor ready/);
  const attemptId = await page.locator("main").getAttribute("data-attempt-id");
  const deadline = await page.locator(".server-deadline").innerText();
  const mutations = trackMutations(page);

  await page.goBack();
  await expect(page.getByRole("heading", { name: "Practice library", level: 1 })).toBeFocused();
  expect(new URL(page.url()).pathname).toBe("/");
  await expect(page.getByRole("main")).toHaveAttribute("data-active-attempt-id", attemptId);
  const summary = page.locator(".active-session");
  await expect(summary).toContainText("Active");
  await expect(summary).toContainText("File Storage");
  await expect(page.getByRole("status")).toContainText("An existing session is available to reconnect.");
  await entry.expectReconnectAction();

  await page.goForward();
  // Forward lands on the attempt route's continue screen: metadata only,
  // no source request, and the editor opens only after the explicit action.
  const continueHeading = page.getByRole("heading", { name: "File Storage", level: 1 });
  await expect(continueHeading).toBeFocused();
  await expect(page.locator("main.attempt-entry")).toHaveAttribute("data-active-attempt-id", attemptId);
  await expect(page.locator(".session-summary")).toContainText(deadline.replace("Server deadline: ", ""));
  expect(new URL(page.url()).pathname).toBe(`/attempt/${attemptId}`);
  const sourceBefore = sourceRequests(requestPolicy.requestRecords()).length;
  await page.getByRole("button", { name: "Reconnect to active session" }).click();
  await expect(page.locator(".status")).toHaveText(/Python editor ready/);
  await expect(page.locator("main")).toHaveAttribute("data-attempt-id", attemptId);
  await expect(page.locator(".server-deadline")).toHaveText(deadline);
  expect(sourceRequests(requestPolicy.requestRecords()).length).toBe(sourceBefore + 1);

  await page.goBack();
  await entry.expectReconnectAction();
  await page.getByRole("button", { name: "Reconnect to active session" }).click();
  await expect(page.locator("main")).toHaveAttribute("data-attempt-id", attemptId);
  expect(new URL(page.url()).pathname).toBe(`/attempt/${attemptId}`);
  expect(mutations).toEqual([]);
});

test("a direct attempt address shows the continue screen and never starts a timer", async ({ page }) => {
  const entry = new EntryPage(page);
  await page.goto(`${harness.origin}/#token=${harness.token}`);
  await entry.expectLoaded();
  await entry.start("full");
  await expect(page.locator(".status")).toHaveText(/Python editor ready/);
  const attemptId = await page.locator("main").getAttribute("data-attempt-id");
  const deadline = await page.locator(".server-deadline").innerText();
  const mutations = trackMutations(page);
  const sourceBefore = sourceRequests(requestPolicy.requestRecords()).length;

  await page.goto(`${harness.origin}/attempt/${attemptId}`);
  await expect(page.getByRole("heading", { name: "File Storage", level: 1 })).toBeFocused();
  await expect(page.getByRole("status")).toContainText("An existing session is available to reconnect.");
  await expect(page.locator(".session-summary")).toContainText("Active");
  await expect(page.getByRole("button", { name: "Back to library" })).toBeVisible();
  expect(sourceRequests(requestPolicy.requestRecords()).length).toBe(sourceBefore);
  await page.getByRole("button", { name: "Reconnect to active session" }).click();
  await expect(page.locator(".status")).toHaveText(/Python editor ready/);
  await expect(page.locator("main")).toHaveAttribute("data-attempt-id", attemptId);
  await expect(page.locator(".server-deadline")).toHaveText(deadline);
  await expect(page.locator(".assessment-header .header-status").first().locator("strong"))
    .toHaveText("Active");
  expect(mutations).toEqual([]);
  const bootstrap = await page.evaluate(async () => {
    const response = await fetch("/api/bootstrap", {
      headers: { "X-Simulator-Token": window.sessionStorage.getItem("simulator-token") },
    });
    return (await response.json()).data.session;
  });
  expect(bootstrap.attempt_id).toBe(attemptId);
  expect(bootstrap.deadline_at).toBe(deadline.replace("Server deadline: ", ""));
});

test("unknown attempt addresses and unknown routes recover back to the library", async ({ page }) => {
  const entry = new EntryPage(page);
  await page.goto(`${harness.origin}/#token=${harness.token}`);
  await entry.expectLoaded();
  const mutations = trackMutations(page);
  const missing = "0f1c2d3e-4a5b-4c6d-8e9f-0a1b2c3d4e5f";
  requestPolicy.expectHttpError({
    method: "GET",
    path: `/api/time?attempt_id=${missing}`,
    status: 404,
  });
  await page.goto(`${harness.origin}/attempt/${missing}`);
  await expect(page.getByRole("heading", { name: "Attempt not found", level: 1 })).toBeFocused();
  await expect(page.getByRole("alert")).toContainText("No attempt with this address is stored locally");
  await page.getByRole("button", { name: "Back to library" }).click();
  await entry.expectLoaded();
  expect(new URL(page.url()).pathname).toBe("/");

  await page.goto(`${harness.origin}/attempt/not-an-attempt`);
  await expect(page.getByRole("heading", { name: "Page not found", level: 1 })).toBeFocused();
  await expect(page.getByRole("alert")).toContainText("does not match a library, attempt, history, or review screen");
  await page.getByRole("button", { name: "Back to library" }).click();
  await entry.expectLoaded();
  expect(new URL(page.url()).pathname).toBe("/");
  expect(mutations).toEqual([]);
  expect(sourceRequests(requestPolicy.requestRecords())).toEqual([]);
});

test("history and review routes are metadata-only shells that never select an attempt", async ({ page }) => {
  const entry = new EntryPage(page);
  await page.goto(`${harness.origin}/#token=${harness.token}`);
  await entry.expectLoaded();
  const mutations = trackMutations(page);
  await page.getByRole("button", { name: "History" }).click();
  await expect(page.getByRole("heading", { name: "Attempt history", level: 1 })).toBeFocused();
  expect(new URL(page.url()).pathname).toBe("/history");
  await page.goBack();
  await entry.expectLoaded();
  await page.goForward();
  await expect(page.getByRole("heading", { name: "Attempt history", level: 1 })).toBeVisible();

  const reviewed = "0f1c2d3e-4a5b-4c6d-8e9f-0a1b2c3d4e5f";
  await page.goto(`${harness.origin}/history/review/${reviewed}`);
  await expect(page.getByRole("heading", { name: "Attempt review", level: 1 })).toBeFocused();
  await expect(page.getByRole("main")).toHaveAttribute("data-review-attempt-id", reviewed);
  await page.getByRole("button", { name: "Back to history" }).click();
  await expect(page.getByRole("heading", { name: "Attempt history", level: 1 })).toBeFocused();
  await page.getByRole("button", { name: "Back to library" }).click();
  await entry.expectLoaded();
  await expect(page.getByRole("main")).not.toHaveAttribute("data-active-attempt-id", /.+/u);
  expect(mutations).toEqual([]);
  expect(sourceRequests(requestPolicy.requestRecords())).toEqual([]);
});

test("a failed bootstrap on the library route offers a reload and leaks nothing", async ({ page }) => {
  requestPolicy.intercept("/api/bootstrap", {
    status: 503,
    contentType: "application/json",
    body: JSON.stringify({
      schema_version: "web/v1", ok: false,
      error: { code: "temporary_failure", message: "fixture at /Users/private/.cache is busy" },
    }),
  });
  requestPolicy.expectHttpError({ method: "GET", path: "/api/bootstrap", status: 503 });
  await page.goto(`${harness.origin}/#token=${harness.token}`);
  await expect(page.getByRole("heading", { name: "Assessment unavailable", level: 1 })).toBeFocused();
  const alert = page.getByRole("alert");
  await expect(alert).toContainText("Reload the local simulator");
  expect(await alert.innerText()).not.toContain("/Users/private");
  requestPolicy.clearIntercept("/api/bootstrap");
  await page.getByRole("button", { name: "Reload local simulator" }).click();
  await new EntryPage(page).expectLoaded();
});
