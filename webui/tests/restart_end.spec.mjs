import { readFile, stat } from "node:fs/promises";
import { join } from "node:path";
import { expect, test } from "@playwright/test";
import {
  installOfflineRequestPolicy,
  startFixtureServer,
} from "./browser_harness.mjs";

// End attempt, Restart and Reset source (D001/D004, 005/01/02). Every journey
// runs against the synthetic fixture workspace and checks the stored attempt
// files directly, so "saved old work is kept" is proven on disk, not inferred
// from the UI.

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

const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/u;

test("restart keeps the old attempt's saved bytes and opens a fresh replacement", async ({ page }) => {
  const started = await startAttempt(page);
  const oldId = started.data.session.attempt_id;
  await append(page, "\n# saved before restart");
  await expect(saveStatus(page)).toHaveText("Saved snapshot");
  const oldSource = await readAttemptSource(oldId);
  expect(oldSource).toContain("# saved before restart");
  const oldSession = await readSession(oldId);
  expect(oldSession.status).toBe("active");
  const posts = trackPosts(page);

  await page.getByRole("button", { name: "Restart" }).click();
  const dialog = page.getByRole("dialog", { name: "Restart with a new attempt?" });
  await expect(dialog).toContainText("saved work here is kept");
  await expect(dialog).toContainText("timer starts over only there");
  await expect(dialog).toContainText("Unsaved local edits are saved first");
  await dialog.getByRole("button", { name: "Cancel" }).click();
  await expect(page.getByRole("button", { name: "Restart" })).toBeFocused();
  expect(posts).toEqual([]);
  expect(await readSession(oldId)).toEqual(oldSession);

  await page.getByRole("button", { name: "Restart" }).click();
  const restarted = page.waitForResponse((response) =>
    new URL(response.url()).pathname === `/api/attempts/${oldId}/restart`,
  );
  await dialog.getByRole("button", { name: "Restart attempt" }).click();
  const response = await restarted;
  expect(response.status()).toBe(201);
  const body = await response.json();
  const newId = body.data.replacement_attempt_id;
  expect(newId).toMatch(UUID);
  expect(newId).not.toBe(oldId);
  expect(response.request().postDataJSON()).toEqual({
    operation_id: expect.stringMatching(UUID),
    expected_revision: oldSession.revision,
  });

  await expect(page.locator(".status")).toHaveText(/Python editor ready/);
  await expect(page.locator("main")).toHaveAttribute("data-attempt-id", newId);
  expect(new URL(page.url()).pathname).toBe(`/attempt/${newId}`);
  await expect(page.locator(".assessment-header .header-status").first().locator("strong"))
    .toHaveText("Active");
  await expect(page.locator(".view-lines")).not.toContainText("# saved before restart");
  const newSession = await readSession(newId);
  expect(newSession.status).toBe("active");
  expect(newSession.profile).toEqual(oldSession.profile);
  expect(Date.parse(newSession.started_at)).toBeGreaterThanOrEqual(Date.parse(oldSession.started_at));
  expect(newSession.deadline_at).not.toBe(undefined);

  const endedSession = await readSession(oldId);
  expect(endedSession.status).toBe("abandoned");
  expect(endedSession.abandonment.reason).toBe("restarted");
  expect(await readAttemptSource(oldId)).toBe(oldSource);
  expect(await harness.readStatus(oldId)).toContain("abandoned");
  expect(posts.map((request) => new URL(request.url()).pathname)).toEqual([
    `/api/attempts/${oldId}/restart`,
  ]);
});

test("duplicate restart clicks and a retry after a lost response reuse one operation", async ({ page }) => {
  const started = await startAttempt(page);
  const oldId = started.data.session.attempt_id;
  const restartPath = `/api/attempts/${oldId}/restart`;
  const posts = trackPosts(page);
  const restart = page.getByRole("button", { name: "Restart" });
  const dialog = page.getByRole("dialog", { name: "Restart with a new attempt?" });

  // First attempt: the server answer is replaced by a synthetic recovery-pending
  // envelope, as if the process died after journaling and before publishing.
  requestPolicy.intercept(restartPath, {
    status: 503,
    contentType: "application/json",
    body: JSON.stringify({
      schema_version: "web/v1", ok: false,
      error: { code: "recovery_pending", message: "restart pending at /Users/private/attempts" },
    }),
  });
  requestPolicy.expectHttpError({ method: "POST", path: restartPath, status: 503 });
  await restart.click();
  const firstResponse = page.waitForResponse((response) =>
    new URL(response.url()).pathname === restartPath,
  );
  await dialog.getByRole("button", { name: "Restart attempt" }).click();
  // The lifecycle operation lock disables every mutation control while the
  // request is in flight, so a second click cannot start a second operation.
  await expect(restart).toBeDisabled();
  await expect(page.getByRole("button", { name: "End attempt" })).toBeDisabled();
  await expect(page.getByRole("button", { name: "Submit" })).toBeDisabled();
  expect((await firstResponse).status()).toBe(503);
  await expect(page.locator(".status")).toContainText("recorded but not finished");
  expect(await page.locator(".status").innerText()).not.toContain("/Users/private");
  await expect(restart).toBeEnabled();
  expect(await readSession(oldId)).toMatchObject({ status: "active" });
  requestPolicy.clearIntercept(restartPath);

  // The server is really restarted between the failed attempt and the retry.
  await harness.restart();
  requestPolicy.refreshOrigin();
  await restart.click();
  const secondResponse = page.waitForResponse((response) =>
    new URL(response.url()).pathname === restartPath,
  );
  await dialog.getByRole("button", { name: "Restart attempt" }).click();
  const response = await secondResponse;
  expect(response.status()).toBe(201);
  const newId = (await response.json()).data.replacement_attempt_id;
  await expect(page.locator("main")).toHaveAttribute("data-attempt-id", newId);

  const bodies = posts
    .filter((request) => new URL(request.url()).pathname === restartPath)
    .map((request) => request.postDataJSON());
  expect(bodies).toHaveLength(2);
  expect(bodies[0].operation_id).toBe(bodies[1].operation_id);
  expect(bodies[0].expected_revision).toBe(bodies[1].expected_revision);
  const completion = join(harness.workspaceRoot, "attempts", ".restart-completed", `${bodies[0].operation_id}.json`);
  expect((await stat(completion)).isFile()).toBe(true);
  expect(await readSession(oldId)).toMatchObject({ status: "abandoned" });
});

test("restart with unsaved text is blocked until the edits save or are explicitly discarded", async ({ page }) => {
  const started = await startAttempt(page);
  const oldId = started.data.session.attempt_id;
  await append(page, "\n# saved marker");
  await expect(saveStatus(page)).toHaveText("Saved snapshot");
  requestPolicy.intercept("/api/source", {
    status: 503,
    contentType: "application/json",
    body: JSON.stringify({
      schema_version: "web/v1", ok: false,
      error: { code: "temporary_failure", message: "temporary save failure" },
    }),
  });
  // The failed autosave, then one save retry per Restart confirmation (the
  // buffer is flushed before the discard question is ever asked).
  requestPolicy.expectHttpError({ method: "PUT", path: "/api/source", status: 503, count: 3 });
  await append(page, "\n# unsaved marker");
  await expect(saveStatus(page)).toHaveText("Save failed — retry");
  const posts = trackPosts(page);
  const postPaths = () => posts
    .filter((request) => request.method() === "POST")
    .map((request) => new URL(request.url()).pathname);

  await page.getByRole("button", { name: "Restart" }).click();
  const confirm = page.getByRole("dialog", { name: "Restart with a new attempt?" });
  await confirm.getByRole("button", { name: "Restart attempt" }).click();
  const discard = page.getByRole("dialog", { name: "Unsaved edits could not be saved" });
  await expect(discard).toBeVisible();
  await expect(discard).toContainText("Continuing discards those unsaved edits");
  await discard.getByRole("button", { name: "Cancel" }).click();
  await expect(discard).toBeHidden();
  await expect(page.getByRole("button", { name: "Restart" })).toBeFocused();
  await expect(page.locator(".view-lines")).toContainText("# unsaved marker");
  expect(postPaths()).toEqual([]);
  expect(posts.filter((request) => request.method() === "PUT")).toHaveLength(1);
  expect(await readSession(oldId)).toMatchObject({ status: "active" });

  await page.getByRole("button", { name: "Restart" }).click();
  await confirm.getByRole("button", { name: "Restart attempt" }).click();
  await expect(discard).toBeVisible();
  // The discard path skips the flush, so lifting the save failure here only
  // lets the replacement attempt load its own source afterwards.
  requestPolicy.clearIntercept("/api/source");
  const restarted = page.waitForResponse((response) =>
    new URL(response.url()).pathname === `/api/attempts/${oldId}/restart`,
  );
  await discard.getByRole("button", { name: "Discard unsaved edits and restart" }).click();
  expect((await restarted).status()).toBe(201);
  await expect(page.locator(".status")).toHaveText(/Python editor ready/);
  await expect(page.locator("main")).not.toHaveAttribute("data-attempt-id", oldId);
  const oldSource = await readAttemptSource(oldId);
  expect(oldSource).toContain("# saved marker");
  expect(oldSource).not.toContain("# unsaved marker");
  expect(await readSession(oldId)).toMatchObject({ status: "abandoned" });
});

test("a submission in flight blocks restart and end, and reset source keeps the attempt", async ({ page }) => {
  const started = await startAttempt(page);
  const attemptId = started.data.session.attempt_id;
  await append(page, "\n# reset candidate");
  await expect(saveStatus(page)).toHaveText("Saved snapshot");
  const sessionBefore = await readSession(attemptId);

  await page.getByRole("button", { name: "Reset source" }).click();
  const resetDialog = page.getByRole("dialog", { name: "Reset candidate source" });
  const reset = page.waitForResponse((response) =>
    new URL(response.url()).pathname === "/api/source/reset",
  );
  await resetDialog.getByRole("button", { name: "Reset source" }).click();
  expect((await reset).status()).toBe(200);
  await expect(page.locator(".view-lines")).not.toContainText("# reset candidate");
  await expect(page.locator("main")).toHaveAttribute("data-attempt-id", attemptId);
  await expect(page.locator(".assessment-header .header-status").first().locator("strong"))
    .toHaveText("Active");
  const sessionAfterReset = await readSession(attemptId);
  expect(sessionAfterReset.status).toBe("active");
  expect(sessionAfterReset.attempt_id).toBe(attemptId);
  expect(sessionAfterReset.deadline_at).toBe(sessionBefore.deadline_at);

  const submitHeld = requestPolicy.hold("/api/submit");
  await page.getByRole("button", { name: "Submit" }).click();
  await page.getByRole("dialog", { name: "Submit local practice attempt" })
    .getByRole("button", { name: "Submit attempt" }).click();
  await submitHeld;
  await expect(page.getByRole("button", { name: "Restart" })).toBeDisabled();
  await expect(page.getByRole("button", { name: "End attempt" })).toBeDisabled();
  await expect(page.getByRole("button", { name: "Reset source" })).toBeDisabled();
  requestPolicy.release("/api/submit");
  await expect(page.getByText("Submitted", { exact: true })).toBeVisible();
  for (const name of ["Restart", "End attempt", "Reset source", "Run Tests", "Submit"]) {
    await expect(page.getByRole("button", { name })).toBeDisabled();
  }
});

test("end attempt records an ended attempt without a score and keeps saved work readable", async ({ page }) => {
  const started = await startAttempt(page);
  const attemptId = started.data.session.attempt_id;
  await append(page, "\n# saved before ending");
  await expect(saveStatus(page)).toHaveText("Saved snapshot");
  const sessionBefore = await readSession(attemptId);
  const posts = trackPosts(page);

  await page.getByRole("button", { name: "End attempt" }).click();
  const dialog = page.getByRole("dialog", { name: "End attempt?" });
  await expect(dialog).toContainText("ended without a score");
  await expect(dialog).toContainText("saved work is kept");
  await dialog.getByRole("button", { name: "Cancel" }).click();
  await expect(page.getByRole("button", { name: "End attempt" })).toBeFocused();
  expect(posts).toEqual([]);

  await page.getByRole("button", { name: "End attempt" }).click();
  const ended = page.waitForResponse((response) =>
    new URL(response.url()).pathname === `/api/attempts/${attemptId}/abandon`,
  );
  await dialog.getByRole("button", { name: "End attempt" }).click();
  const response = await ended;
  expect(response.status()).toBe(200);
  expect(response.request().postDataJSON()).toEqual({
    expected_revision: sessionBefore.revision,
  });
  const body = await response.json();
  expect(body.data.newly_abandoned).toBe(true);
  expect(body.data.session.status).toBe("abandoned");

  await expect(page.getByText("Ended", { exact: true })).toBeVisible();
  await expect(page.locator("main")).toHaveAttribute("data-attempt-id", attemptId);
  await expect(page.getByTestId("output-drawer")).toContainText("ended before submission");
  await expect(page.locator(".sr-status")).toContainText("Attempt ended without submission");
  await expect(page.locator(".fallback")).toHaveValue(/# saved before ending/u);
  await expect(page.locator(".fallback")).toHaveAttribute("readonly", "");
  for (const name of ["Save changes", "Run Tests", "Reset source", "End attempt", "Restart", "Submit"]) {
    await expect(page.getByRole("button", { name })).toBeDisabled();
  }
  const session = await readSession(attemptId);
  expect(session.status).toBe("abandoned");
  expect(session.abandonment.reason).toBe("ended");
  expect(session.score).toBe(null);
  expect(await readAttemptSource(attemptId)).toContain("# saved before ending");
  expect(await harness.readStatus(attemptId)).toContain("abandoned");
  expect(posts.map((request) => new URL(request.url()).pathname)).toEqual([
    `/api/attempts/${attemptId}/abandon`,
  ]);
  expect(harness.attemptId).toBe(attemptId);
});

test("a stale revision refreshes the view and mints a new operation for the next restart", async ({ page }) => {
  const started = await startAttempt(page);
  const attemptId = started.data.session.attempt_id;
  const restartPath = `/api/attempts/${attemptId}/restart`;
  requestPolicy.intercept(restartPath, {
    status: 409,
    contentType: "application/json",
    body: JSON.stringify({
      schema_version: "web/v1", ok: false,
      error: { code: "stale_revision", message: "expected revision 7 at /tmp/private" },
    }),
  });
  requestPolicy.expectHttpError({ method: "POST", path: restartPath, status: 409 });
  const posts = trackPosts(page);
  const dialog = page.getByRole("dialog", { name: "Restart with a new attempt?" });
  await page.getByRole("button", { name: "Restart" }).click();
  const stale = page.waitForResponse((response) =>
    new URL(response.url()).pathname === restartPath,
  );
  await dialog.getByRole("button", { name: "Restart attempt" }).click();
  expect((await stale).status()).toBe(409);
  await expect(page.locator(".status")).toContainText("changed elsewhere");
  expect(await page.locator(".status").innerText()).not.toContain("/tmp/private");
  await expect(page.getByRole("button", { name: "Restart" })).toBeEnabled();
  await expect(page.locator("main")).toHaveAttribute("data-attempt-id", attemptId);
  requestPolicy.clearIntercept(restartPath);

  await page.getByRole("button", { name: "Restart" }).click();
  const restarted = page.waitForResponse((response) =>
    new URL(response.url()).pathname === restartPath,
  );
  await dialog.getByRole("button", { name: "Restart attempt" }).click();
  expect((await restarted).status()).toBe(201);
  await expect(page.locator("main")).not.toHaveAttribute("data-attempt-id", attemptId);
  const bodies = posts
    .filter((request) => new URL(request.url()).pathname === restartPath)
    .map((request) => request.postDataJSON());
  expect(bodies).toHaveLength(2);
  expect(bodies[0].operation_id).not.toBe(bodies[1].operation_id);
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

function trackPosts(page) {
  const requests = [];
  page.on("request", (request) => {
    if (["POST", "PUT"].includes(request.method())) requests.push(request);
  });
  return requests;
}

async function readAttemptSource(attemptId) {
  return readFile(join(harness.workspaceRoot, "attempts", attemptId, "simulation.py"), "utf8");
}

async function readSession(attemptId) {
  return JSON.parse(
    await readFile(join(harness.workspaceRoot, "attempts", attemptId, "session.json"), "utf8"),
  );
}
