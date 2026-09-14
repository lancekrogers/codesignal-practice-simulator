import { mkdir, readFile, symlink, writeFile } from "node:fs/promises";
import { join } from "node:path";
import { expect, test } from "@playwright/test";
import {
  installOfflineRequestPolicy,
  startFixtureServer,
} from "./browser_harness.mjs";
import { EntryPage } from "./pages/entry_page.mjs";

// Attempt history screen (D004, 005/02/01): filters, bounded pages, warnings,
// per-row availability, and navigation state that survives review and back.
// Attempts are created through the public API from the page context; the
// listing must stay metadata-only (no source, review or lifecycle requests).

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

test("an empty history explains itself and requests only the listing", async ({ page }) => {
  await openLibrary(page);
  const mutations = trackRequests(page);
  await page.getByRole("button", { name: "History" }).click();
  await expect(page.getByRole("heading", { name: "Attempt history", level: 1 })).toBeFocused();
  await expect(page.getByRole("status")).toContainText("No attempts yet. Start one from the library.");
  await expect(page.getByLabel("Exercise")).toHaveValue("");
  await expect(page.getByLabel("Status")).toHaveValue("");
  await expect(page.getByLabel("Rows per page")).toHaveValue("25");
  await expect(page.getByRole("button", { name: "Older" })).toBeDisabled();
  await expect(page.getByRole("button", { name: "Newest" })).toBeDisabled();
  expect(mutations.filter((r) => r.method !== "GET")).toEqual([]);
  expect(mutations.map((r) => r.path)).toEqual(
    expect.arrayContaining(["/api/attempts"]),
  );
  expect(mutations.some((r) => r.path.startsWith("/api/source") || r.path.includes("/review"))).toBe(false);
  // Keyboard: heading → Back to library → the three filters → Refresh.
  await page.keyboard.press("Tab");
  await expect(page.getByRole("button", { name: "Back to library" })).toBeFocused();
  await page.keyboard.press("Tab");
  await expect(page.getByLabel("Exercise")).toBeFocused();
  await page.keyboard.press("Tab");
  await expect(page.getByLabel("Status")).toBeFocused();
  await page.keyboard.press("Tab");
  await expect(page.getByLabel("Rows per page")).toBeFocused();
  await page.keyboard.press("Tab");
  await expect(page.getByRole("button", { name: "Refresh" })).toBeFocused();
});

test("pages newest-first, filters by status and exercise, and keeps state through review and back", async ({ page }) => {
  await openLibrary(page);
  // The listing orders by creation time, so each attempt gets a later clock.
  const ended = [];
  let minute = 0;
  for (const assessment of ["file_storage", "account_ledger", "file_storage"]) {
    await harness.setClock(clockAt(minute++));
    ended.push(await createEndedAttempt(page, assessment));
  }
  const requests = trackRequests(page);

  await page.goto(`${harness.origin}/history#limit=2`);
  await expect(page.getByRole("heading", { name: "Attempt history", level: 1 })).toBeFocused();
  await expect(page.getByRole("status")).toContainText("Showing 2 attempts on the newest page.");
  const rows = page.locator("tbody tr");
  await expect(rows).toHaveCount(2);
  await expect(rows.nth(0)).toHaveAttribute("data-attempt-id", ended[2]);
  await expect(rows.nth(0)).toContainText("File Storage");
  await expect(rows.nth(0)).toContainText("Ended");
  await expect(rows.nth(0)).toContainText("No result recorded");
  await expect(rows.nth(0)).toContainText("Saved work only");
  await expect(rows.nth(0).getByRole("button", { name: /^Resume/ })).toHaveCount(0);
  await expect(rows.nth(1)).toHaveAttribute("data-attempt-id", ended[1]);
  await expect(rows.nth(1)).toContainText("Account Ledger");

  await page.getByRole("button", { name: "Older" }).click();
  await expect(page.getByRole("status")).toContainText("Showing 1 attempt on an older page.");
  await expect(rows.nth(0)).toHaveAttribute("data-attempt-id", ended[0]);
  await expect(page.getByRole("button", { name: "Older" })).toBeDisabled();
  // The control that had focus is disabled after the re-render, so focus
  // lands on the heading instead of being lost to the document body.
  await expect(page.getByRole("heading", { name: "Attempt history", level: 1 })).toBeFocused();
  await expect(page.locator(".history-pagination .history-notice")).toContainText("can move between pages");
  expect(new URL(page.url()).hash).toMatch(/cursor=/u);

  // The dataset grows while an older page is open; Newest shows the new attempt.
  await harness.setClock(clockAt(minute++));
  const newest = await createEndedAttempt(page, "account_ledger");
  requests.length = 0; // the test's own API calls are not the screen's
  await page.getByRole("button", { name: "Newest" }).click();
  await expect(rows.nth(0)).toHaveAttribute("data-attempt-id", newest);
  await expect(rows.nth(1)).toHaveAttribute("data-attempt-id", ended[2]);
  expect(new URL(page.url()).hash).toBe("#limit=2");

  await page.getByLabel("Status").selectOption("abandoned");
  await expect(page.getByRole("status")).toContainText("Showing 2 attempts on the newest page.");
  await expect(rows.nth(0)).toHaveAttribute("data-attempt-id", newest);
  expect(new URL(page.url()).hash).toBe("#status=abandoned&limit=2");
  await page.getByLabel("Exercise").selectOption("file_storage");
  await expect(rows).toHaveCount(2);
  await expect(rows.nth(0)).toHaveAttribute("data-attempt-id", ended[2]);
  await expect(rows.nth(1)).toHaveAttribute("data-attempt-id", ended[0]);
  await expect(page.getByRole("button", { name: "Older" })).toBeDisabled();

  // Up to here the history screen itself has requested only the listing and
  // the bootstrap: never source, review or a mutation.
  expect(requests.filter((r) => r.method !== "GET")).toEqual([]);
  expect(requests.some((r) => r.path.startsWith("/api/source") || r.path.includes("/review"))).toBe(false);

  // Review keeps the filters in the fragment; Back to history restores them.
  // (The review screen legitimately reads that attempt's review and saved work.)
  const activeBefore = await readActivePointer();
  await rows.nth(0).getByRole("button", { name: /^Review/ }).click();
  await expect(page.getByRole("heading", { name: "Attempt review", level: 1 })).toBeFocused();
  expect(new URL(page.url()).pathname).toBe(`/history/review/${ended[2]}`);
  expect(new URL(page.url()).hash).toBe("#status=abandoned&assessment_id=file_storage&limit=2");
  await page.getByRole("button", { name: "Back to history" }).click();
  await expect(page.getByLabel("Status")).toHaveValue("abandoned");
  await expect(page.getByLabel("Exercise")).toHaveValue("file_storage");
  await expect(rows.nth(0)).toHaveAttribute("data-attempt-id", ended[2]);
  await page.goBack();
  await expect(page.getByRole("heading", { name: "Attempt review", level: 1 })).toBeVisible();
  await page.goBack();
  await expect(page.getByLabel("Status")).toHaveValue("abandoned");
  expect(await readActivePointer()).toBe(activeBefore);
  expect(requests.filter((r) => r.method !== "GET")).toEqual([]);
  // The review was opened twice (Review, then browser back onto it); each time
  // it read only that attempt's review.
  const reviewReads = requests.filter((r) => r.path.includes("/review"));
  expect(reviewReads).toHaveLength(2);
  for (const read of reviewReads) {
    expect(read).toEqual({ method: "GET", path: `/api/attempts/${ended[2]}/review` });
  }

  // A live attempt started meanwhile appears after Refresh; Resume is offered
  // only for that selected active attempt and opens it directly.
  await page.getByLabel("Status").selectOption("");
  await page.getByLabel("Exercise").selectOption("");
  await harness.setClock(clockAt(minute++));
  const active = await startAttemptViaApi(page, "in_memory_records");
  await page.getByRole("button", { name: "Refresh" }).click();
  await expect(rows.nth(0)).toHaveAttribute("data-attempt-id", active);
  await expect(rows.nth(0)).toContainText("In-Memory Records");
  await expect(rows.nth(0)).toContainText("Active");
  await expect(rows.nth(1).getByRole("button", { name: /^Resume/ })).toHaveCount(0);
  await rows.nth(0).getByRole("button", { name: /^Resume/ }).click();
  await expect(page.locator(".status")).toHaveText(/Python editor ready/);
  await expect(page.locator("main")).toHaveAttribute("data-attempt-id", active);
});

test("skipped and corrupt entries are reported without hiding the safe rows", async ({ page }) => {
  await openLibrary(page);
  await harness.setClock(clockAt(1));
  const good = await createEndedAttempt(page, "file_storage");
  const attempts = join(harness.workspaceRoot, "attempts");
  await mkdir(join(attempts, "not-an-attempt"), { recursive: true });
  await symlink(join(attempts, good), join(attempts, "0f1c2d3e-4a5b-4c6d-8e9f-0a1b2c3d4e5f"));
  const corrupt = "1a2b3c4d-5e6f-4a7b-8c9d-0e1f2a3b4c5d";
  await mkdir(join(attempts, corrupt), { recursive: true });
  await writeFile(join(attempts, corrupt, "session.json"), "{not json", "utf8");

  await page.goto(`${harness.origin}/history`);
  await expect(page.getByRole("heading", { name: "Attempt history", level: 1 })).toBeFocused();
  await expect(page.locator(".history-warning")).toContainText(
    "2 entries in the attempts folder are not a safe attempt record and were skipped.",
  );
  const rows = page.locator("tbody tr");
  await expect(rows).toHaveCount(2);
  await expect(rows.nth(0)).toHaveAttribute("data-attempt-id", good);
  await expect(rows.nth(0).getByRole("button", { name: /^Review/ })).toBeEnabled();
  const broken = rows.nth(1);
  await expect(broken).toHaveAttribute("data-attempt-id", corrupt);
  await expect(broken).toHaveAttribute("data-available", "false");
  await expect(broken).toContainText("Unavailable");
  await expect(broken).toContainText("Record corrupt");
  await expect(broken).toContainText("Unknown exercise");
  await expect(broken.getByRole("button", { name: /^Review/ })).toBeDisabled();
  const text = await page.getByRole("main").innerText();
  expect(text).not.toMatch(/\/Users|\/tmp|\/private|attempts\//u);
});

test("a malformed cursor recovers to the newest page instead of crashing", async ({ page }) => {
  await openLibrary(page);
  const attempt = await createEndedAttempt(page, "file_storage");
  // A fragment value with an illegal shape never reaches the server.
  await page.goto(`${harness.origin}/history#cursor=%25%25%25&limit=abc`);
  await expect(page.getByRole("heading", { name: "Attempt history", level: 1 })).toBeFocused();
  await expect(page.locator(".history-notice").first())
    .toContainText("page position in this address is not valid");
  await expect(page.locator(".history-notice").nth(1))
    .toContainText("rows-per-page value in this address is not valid");
  await expect(page.locator("tbody tr")).toHaveCount(1);
  expect(new URL(page.url()).hash).toBe("");

  // A well-shaped cursor the server rejects is shown as a recoverable error.
  requestPolicy.expectHttpError({ method: "GET", path: "/api/attempts", status: 422 });
  await page.goto(`${harness.origin}/history#cursor=bm90LWEtY3Vyc29y`);
  await expect(page.getByRole("alert")).toContainText("page position or filters in this address are not valid");
  await expect(page.locator("tbody tr")).toHaveCount(0);
  await page.getByRole("button", { name: "Show newest" }).click();
  await expect(page.locator("tbody tr")).toHaveCount(1);
  await expect(page.locator("tbody tr").first()).toHaveAttribute("data-attempt-id", attempt);
  expect(new URL(page.url()).hash).toBe("");
});

test("a listing failure offers retry and never leaks server text", async ({ page }) => {
  await openLibrary(page);
  const attempt = await createEndedAttempt(page, "file_storage");
  requestPolicy.intercept("/api/attempts", {
    status: 404,
    contentType: "application/json",
    body: JSON.stringify({
      schema_version: "web/v1", ok: false,
      error: { code: "history_unavailable", message: "attempts at /Users/private/workspace unreadable" },
    }),
  });
  requestPolicy.expectHttpError({ method: "GET", path: "/api/attempts", status: 404 });
  await page.goto(`${harness.origin}/history`);
  const alert = page.getByRole("alert");
  await expect(alert).toContainText("Attempt history is unavailable");
  expect(await alert.innerText()).not.toContain("/Users/private");
  await expect(page.getByRole("status")).toContainText("Attempt history could not be loaded.");
  requestPolicy.clearIntercept("/api/attempts");
  await page.getByRole("button", { name: "Retry" }).click();
  await expect(page.locator("tbody tr")).toHaveCount(1);
  await expect(page.locator("tbody tr").first()).toHaveAttribute("data-attempt-id", attempt);
  await expect(page.getByRole("status")).toContainText("Showing 1 attempt on the newest page.");
});

function clockAt(minute) {
  return `2030-01-01T00:${String(minute).padStart(2, "0")}:00+00:00`;
}

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

async function api(page, method, path, body) {
  return page.evaluate(async ({ method, path, body }) => {
    const response = await fetch(path, {
      method,
      headers: {
        "X-Simulator-Token": window.sessionStorage.getItem("simulator-token"),
        ...(body ? { "Content-Type": "application/json" } : {}),
      },
      ...(body ? { body: JSON.stringify(body) } : {}),
    });
    return { status: response.status, document: await response.json() };
  }, { method, path, body });
}

async function startAttemptViaApi(page, assessment) {
  const started = await api(page, "POST", "/api/attempts", { assessment, mode: "full" });
  expect(started.status).toBe(201);
  return started.document.data.session.attempt_id;
}

async function createEndedAttempt(page, assessment) {
  const attemptId = await startAttemptViaApi(page, assessment);
  const time = await api(page, "GET", `/api/time?attempt_id=${attemptId}`);
  const ended = await api(page, "POST", `/api/attempts/${attemptId}/abandon`, {
    expected_revision: time.document.data.session.revision,
  });
  expect(ended.status).toBe(200);
  return attemptId;
}

async function readActivePointer() {
  return readFile(join(harness.workspaceRoot, "attempts", "active.json"), "utf8");
}
