import { createHash } from "node:crypto";
import { expect, test } from "@playwright/test";
import {
  installOfflineRequestPolicy,
  startFixtureServer,
} from "./browser_harness.mjs";

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

test("debounced autosave survives a refresh", async ({ page }) => {
  const started = await startAttempt(page);
  await append(page, "\n# autosave survives refresh");
  await expect(saveStatus(page)).toHaveText("Saved snapshot");

  await page.reload();
  await page.getByRole("button", { name: "Reconnect to active session" }).click();
  await expect(page.getByText("Python editor ready.", { exact: false })).toBeVisible();
  await expect(page.locator(".monaco-editor .view-lines")).toContainText(
    "# autosave survives refresh",
  );
  expect((await source(harness, started.data.session.attempt_id)).content)
    .toContain("# autosave survives refresh");
});

test("serializes rapid edits and saves the latest buffer", async ({ page }) => {
  const started = await startAttempt(page);
  requestPolicy.delay("/api/source", 350);
  const requests = trackPuts(page);

  await append(page, "\n# first queued edit");
  await expect.poll(() => requests.length).toBe(1);
  await append(page, "\n# final queued edit");
  await expect(saveStatus(page)).toHaveText("Saved snapshot");

  expect(requests).toHaveLength(2);
  expect(requests[0].postDataJSON().content).toContain("# first queued edit");
  expect(requests[1].postDataJSON().content).toContain("# final queued edit");
  expect(requests[1].headers()["if-match"]).toBe(
    etagFor(requests[0].postDataJSON().content),
  );
  expect((await source(harness, started.data.session.attempt_id)).content)
    .toContain("# final queued edit");
});

test("shows a failed save and retries it successfully", async ({ page }) => {
  const started = await startAttempt(page);
  const requests = trackPuts(page);
  const competingRequests = [];
  page.on("request", (request) => {
    const path = new URL(request.url()).pathname;
    if (["/api/test", "/api/source/reset", "/api/source/restore"].includes(path)) {
      competingRequests.push(request);
    }
  });
  requestPolicy.intercept("/api/source", {
    status: 503,
    contentType: "application/json",
    body: JSON.stringify({
      schema_version: "web/v1",
      ok: false,
      error: { code: "temporary_failure", message: "temporary save failure" },
    }),
  });
  requestPolicy.expectHttpError(503);

  await append(page, "\n# retry this save");
  await expect(saveStatus(page)).toHaveText("Save failed — retry");
  await expect(page.getByRole("button", { name: "Save changes" })).toBeEnabled();

  requestPolicy.clearIntercept("/api/source");
  let releaseRetry;
  const retryGate = new Promise((resolve) => {
    releaseRetry = resolve;
  });
  await page.route("**/api/source*", async (route) => {
    await retryGate;
    await route.continue();
  });
  const retryResponse = page.waitForResponse((response) =>
    new URL(response.url()).pathname === "/api/source" &&
    response.request().method() === "PUT",
  );
  const retryRequest = page.waitForRequest((request) =>
    request.method() === "PUT" &&
    new URL(request.url()).pathname === "/api/source",
  );
  try {
    await page.getByRole("button", { name: "Save changes" }).click();
    await retryRequest;
    const run = page.getByRole("button", { name: "Run Tests" });
    if (await run.isEnabled()) await run.click();
    const reset = page.getByRole("button", { name: "Reset" });
    if (await reset.isEnabled()) await reset.click();
    await expect(page.getByRole("dialog")).toBeHidden();
    expect(requests).toHaveLength(2);
    expect(competingRequests).toHaveLength(0);
  } finally {
    releaseRetry();
    await retryResponse;
    await page.unroute("**/api/source*");
  }
  await expect(saveStatus(page)).toHaveText("Saved snapshot");
  expect((await source(harness, started.data.session.attempt_id)).content)
    .toContain("# retry this save");
});

test("preserves local text and explicitly reloads the server after a stale PUT", async ({
  page,
}) => {
  const started = await startAttempt(page);
  const attemptId = started.data.session.attempt_id;
  const serverContent = `SERVER VERSION\n${"bounded ".repeat(100)}SERVER HIDDEN`;
  const serverSave = await putSource(attemptId, serverContent, started.data.source.etag);
  expect(serverSave.status).toBe(200);
  requestPolicy.expectHttpError(409);

  const localMarker = "# local conflict text";
  await append(page, `\n${localMarker}`);
  await expect(saveStatus(page)).toHaveText("Conflict — choose a version");
  await expect(page.locator(".monaco-editor .view-lines")).toContainText(localMarker);

  const preview = page.locator(".source-conflict pre");
  await expect(preview).toContainText("SERVER VERSION");
  await expect(preview).not.toContainText("SERVER HIDDEN");
  expect(await preview.textContent()).toHaveLength(512);

  await page.getByRole("button", { name: "Reload server version" }).click();
  await expect(saveStatus(page)).toHaveText("Saved snapshot");
  await expect(page.locator(".monaco-editor .view-lines")).toContainText(
    "SERVER VERSION",
  );
  await expect(page.locator(".monaco-editor .view-lines")).not.toContainText(
    localMarker,
  );
});

test("explicitly copies local text after refreshing a conflict ETag", async ({ page }) => {
  const started = await startAttempt(page);
  const attemptId = started.data.session.attempt_id;
  const serverSave = await putSource(
    attemptId,
    "SERVER COPY VERSION\n",
    started.data.source.etag,
  );
  requestPolicy.expectHttpError(409);
  const localMarker = "# copied local conflict text";
  const requests = trackPuts(page);

  await append(page, `\n${localMarker}`);
  await expect(saveStatus(page)).toHaveText("Conflict — choose a version");
  await page.getByRole("button", { name: "Copy local version" }).click();
  await expect(saveStatus(page)).toHaveText("Saved snapshot");

  expect(requests).toHaveLength(2);
  expect(requests[1].headers()["if-match"]).toBe(serverSave.document.data.source.etag);
  expect((await source(harness, attemptId)).content).toContain(localMarker);
});

test("keeps conflict unresolved while typing until local recovery is explicit", async ({
  page,
}) => {
  const started = await startAttempt(page);
  const attemptId = started.data.session.attempt_id;
  const serverSave = await putSource(
    attemptId,
    "SERVER CONFLICT VERSION\n",
    started.data.source.etag,
  );
  requestPolicy.expectHttpError(409);
  await append(page, "\n# conflict edit");
  await expect(saveStatus(page)).toHaveText("Conflict — choose a version");
  const requests = trackPuts(page);
  await append(page, "\n# typed while unresolved");
  await page.waitForTimeout(700);
  await expect(saveStatus(page)).toHaveText("Conflict — choose a version");
  expect(requests).toHaveLength(0);
  await page.getByRole("button", { name: "Copy local version" }).click();
  await expect(saveStatus(page)).toHaveText("Saved snapshot");
  expect((await source(harness, attemptId)).content)
    .toContain("# typed while unresolved");
  expect(serverSave.document.data.source.content).toContain("SERVER");
});

test("pauses Monaco and preserves the buffer across a delayed source action", async ({
  page,
}) => {
  await startAttempt(page);
  await append(page, "\n# action candidate");
  await expect(saveStatus(page)).toHaveText("Saved snapshot");
  await page.getByRole("tab", { name: "History" }).click();
  const restore = page.getByRole("button", { name: "Restore this version" }).first();
  await restore.click();
  const dialog = page.getByRole("dialog");
  await dialog.getByRole("button", { name: "Cancel" }).click();
  requestPolicy.delay("/api/source/restore", 500);
  await restore.click();
  const response = page.waitForResponse((item) =>
    new URL(item.url()).pathname === "/api/source/restore",
  );
  await dialog.getByRole("button", { name: "Restore version" }).click();
  const input = page.locator(".monaco-editor .native-edit-context");
  await expect(input).toHaveAttribute("aria-autocomplete", "none");
  await page.locator(".monaco-editor").click();
  await page.keyboard.type("\n# blocked during action");
  await response;
  await expect(input).toHaveAttribute("aria-autocomplete", "both");
  await expect(page.locator(".monaco-editor .view-lines")).not.toContainText(
    "# blocked during action",
  );
});

test("delayed restore holds the shared lease without entering testing", async ({ page }) => {
  await startAttempt(page);
  await append(page, "\n# restore lock candidate");
  await expect(saveStatus(page)).toHaveText("Saved snapshot");
  await page.getByRole("tab", { name: "History" }).click();
  const restore = page.getByRole("button", { name: "Restore this version" }).first();
  requestPolicy.delay("/api/source/restore", 500);
  await restore.click();
  const dialog = page.getByRole("dialog");
  const restoreRequest = page.waitForRequest((item) =>
    new URL(item.url()).pathname === "/api/source/restore" &&
    item.method() === "POST",
  );
  const response = page.waitForResponse((item) =>
    new URL(item.url()).pathname === "/api/source/restore",
  );
  await dialog.getByRole("button", { name: "Restore version" }).click();
  await restoreRequest;
  const run = page.getByRole("button", { name: "Run Tests" });
  await expect(run).toBeDisabled();
  await expect(run).toHaveText("Run Tests");
  await expect(page.getByRole("button", { name: "Submit" })).toBeDisabled();
  await response;
});

test("delayed testing holds the shared lease against reset", async ({ page }) => {
  await startAttempt(page);
  let releaseTesting;
  const testingGate = new Promise((resolve) => {
    releaseTesting = resolve;
  });
  await page.route("**/api/test", async (route) => {
    await testingGate;
    await route.continue();
  });
  const sourceMutations = trackMutations(page);
  const run = page.locator('button[data-action="run"]');
  const testRequest = page.waitForRequest((item) =>
    new URL(item.url()).pathname === "/api/test" &&
    item.method() === "POST",
  );
  const testResponse = page.waitForResponse((item) =>
    new URL(item.url()).pathname === "/api/test",
  );
  try {
    await run.click();
    await testRequest;
    await expect(run).toHaveText("Testing…");
    const reset = page.getByRole("button", { name: "Reset" });
    await expect(reset).toBeDisabled();
    await expect(page.getByRole("button", { name: "Submit" })).toBeDisabled();
    expect(sourceMutations).toHaveLength(0);
  } finally {
    releaseTesting();
    await testResponse;
    await page.unroute("**/api/test");
  }
});

test("recovers an action conflict through the explicit local choice", async ({ page }) => {
  const started = await startAttempt(page);
  const attemptId = started.data.session.attempt_id;
  await append(page, "\n# restore conflict local");
  await expect(saveStatus(page)).toHaveText("Saved snapshot");
  await page.getByRole("tab", { name: "History" }).click();
  const restore = page.getByRole("button", { name: "Restore this version" }).first();
  const current = await source(harness, attemptId);
  await putSource(attemptId, "SERVER ACTION VERSION\n", current.etag);
  requestPolicy.expectHttpError(409);
  await restore.click();
  const dialog = page.getByRole("dialog");
  await dialog.getByRole("button", { name: "Restore version" }).click();
  await expect(saveStatus(page)).toHaveText("Conflict — choose a version");
  await expect(page.locator(".source-conflict")).toContainText("SERVER ACTION VERSION");
  await page.getByRole("button", { name: "Copy local version" }).click();
  await expect(saveStatus(page)).toHaveText("Saved snapshot");
  expect((await source(harness, attemptId)).content).toContain("# restore conflict local");
});

test("renders bounded candidate-only history", async ({ page }) => {
  const started = await startAttempt(page);
  await append(page, `\n# history candidate ${"x".repeat(700)} HIDDEN`);
  await expect(saveStatus(page)).toHaveText("Saved snapshot");
  await append(page, "\n# history successor");
  await expect(saveStatus(page)).toHaveText("Saved snapshot");

  await page.getByRole("tab", { name: "History" }).click();
  const history = page.locator(".history-list");
  await expect(history.locator(".history-item")).toHaveCount(2);
  expect(await history.locator("pre").evaluateAll((items) =>
    items.every((item) => item.textContent.length <= 512),
  )).toBe(true);
  await expect(history).toContainText("save ·");
  for (const forbidden of ["event", "test", "reference", "FETCH_ONLY"]) {
    await expect(history).not.toContainText(forbidden);
  }
  expect((await source(harness, started.data.session.attempt_id)).content)
    .toContain("# history successor");
});

test("confirms restore and reset, flushing each edit before CAS actions", async ({
  page,
}) => {
  const started = await startAttempt(page);
  const attemptId = started.data.session.attempt_id;
  await prepareRestoreReset(page);
  await page.getByRole("tab", { name: "History" }).click();
  const restore = page.getByRole("button", { name: "Restore this version" }).first();
  const dialog = page.getByRole("dialog");
  await cancelRestore(page, restore, dialog);
  await flushRestore(page, restore, dialog);
  const reset = page.getByRole("button", { name: "Reset" });
  await flushReset(page, reset, dialog);
  expect((await source(harness, attemptId)).content).toBe(started.data.source.content);
});

async function prepareRestoreReset(page) {
  await append(page, "\n# restore candidate");
  await expect(saveStatus(page)).toHaveText("Saved snapshot");
  await append(page, "\n# current candidate");
  await expect(saveStatus(page)).toHaveText("Saved snapshot");
}

async function cancelRestore(page, restore, dialog) {
  await restore.click();
  await expect(dialog).toContainText("Restore candidate version");
  await expect(dialog).toHaveAccessibleName("Restore candidate version");
  await expect(dialog).toHaveAccessibleDescription(
    "This replaces the current server source with the selected candidate version. Your current source must be saved first.",
  );
  await dialog.getByRole("button", { name: "Cancel" }).click();
  await expect(dialog).toBeHidden();
  await expect(restore).toBeFocused();
}

async function flushRestore(page, restore, dialog) {
  await append(page, "\n# pending restore flush");
  const restoreRequests = trackMutations(page);
  const restoreResponse = page.waitForResponse((response) =>
    new URL(response.url()).pathname === "/api/source/restore" &&
    response.request().method() === "POST",
  );
  await restore.click();
  await dialog.getByRole("button", { name: "Restore version" }).click();
  await restoreResponse;
  expect(restoreRequests.map((request) => new URL(request.url()).pathname))
    .toEqual(["/api/source", "/api/source/restore"]);
  expect(restoreRequests[1].headers()["if-match"]).toBe(
    etagFor(restoreRequests[0].postDataJSON().content),
  );
}

async function flushReset(page, reset, dialog) {
  await append(page, "\n# pending reset flush");
  const resetRequests = trackMutations(page);
  await reset.click();
  await expect(dialog).toContainText("Reset candidate source");
  await expect(dialog).toHaveAccessibleName("Reset candidate source");
  await expect(dialog).toHaveAccessibleDescription(
    "This permanently replaces the current source with the attempt baseline. Your current source must be saved first.",
  );
  await dialog.getByRole("button", { name: "Cancel" }).click();
  await expect(dialog).toBeHidden();
  await expect(reset).toBeFocused();
  await reset.click();
  const resetResponse = page.waitForResponse((response) =>
    new URL(response.url()).pathname === "/api/source/reset" &&
    response.request().method() === "POST",
  );
  await dialog.getByRole("button", { name: "Reset source" }).click();
  await resetResponse;
  expect(resetRequests.map((request) => new URL(request.url()).pathname))
    .toEqual(["/api/source", "/api/source/reset"]);
  expect(resetRequests[1].headers()["if-match"]).toBe(
    etagFor(resetRequests[0].postDataJSON().content),
  );
}

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

function trackMutations(page) {
  const requests = [];
  page.on("request", (request) => {
    if (["PUT", "POST"].includes(request.method()) &&
        new URL(request.url()).pathname.startsWith("/api/source")) {
      requests.push(request);
    }
  });
  return requests;
}

async function source(server, attemptId) {
  const response = await directRequest(
    server,
    `/api/source?attempt_id=${encodeURIComponent(attemptId)}`,
  );
  return response.document.data;
}

async function putSource(attemptId, content, etag) {
  return directRequest(
    harness,
    `/api/source?attempt_id=${encodeURIComponent(attemptId)}`,
    { method: "PUT", content, etag },
  );
}

async function directRequest(server, path, options = {}) {
  const headers = {
    "X-Simulator-Token": server.token,
  };
  if (options.method && options.method !== "GET") {
    headers.Origin = server.origin;
    headers["Content-Type"] = "application/json";
    headers["If-Match"] = options.etag;
  }
  const response = await fetch(`${server.origin}${path}`, {
    method: options.method || "GET",
    headers,
    body: options.content === undefined
      ? undefined
      : JSON.stringify({ content: options.content }),
  });
  return {
    status: response.status,
    etag: response.headers.get("etag"),
    document: await response.json(),
  };
}

function etagFor(content) {
  return `sha256:${createHash("sha256").update(content).digest("hex")}`;
}
