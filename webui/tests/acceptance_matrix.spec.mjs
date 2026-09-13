import { mkdir, readFile, writeFile } from "node:fs/promises";
import { join } from "node:path";
import { expect, test } from "@playwright/test";
import {
  installOfflineRequestPolicy,
  startFixtureServer,
} from "./browser_harness.mjs";
import { EntryPage } from "./pages/entry_page.mjs";

// Acceptance-matrix journeys (006/01) that no earlier spec covered: a stale
// second tab attempting the same restart, and a real legacy session/v1 record
// browsed and reviewed through the shipped screens. Synthetic workspace only.

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

test("a stale tab cannot restart an attempt that another tab already restarted (R3/R4/R9)", async ({ page }) => {
  await openLibrary(page);
  await new EntryPage(page).start("full");
  await expect(page.locator(".status")).toHaveText(/Python editor ready/);
  const oldId = await page.locator("main").getAttribute("data-attempt-id");
  const oldSource = await readFile(join(harness.workspaceRoot, "attempts", oldId, "simulation.py"));

  // The second tab reconnects to the same attempt and then goes stale. The
  // capability lives in per-tab session storage, so the new tab captures it
  // from the fragment exactly as a freshly opened window would.
  const stale = await page.context().newPage();
  const stalePolicy = await installOfflineRequestPolicy(stale, harness);
  await stale.goto(`${harness.origin}/attempt/${oldId}#token=${harness.token}`);
  await stale.getByRole("button", { name: "Reconnect to active session" }).click();
  await expect(stale.locator(".status")).toHaveText(/Python editor ready/);
  await expect(stale.locator("main")).toHaveAttribute("data-attempt-id", oldId);

  // First tab restarts.
  await page.getByRole("button", { name: "Restart" }).click();
  const restarted = page.waitForResponse((response) =>
    new URL(response.url()).pathname === `/api/attempts/${oldId}/restart`,
  );
  await page.getByRole("dialog", { name: "Restart with a new attempt?" })
    .getByRole("button", { name: "Restart attempt" }).click();
  expect((await restarted).status()).toBe(201);
  await expect(page.locator(".status")).toHaveText(/Python editor ready/);
  const replacement = await page.locator("main").getAttribute("data-attempt-id");
  expect(replacement).not.toBe(oldId);

  // The stale tab still shows the old attempt as active; its Restart must not
  // create a second replacement. The fresh revision read finds the attempt
  // ended and the tab refreshes into the read-only view instead of posting.
  const stalePosts = [];
  stale.on("request", (request) => {
    if (["POST", "PUT"].includes(request.method())) stalePosts.push(new URL(request.url()).pathname);
  });
  await stale.getByRole("button", { name: "Restart" }).click();
  await stale.getByRole("dialog", { name: "Restart with a new attempt?" })
    .getByRole("button", { name: "Restart attempt" }).click();
  await expect(stale.getByText("Ended", { exact: true })).toBeVisible();
  await expect(stale.locator("main")).toHaveAttribute("data-attempt-id", oldId);
  for (const name of ["Restart", "End attempt", "Submit", "Reset source"]) {
    await expect(stale.getByRole("button", { name })).toBeDisabled();
  }
  expect(stalePosts).toEqual([]);

  const attempts = join(harness.workspaceRoot, "attempts");
  const oldSession = JSON.parse(await readFile(join(attempts, oldId, "session.json"), "utf8"));
  expect(oldSession.status).toBe("abandoned");
  expect(await readFile(join(attempts, oldId, "simulation.py"))).toEqual(oldSource);
  const pointer = JSON.parse(await readFile(join(attempts, "active.json"), "utf8"));
  expect(pointer.attempt_id).toBe(replacement);
  // Exactly one replacement exists: old, replacement, nothing else.
  const listing = await page.evaluate(async () => {
    const response = await fetch("/api/attempts?limit=100", {
      headers: { "X-Simulator-Token": window.sessionStorage.getItem("simulator-token") },
    });
    return (await response.json()).data.items.map((item) => [item.attempt_id, item.status]);
  });
  expect(listing).toHaveLength(2);
  expect(new Map(listing).get(replacement)).toBe("active");
  expect(new Map(listing).get(oldId)).toBe("abandoned");
  await stalePolicy.assert();
  await stale.close();
});

test("a real legacy session/v1 record is listed and reviewed honestly without being upgraded (R5/R6/R8)", async ({ page }) => {
  await openLibrary(page);
  const legacyId = "0f1c2d3e-4a5b-4c6d-8e9f-0a1b2c3d4e5f";
  const legacyDirectory = join(harness.workspaceRoot, "attempts", legacyId);
  await mkdir(legacyDirectory, { recursive: true });
  const legacySession = {
    schema_version: "session/v1",
    attempt_id: legacyId,
    assessment: { assessment_id: "file_storage", display_name: "File Storage", level_count: 4 },
    profile: { mode: "drill", profile_id: "drill-30m", duration_seconds: 1800 },
    started_at: "2029-12-31T23:00:00+00:00",
    deadline_at: "2029-12-31T23:30:00+00:00",
    status: "submitted",
    revision: 2,
    score: {
      levels: [
        { level: 1, outcome: "passed" }, { level: 2, outcome: "passed" },
        { level: 3, outcome: "failed" }, { level: 4, outcome: "failed" },
      ],
      passed_levels: 2,
      highest_contiguous_level: 2,
    },
    submitted_at: "2029-12-31T23:20:00+00:00",
  };
  const sessionBytes = JSON.stringify(legacySession, null, 2);
  const legacySource = "def evaluate(group):\n    return 'legacy'  # written by an older release\n";
  await writeFile(join(legacyDirectory, "session.json"), sessionBytes, "utf8");
  await writeFile(join(legacyDirectory, "simulation.py"), legacySource, "utf8");
  await writeFile(join(legacyDirectory, "events.jsonl"), "", "utf8");
  const before = {
    session: await readFile(join(legacyDirectory, "session.json")),
    source: await readFile(join(legacyDirectory, "simulation.py")),
    events: await readFile(join(legacyDirectory, "events.jsonl")),
  };
  const requests = [];
  page.on("request", (request) => {
    const url = new URL(request.url());
    if (url.pathname.startsWith("/api/")) requests.push({ method: request.method(), path: url.pathname });
  });

  await page.goto(`${harness.origin}/history`);
  const row = page.locator(`tbody tr[data-attempt-id="${legacyId}"]`);
  await expect(row).toBeVisible();
  await expect(row).toContainText("File Storage");
  await expect(row).toContainText("Submitted");
  await expect(row).toContainText("drill · 30 min");
  await expect(row).toContainText("Final: 2 of 4 levels");
  await expect(row).toContainText("No submission review stored");
  await expect(row).toHaveAttribute("data-available", "true");
  await expect(row.getByRole("button", { name: /^Review/ })).toBeEnabled();

  await row.getByRole("button", { name: /^Review/ }).click();
  await expect(page.getByRole("heading", { name: "Attempt review: File Storage", level: 1 })).toBeFocused();
  const banners = page.locator(".review-legacy");
  await expect(banners).toHaveCount(2);
  await expect(banners.nth(0)).toContainText("Submitted-source binding unavailable");
  await expect(banners.nth(1)).toContainText("Content identity unavailable");
  await expect(page.locator(".session-summary")).toContainText("unavailable (legacy record)");
  await expect(page.locator(".session-summary")).toContainText("session/v1");
  await expect(page.locator(".review-result")).toContainText("Passed 2 of 4 levels.");
  await expect(page.getByRole("heading", { name: "Current file (not proven submitted)" })).toBeVisible();
  await expect(page.getByRole("textbox", { name: "Legacy source, read-only" })).toHaveValue(legacySource);
  await expect(page.getByRole("button", { name: "Retry this exercise" })).toBeEnabled();

  // Reading never upgraded, repaired or reselected the legacy record.
  expect(await readFile(join(legacyDirectory, "session.json"))).toEqual(before.session);
  expect(await readFile(join(legacyDirectory, "simulation.py"))).toEqual(before.source);
  expect(await readFile(join(legacyDirectory, "events.jsonl"))).toEqual(before.events);
  await expect(page.getByRole("main")).toHaveAttribute("data-review-attempt-id", legacyId);
  expect(requests.filter((r) => r.method !== "GET")).toEqual([]);
  const activeExists = await readFile(join(harness.workspaceRoot, "attempts", "active.json"), "utf8")
    .then(() => true, (error) => (error.code === "ENOENT" ? false : Promise.reject(error)));
  expect(activeExists).toBe(false);
  expect(harness.attemptId).toBeUndefined();
});

async function openLibrary(page) {
  await page.goto(`${harness.origin}/#token=${harness.token}`);
  await new EntryPage(page).expectLoaded();
}
