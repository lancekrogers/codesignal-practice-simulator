import { readFile } from "node:fs/promises";
import { join } from "node:path";
import { expect, test } from "@playwright/test";
import {
  installOfflineRequestPolicy,
  startFixtureServer,
} from "./browser_harness.mjs";
import { EntryPage } from "./pages/entry_page.mjs";

// Read-only review screen (D002/D004, 005/02/02). Attempts are prepared through
// the public API from the page context; the review itself must never mutate,
// rescore or reselect anything, and Retry must never displace a live attempt
// without the explicit choice.

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

const SUBMITTED_SOURCE = "def evaluate(group):\n    return 'ok'  # reviewed submission\n";

test("reviews a submission while another attempt is live and resolves retry explicitly", async ({ page }) => {
  await openLibrary(page);
  await harness.setClock("2030-01-01T00:01:00+00:00");
  const reviewed = await submitAttemptViaApi(page, "file_storage", SUBMITTED_SOURCE);
  await harness.setClock("2030-01-01T00:02:00+00:00");
  const live = await startAttemptViaApi(page, "account_ledger");
  const liveSession = await readSession(live);
  const reviewedBytes = await readFile(join(harness.workspaceRoot, "attempts", reviewed, "review.json"));
  const pointerBefore = await readActivePointer();
  const requests = trackRequests(page);

  await page.goto(`${harness.origin}/history/review/${reviewed}`);
  const heading = page.getByRole("heading", { name: "Attempt review: File Storage", level: 1 });
  await expect(heading).toBeFocused();
  await expect(page.getByRole("main")).toHaveAttribute("data-review-attempt-id", reviewed);
  await expect(page.getByRole("status")).toContainText("Read-only review of a submitted attempt");
  const summary = page.locator(".session-summary");
  await expect(summary).toContainText("Submitted");
  await expect(summary).toContainText("(pinned)");
  await expect(summary).toContainText("full · 90 min");
  await expect(summary).toContainText("session/v2");
  await expect(page.getByRole("heading", { name: "Final result" })).toBeVisible();
  await expect(page.locator(".review-result")).toContainText(/Passed \d of 4 levels/u);
  await expect(page.getByRole("heading", { name: "Submitted source" })).toBeVisible();
  const source = page.getByRole("textbox", { name: "Submitted source, read-only" });
  await expect(source).toHaveValue(SUBMITTED_SOURCE);
  await expect(source).toHaveAttribute("readonly", "");
  await expect(page.locator(".review-source .exercise-meta")).toContainText(/sha256 [0-9a-f]{64}/u);
  await source.click();
  await page.keyboard.type("# tamper");
  await expect(source).toHaveValue(SUBMITTED_SOURCE);
  await expect(page.locator(".review-legacy")).toHaveCount(0);
  for (const name of ["Submit", "Run Tests", "Save changes"]) {
    await expect(page.getByRole("button", { name })).toHaveCount(0);
  }
  expect(requests.filter((r) => r.method !== "GET")).toEqual([]);
  expect(requests.map((r) => r.path)).toEqual(
    expect.arrayContaining(["/api/bootstrap", `/api/attempts/${reviewed}/review`]),
  );
  expect(requests.some((r) => r.path === "/api/source" || r.path === "/api/test" || r.path === "/api/submit")).toBe(false);
  expect(await readActivePointer()).toBe(pointerBefore);
  expect(await readFile(join(harness.workspaceRoot, "attempts", reviewed, "review.json"))).toEqual(reviewedBytes);

  // Retry with a live attempt: the conflict dialog offers resume or end-and-start.
  await page.getByRole("button", { name: "Retry this exercise" }).click();
  const conflict = page.getByRole("dialog", { name: "An attempt is already in progress" });
  await expect(conflict).toContainText("Nothing happens until you choose");
  await expect(conflict.locator(".warning")).toBeHidden();
  await conflict.getByRole("button", { name: "Cancel" }).click();
  await expect(conflict).toBeHidden();
  await expect(page.getByRole("button", { name: "Retry this exercise" })).toBeFocused();
  expect(requests.filter((r) => r.method !== "GET")).toEqual([]);
  expect(await readActivePointer()).toBe(pointerBefore);

  await page.getByRole("button", { name: "Retry this exercise" }).click();
  await conflict.getByRole("button", { name: "Resume active attempt" }).click();
  await expect(page.locator(".status")).toHaveText(/Python editor ready/);
  await expect(page.locator("main")).toHaveAttribute("data-attempt-id", live);
  expect(requests.filter((r) => r.method !== "GET")).toEqual([]);

  await page.goto(`${harness.origin}/history/review/${reviewed}`);
  await expect(heading).toBeFocused();
  await page.getByRole("button", { name: "Retry this exercise" }).click();
  const started = page.waitForResponse((response) =>
    new URL(response.url()).pathname === "/api/attempts" && response.request().method() === "POST",
  );
  await conflict.getByRole("button", { name: "End it and start a new attempt" }).click();
  const response = await started;
  expect(response.status()).toBe(201);
  expect(response.request().postDataJSON()).toEqual({ assessment: "file_storage", mode: "full" });
  const replacement = (await response.json()).data.session.attempt_id;
  await expect(page.locator(".status")).toHaveText(/Python editor ready/);
  await expect(page.locator("main")).toHaveAttribute("data-attempt-id", replacement);
  expect(requests.filter((r) => r.method !== "GET").map((r) => r.path)).toEqual([
    `/api/attempts/${live}/abandon`,
    "/api/attempts",
  ]);
  const endedLive = await readSession(live);
  expect(endedLive.status).toBe("abandoned");
  expect(endedLive.revision).toBeGreaterThan(liveSession.revision);
  expect(await readFile(join(harness.workspaceRoot, "attempts", reviewed, "review.json"))).toEqual(reviewedBytes);
  expect((await readSession(reviewed)).status).toBe("submitted");
});

test("an ended attempt shows its saved work and last practice result, never a final result", async ({ page }) => {
  await openLibrary(page);
  const attemptId = await startAttemptViaApi(page, "file_storage");
  const saved = "def evaluate(group):\n    return 'ok'  # saved before ending\n";
  const etag = await saveSourceViaApi(page, attemptId, saved);
  const tested = await api(page, "POST", `/api/test?attempt_id=${attemptId}`, { content: saved }, etag);
  expect(tested.status).toBe(200);
  await endAttemptViaApi(page, attemptId);
  const requests = trackRequests(page);

  await page.goto(`${harness.origin}/history/review/${attemptId}`);
  await expect(page.getByRole("heading", { name: "Attempt review: File Storage", level: 1 })).toBeFocused();
  await expect(page.getByRole("status")).toContainText("Read-only review of an ended attempt");
  await expect(page.locator(".session-summary")).toContainText("Ended");
  await expect(page.getByRole("heading", { name: "Last practice result" })).toBeVisible();
  await expect(page.locator(".review-result")).toContainText("ended without a submission");
  await expect(page.locator(".review-result")).toContainText(/passed \d of 4 levels; this is not a final result/u);
  await expect(page.getByText("Final result", { exact: true })).toHaveCount(0);
  await expect(page.getByRole("heading", { name: "Saved work (not a submission)" })).toBeVisible();
  const work = page.getByRole("textbox", { name: "Saved work, read-only" });
  await expect(work).toHaveValue(saved);
  await expect(work).toHaveAttribute("readonly", "");
  await expect(page.getByRole("button", { name: "Retry this exercise" })).toBeEnabled();
  expect(requests.filter((r) => r.method !== "GET")).toEqual([]);
  expect(requests.map((r) => r.path)).toEqual(expect.arrayContaining([
    `/api/attempts/${attemptId}/review`,
    "/api/source",
  ]));

  // No live attempt: Retry confirms and starts directly, keeping the format.
  await page.getByRole("button", { name: "Retry this exercise" }).click();
  const confirm = page.getByRole("dialog", { name: "Start a new attempt?" });
  await expect(confirm).toContainText("new full attempt of File Storage");
  await expect(confirm.locator(".warning")).toBeHidden();
  const started = page.waitForResponse((response) =>
    new URL(response.url()).pathname === "/api/attempts" && response.request().method() === "POST",
  );
  await confirm.getByRole("button", { name: "Confirm and start" }).click();
  expect((await started).status()).toBe(201);
  await expect(page.locator(".status")).toHaveText(/Python editor ready/);
  await expect(page.locator("main")).not.toHaveAttribute("data-attempt-id", attemptId);
  expect(requests.filter((r) => r.method !== "GET").map((r) => r.path)).toEqual(["/api/attempts"]);
});

test("legacy records are labelled and a version change is announced before retry", async ({ page }) => {
  await openLibrary(page);
  const reviewed = await submitAttemptViaApi(page, "file_storage", SUBMITTED_SOURCE);
  const reviewPath = `/api/attempts/${reviewed}/review`;
  const legacy = {
    schema_version: "web/v1",
    ok: true,
    data: {
      attempt_id: reviewed,
      schema_version: "session/v1",
      status: "submitted",
      assessment: {
        assessment_id: "file_storage",
        display_name: "File Storage",
        level_count: 4,
        content_identity: "unavailable",
        content_version: null,
        content_digest: null,
      },
      profile: { mode: "drill", profile_id: "drill-30m", duration_seconds: 1800 },
      started_at: "2029-12-31T23:00:00+00:00",
      deadline_at: "2029-12-31T23:30:00+00:00",
      submitted_at: "2029-12-31T23:20:00+00:00",
      score: {
        passed_levels: 2,
        highest_contiguous_level: 2,
        levels: [
          { level: 1, outcome: "passed" }, { level: 2, outcome: "passed" },
          { level: 3, outcome: "failed" }, { level: 4, outcome: "error" },
        ],
      },
      practice_score: null,
      source_binding: "not_captured",
      source: {
        filename: "simulation.py",
        sha256: "a".repeat(64),
        content: "# current file at /Users/private/elsewhere is not shown as a path\n",
        binding: "legacy_unbound",
      },
      issues: ["submitted_source_binding_unavailable", "content_identity_unavailable"],
    },
  };
  requestPolicy.intercept(reviewPath, {
    status: 200, contentType: "application/json", body: JSON.stringify(legacy),
  });
  await page.route("**/api/bootstrap", async (route) => {
    const response = await route.fetch();
    const body = await response.json();
    for (const entry of body.data.catalog) {
      if (entry.assessment_id === "file_storage") entry.content_version = "upstream-newer";
    }
    await route.fulfill({ response, body: JSON.stringify(body) });
  });

  await page.goto(`${harness.origin}/history/review/${reviewed}`);
  await expect(page.getByRole("heading", { name: "Attempt review: File Storage", level: 1 })).toBeFocused();
  const banners = page.locator(".review-legacy");
  await expect(banners).toHaveCount(2);
  await expect(banners.nth(0)).toContainText("Submitted-source binding unavailable");
  await expect(banners.nth(0)).toContainText("not proven submitted bytes");
  await expect(banners.nth(1)).toContainText("Content identity unavailable");
  await expect(page.locator(".session-summary")).toContainText("unavailable (legacy record)");
  await expect(page.locator(".session-summary")).toContainText("session/v1");
  await expect(page.locator(".review-result")).toContainText("Passed 2 of 4 levels.");
  await expect(page.getByRole("heading", { name: "Current file (not proven submitted)" })).toBeVisible();
  await expect(page.getByRole("textbox", { name: "Legacy source, read-only" })).toHaveValue(legacy.data.source.content);
  await expect(page.locator(".review-source .exercise-meta")).toContainText(`sha256 ${"a".repeat(64)}`);

  await page.getByRole("button", { name: "Retry this exercise" }).click();
  const confirm = page.getByRole("dialog", { name: "Start a new attempt?" });
  await expect(confirm).toContainText("new drill attempt of File Storage");
  await expect(confirm.locator(".warning")).toBeVisible();
  await expect(confirm.locator(".warning")).toContainText("content version is not recorded (legacy record)");
  await expect(confirm.locator(".warning")).toContainText("upstream-newer");
  await confirm.getByRole("button", { name: "Cancel" }).click();
  await expect(confirm).toBeHidden();

  // A pinned record whose version differs from the library is announced too.
  legacy.data.schema_version = "session/v2";
  legacy.data.assessment.content_identity = "pinned";
  legacy.data.assessment.content_version = "upstream-older";
  legacy.data.assessment.content_digest = "b".repeat(64);
  legacy.data.issues = ["submitted_source_binding_unavailable"];
  requestPolicy.intercept(reviewPath, {
    status: 200, contentType: "application/json", body: JSON.stringify(legacy),
  });
  await page.goto(`${harness.origin}/history/review/${reviewed}`);
  await expect(banners).toHaveCount(1);
  await expect(page.locator(".session-summary")).toContainText("upstream-older (pinned)");
  await page.getByRole("button", { name: "Retry this exercise" }).click();
  await expect(confirm.locator(".warning")).toContainText(
    "current library version upstream-newer differs from the version this attempt used (upstream-older)",
  );
  await confirm.getByRole("button", { name: "Cancel" }).click();
});

test("a removed catalog version keeps the stored review readable with retry blocked", async ({ page }) => {
  await openLibrary(page);
  const reviewed = await submitAttemptViaApi(page, "account_ledger", SUBMITTED_SOURCE);
  await page.route("**/api/bootstrap", async (route) => {
    const response = await route.fetch();
    const body = await response.json();
    body.data.catalog = body.data.catalog.map((entry) =>
      entry.assessment_id === "in_memory_records"
        ? { ...entry, available: false, setup: "packaged_content_invalid", setup_message: "Packaged content failed validation; reinstall the package." }
        : entry,
    ).filter((entry) => entry.assessment_id !== "account_ledger");
    await route.fulfill({ response, body: JSON.stringify(body) });
  });
  await page.goto(`${harness.origin}/history/review/${reviewed}`);
  await expect(page.getByRole("heading", { name: "Attempt review: Account Ledger", level: 1 })).toBeFocused();
  await expect(page.locator(".session-summary")).toContainText("ledger-1 (pinned)");
  await expect(page.locator(".review-result")).toContainText(/Passed \d of 4 levels/u);
  const retry = page.getByRole("button", { name: "Retry this exercise" });
  await expect(retry).toBeDisabled();
  await expect(retry).toHaveAccessibleDescription(/not installed in the current library/u);

  // Setup-required exercises are blocked with the catalog's safe setup message.
  const records = await submitAttemptViaApi(page, "in_memory_records", SUBMITTED_SOURCE);
  await page.goto(`${harness.origin}/history/review/${records}`);
  await expect(page.getByRole("button", { name: "Retry this exercise" })).toBeDisabled();
  await expect(page.getByRole("button", { name: "Retry this exercise" }))
    .toHaveAccessibleDescription(/Packaged content failed validation/u);
});

test("missing, pending and tampered reviews surface errors instead of an empty success", async ({ page }) => {
  await openLibrary(page);
  const reviewed = await submitAttemptViaApi(page, "file_storage", SUBMITTED_SOURCE);
  const missing = "0f1c2d3e-4a5b-4c6d-8e9f-0a1b2c3d4e5f";
  requestPolicy.expectHttpError({ method: "GET", path: `/api/attempts/${missing}/review`, status: 404 });
  await page.goto(`${harness.origin}/history/review/${missing}`);
  await expect(page.getByRole("heading", { name: "Attempt review", level: 1 })).toBeFocused();
  await expect(page.getByRole("heading", { name: "Attempt not found" })).toBeVisible();
  await expect(page.getByRole("alert")).toContainText("No attempt with this address is stored locally");
  await expect(page.getByRole("button", { name: "Retry loading" })).toHaveCount(0);
  await expect(page.locator(".session-summary")).toHaveCount(0);
  await page.getByRole("button", { name: "Back to history" }).click();
  await expect(page.getByRole("heading", { name: "Attempt history", level: 1 })).toBeFocused();

  const reviewPath = `/api/attempts/${reviewed}/review`;
  requestPolicy.intercept(reviewPath, {
    status: 503, contentType: "application/json",
    body: JSON.stringify({
      schema_version: "web/v1", ok: false,
      error: { code: "review_pending", message: "finalizing at /Users/private/attempts" },
    }),
  });
  requestPolicy.expectHttpError({ method: "GET", path: reviewPath, status: 503 });
  await page.goto(`${harness.origin}/history/review/${reviewed}`);
  await expect(page.getByRole("alert")).toContainText("still being finalized");
  expect(await page.getByRole("alert").innerText()).not.toContain("/Users/private");
  await expect(page.locator(".session-summary")).toHaveCount(0);

  // A tampered payload (score as text, source binding contradicting itself) is an error.
  requestPolicy.intercept(reviewPath, {
    status: 200, contentType: "application/json",
    body: JSON.stringify({
      schema_version: "web/v1", ok: true,
      data: {
        attempt_id: reviewed, schema_version: "session/v2", status: "submitted",
        assessment: { assessment_id: "file_storage", display_name: "File Storage", level_count: 4, content_identity: "pinned", content_version: "x", content_digest: "y" },
        profile: { mode: "full", profile_id: "full-90m", duration_seconds: 5400 },
        started_at: "2030-01-01T00:00:00+00:00", deadline_at: "2030-01-01T01:30:00+00:00", submitted_at: "2030-01-01T00:10:00+00:00",
        score: "4/4", practice_score: null, source_binding: "not_applicable",
        source: { filename: "simulation.py", sha256: "c".repeat(64), content: "x", binding: "captured" },
        issues: [],
      },
    }),
  });
  await page.getByRole("button", { name: "Retry loading" }).click();
  await expect(page.getByRole("alert")).toContainText("could not be read safely");
  await expect(page.getByRole("alert")).toContainText("nothing was changed");
  await expect(page.locator(".session-summary")).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Retry this exercise" })).toHaveCount(0);

  // A "captured" binding whose source view is only the unbound legacy file
  // must never be shown as exact scored bytes: it is rejected as well.
  requestPolicy.intercept(reviewPath, {
    status: 200, contentType: "application/json",
    body: JSON.stringify({
      schema_version: "web/v1", ok: true,
      data: {
        attempt_id: reviewed, schema_version: "session/v2", status: "submitted",
        assessment: { assessment_id: "file_storage", display_name: "File Storage", level_count: 4, content_identity: "pinned", content_version: "x", content_digest: "y" },
        profile: { mode: "full", profile_id: "full-90m", duration_seconds: 5400 },
        started_at: "2030-01-01T00:00:00+00:00", deadline_at: "2030-01-01T01:30:00+00:00", submitted_at: "2030-01-01T00:10:00+00:00",
        score: { passed_levels: 4, highest_contiguous_level: 4, levels: [{ level: 1, outcome: "passed" }] },
        practice_score: null, source_binding: "captured",
        source: { filename: "simulation.py", sha256: "d".repeat(64), content: "# unproven\n", binding: "legacy_unbound" },
        issues: [],
      },
    }),
  });
  await page.getByRole("button", { name: "Retry loading" }).click();
  await expect(page.getByRole("alert")).toContainText("could not be read safely");
  await expect(page.getByText("Submitted source")).toHaveCount(0);
  await expect(page.getByRole("textbox")).toHaveCount(0);

  requestPolicy.clearIntercept(reviewPath);
  await page.getByRole("button", { name: "Retry loading" }).click();
  await expect(page.getByRole("heading", { name: "Final result" })).toBeVisible();
  await expect(page.getByRole("textbox", { name: "Submitted source, read-only" })).toHaveValue(SUBMITTED_SOURCE);
});

async function openLibrary(page) {
  await page.goto(`${harness.origin}/#token=${harness.token}`);
  await new EntryPage(page).expectLoaded();
}

function trackRequests(page) {
  const requests = [];
  page.on("request", (request) => {
    const url = new URL(request.url());
    if (url.pathname.startsWith("/api/")) {
      requests.push({ method: request.method(), path: url.pathname });
    }
  });
  return requests;
}

async function api(page, method, path, body, ifMatch) {
  return page.evaluate(async ({ method, path, body, ifMatch }) => {
    const response = await fetch(path, {
      method,
      headers: {
        "X-Simulator-Token": window.sessionStorage.getItem("simulator-token"),
        ...(body ? { "Content-Type": "application/json" } : {}),
        ...(ifMatch ? { "If-Match": ifMatch } : {}),
      },
      ...(body ? { body: JSON.stringify(body) } : {}),
    });
    return { status: response.status, document: await response.json() };
  }, { method, path, body, ifMatch });
}

async function startAttemptViaApi(page, assessment) {
  const started = await api(page, "POST", "/api/attempts", { assessment, mode: "full" });
  expect(started.status).toBe(201);
  return started.document.data.session.attempt_id;
}

async function saveSourceViaApi(page, attemptId, content) {
  const current = await api(page, "GET", `/api/source?attempt_id=${attemptId}`);
  expect(current.status).toBe(200);
  const saved = await api(page, "PUT", `/api/source?attempt_id=${attemptId}`, { content }, current.document.data.etag);
  expect(saved.status).toBe(200);
  return saved.document.data.source.etag;
}

async function submitAttemptViaApi(page, assessment, content) {
  const attemptId = await startAttemptViaApi(page, assessment);
  const etag = await saveSourceViaApi(page, attemptId, content);
  const submitted = await api(page, "POST", `/api/submit?attempt_id=${attemptId}`, { content }, etag);
  expect(submitted.status).toBe(200);
  expect(submitted.document.data.session.status).toBe("submitted");
  return attemptId;
}

async function endAttemptViaApi(page, attemptId) {
  const time = await api(page, "GET", `/api/time?attempt_id=${attemptId}`);
  const ended = await api(page, "POST", `/api/attempts/${attemptId}/abandon`, {
    expected_revision: time.document.data.session.revision,
  });
  expect(ended.status).toBe(200);
}

async function readSession(attemptId) {
  return JSON.parse(
    await readFile(join(harness.workspaceRoot, "attempts", attemptId, "session.json"), "utf8"),
  );
}

async function readActivePointer() {
  return readFile(join(harness.workspaceRoot, "attempts", "active.json"), "utf8");
}
