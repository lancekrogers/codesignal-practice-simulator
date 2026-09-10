import { expect, test } from "@playwright/test";
import {
  installOfflineRequestPolicy,
  startFixtureServer,
} from "./browser_harness.mjs";
import { EditorPage } from "./pages/editor_page.mjs";
import { timeResponse } from "./shell_test_support.mjs";

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

test("supports Python editing, autocomplete, find, and undo/redo offline", async ({
  page,
}) => {
  await startAttempt(page);
  const editor = page.locator(".monaco-editor");
  await expect(editor.locator(".line-numbers").first()).toBeVisible();
  await editor.click();
  await page.keyboard.press("Control+End");
  await page.keyboard.press("Enter");
  await page.keyboard.type("# browser edit");
  await expect(editor.locator(".view-lines")).toContainText("# browser edit");
  await page.keyboard.press(modifier("z"));
  await expect(editor.locator(".view-lines")).not.toContainText("# browser edit");
  await page.keyboard.press(modifier("Shift+z"));
  await expect(editor.locator(".view-lines")).toContainText("# browser edit");

  await page.keyboard.press("Escape");
  await page.keyboard.press(modifier("f"));
  await expect(page.locator(".find-widget")).toBeVisible();
  await page.keyboard.press("Escape");
  await page.keyboard.press("Control+Space");
  await expect(page.locator(".suggest-widget")).toBeVisible();
});

test("persists validated settings without storing source authority", async ({
  page,
}) => {
  await startAttempt(page);
  const editor = new EditorPage(page);
  await editor.openSettings();
  await editor.applySettings({
    selects: {
      Theme: "vs-light",
      "Font size": 18,
      "Tab size": 8,
    },
    checkboxes: {
      "Show minimap": true,
      "Wrap long lines": true,
      "Auto-close brackets": false,
    },
  });

  const stored = await page.evaluate(() =>
    JSON.parse(localStorage.getItem("simulator-editor-preferences")),
  );
  expect(stored).toEqual({
    version: 1,
    theme: "vs-light",
    fontSize: 18,
    tabSize: 8,
    minimap: true,
    wordWrap: true,
    autoClosingBrackets: false,
  });
  expect(stored).not.toHaveProperty("source");
  expect(stored).not.toHaveProperty("etag");

  await page.reload();
  await page.getByRole("button", { name: "Reconnect to active session" }).click();
  await expect(page.getByText("Python editor ready. Changes stay in this local browser."))
    .toBeVisible();
  await editor.openSettings();
  const restored = editor.settingsDialog();
  await expect(restored.getByLabel("Theme")).toHaveValue("vs-light");
  await expect(restored.getByLabel("Font size")).toHaveValue("18");
  await expect(restored.getByLabel("Tab size")).toHaveValue("8");
  await expect(restored.getByLabel("Show minimap")).toBeChecked();
  await expect(restored.getByLabel("Wrap long lines")).toBeChecked();
  await expect(restored.getByLabel("Auto-close brackets")).not.toBeChecked();

  await restored.getByLabel("Font size").evaluate((select) => {
    select.value = "99";
  });
  await restored.getByRole("button", { name: "Apply settings" }).click();
  await expect(restored.getByRole("alert")).toHaveText(
    "Choose valid values before applying settings.",
  );
  expect(await page.evaluate(() =>
    JSON.parse(localStorage.getItem("simulator-editor-preferences")).fontSize,
  )).toBe(18);
});

test("keeps the initial server source clean until the first edit", async ({ page }) => {
  await startAttempt(page);
  await expect(page.getByText("Saved snapshot", { exact: true })).toBeVisible();
  await page.locator(".monaco-editor").click();
  await page.keyboard.press("Control+End");
  await page.keyboard.type("\n# local edit");
  await expect(page.locator(".sr-status")).toHaveText("Unsaved local edits");
});

test("shows exact source in an actionable read-only fallback on initialization failure", async ({
  page,
}) => {
  requestPolicy.forceMonacoInitializationFailure();
  const startResponse = page.waitForResponse(
    (response) =>
      new URL(response.url()).pathname === "/api/attempts" &&
      response.request().method() === "POST",
  );
  await page.goto(`${harness.origin}/#token=${harness.token}`);
  await page.getByRole("button", { name: "Start practice" }).click();
  await page.getByRole("button", { name: "Confirm and start" }).click();
  const source = (await (await startResponse).json()).data.source.content;
  await expect(page.locator(".fallback")).toHaveValue(source);
  await expect(page.locator(".editor-pane > .status")).toContainText(
    "Reload the local simulator to retry",
  );
  await expect(page.getByRole("button", { name: "Settings" })).toBeDisabled();
  await expect(page.locator(".fallback")).toHaveAttribute("readonly", "");
});

test("preserves edited Monaco text and dirty state when a worker fails", async ({
  page,
}) => {
  const startResponse = page.waitForResponse(
    (response) =>
      new URL(response.url()).pathname === "/api/attempts" &&
      response.request().method() === "POST",
  );
  await startAttempt(page);
  const source = (await (await startResponse).json()).data.source.content;
  const edit = "# worker failure edit";
  const requests = [];
  page.on("request", (request) => {
    if (request.method() === "PUT" &&
        new URL(request.url()).pathname === "/api/source") {
      requests.push(request);
    }
  });
  const sourceHeld = requestPolicy.hold("/api/source");
  requestPolicy.intercept("/api/source", {
    status: 503,
    contentType: "application/json",
    body: JSON.stringify({
      schema_version: "web/v1",
      ok: false,
      error: { code: "unavailable", message: "synthetic save failure" },
    }),
  });
  requestPolicy.expectHttpError({
    method: "PUT",
    path: "/api/source",
    status: 503,
  });
  const saveRequest = page.waitForRequest(
    (request) =>
      new URL(request.url()).pathname === "/api/source" &&
      request.method() === "PUT",
  );
  await page.locator(".monaco-editor").click();
  await page.keyboard.press("Control+End");
  await page.keyboard.type(edit);
  await expect(page.locator(".sr-status")).toHaveText("Unsaved local edits");
  await saveRequest;
  await sourceHeld;
  await page.evaluate(() => {
    globalThis.__failureWorker = globalThis.MonacoEnvironment.getWorker("", "python");
  });
  await expect.poll(() => page.workers().length).toBeGreaterThan(0);
  await page.evaluate(() => {
    globalThis.__failureWorker.dispatchEvent(new ErrorEvent("error"));
  });
  requestPolicy.release("/api/source");
  await expect(page.locator(".fallback")).toHaveValue(`${source}${edit}`);
  expect(requests).toHaveLength(1);
  await expect(page.locator(".header-meta")).toContainText("Unsaved local edits");
  await expect(page.locator(".sr-status")).toHaveText("Unsaved local edits");
  await expect(page.locator(".fallback")).toHaveAttribute("readonly", "");
});

test("ignores a delayed worker error after attempt cleanup", async ({ page }) => {
  await page.clock.install();
  const startResponse = page.waitForResponse(
    (response) =>
      new URL(response.url()).pathname === "/api/attempts" &&
      response.request().method() === "POST",
  );
  await startAttempt(page);
  const started = await (await startResponse).json();
  const session = started.data.session;
  await page.evaluate(() => {
    globalThis.__staleWorker = globalThis.MonacoEnvironment.getWorker("", "python");
    globalThis.__staleEditorStatus = document.querySelector(".editor-pane > .status");
  });
  requestPolicy.intercept(
    `/api/time?attempt_id=${session.attempt_id}`,
    timeResponse({ ...session, status: "expired" }, started.data.time),
  );
  await page.clock.fastForward("00:15");
  await expect(page.getByText("Expired", { exact: true })).toBeVisible();
  await page.evaluate(() => {
    globalThis.__staleWorker.dispatchEvent(new ErrorEvent("error"));
  });
  expect(await page.evaluate(() => globalThis.__staleEditorStatus.textContent))
    .toBe("Python editor ready. Changes stay in this local browser.");
});

test("closes an open settings dialog before worker-failure cleanup removes it", async ({
  page,
}) => {
  await startAttempt(page);
  await page.getByRole("button", { name: "Settings" }).click();
  const dialog = page.getByRole("dialog", { name: "Editor settings" });
  await expect(dialog).toBeVisible();
  await page.evaluate(() => {
    globalThis.__failureWorker = globalThis.MonacoEnvironment.getWorker("", "python");
    globalThis.__dialogBeforeFailure = document.querySelector(".editor-settings");
  });
  await page.evaluate(() => {
    globalThis.__failureWorker.dispatchEvent(new ErrorEvent("error"));
  });
  await expect(dialog).toHaveCount(0);
  expect(await page.evaluate(() => ({
    activeConnected: document.activeElement?.isConnected,
    oldDialogConnected: globalThis.__dialogBeforeFailure.isConnected,
  }))).toEqual({ activeConnected: true, oldDialogConnected: false });
});

test("closes an open settings dialog before expiry rerenders the shell", async ({ page }) => {
  await page.clock.install();
  const startResponse = page.waitForResponse(
    (response) =>
      new URL(response.url()).pathname === "/api/attempts" &&
      response.request().method() === "POST",
  );
  await startAttempt(page);
  const started = await (await startResponse).json();
  const session = started.data.session;
  await page.getByRole("button", { name: "Settings" }).click();
  const dialog = page.getByRole("dialog", { name: "Editor settings" });
  await expect(dialog).toBeVisible();
  await page.evaluate(() => {
    globalThis.__dialogBeforeExpiry = document.querySelector(".editor-settings");
  });
  requestPolicy.intercept(
    `/api/time?attempt_id=${session.attempt_id}`,
    timeResponse({ ...session, status: "expired" }, started.data.time),
  );
  await page.clock.fastForward("00:15");
  await expect(page.getByText("Expired", { exact: true })).toBeVisible();
  await expect(dialog).toHaveCount(0);
  expect(await page.evaluate(() => ({
    activeConnected: document.activeElement?.isConnected,
    oldDialogConnected: globalThis.__dialogBeforeExpiry.isConnected,
  }))).toEqual({ activeConnected: true, oldDialogConnected: false });
});

test("rejects string tab sizes in stored editor preferences", async ({ page }) => {
  await page.addInitScript(() => {
    localStorage.setItem(
      "simulator-editor-preferences",
      JSON.stringify({
        version: 1,
        theme: "vs-dark",
        fontSize: 14,
        tabSize: "8",
        minimap: false,
        wordWrap: false,
        autoClosingBrackets: true,
      }),
    );
  });
  await startAttempt(page);
  await page.getByRole("button", { name: "Settings" }).click();
  await expect(page.getByRole("dialog", { name: "Editor settings" })
    .getByLabel("Tab size")).toHaveValue("4");
});

async function startAttempt(page) {
  await page.goto(`${harness.origin}/#token=${harness.token}`);
  await page.getByRole("button", { name: "Start practice" }).click();
  await page.getByRole("button", { name: "Confirm and start" }).click();
  await expect(page.getByText("Python editor ready. Changes stay in this local browser."))
    .toBeVisible();
}

function modifier(shortcut) {
  return `${process.platform === "darwin" ? "Meta" : "Control"}+${shortcut}`;
}
