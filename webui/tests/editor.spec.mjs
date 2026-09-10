import { expect, test } from "@playwright/test";
import {
  installOfflineRequestPolicy,
  startFixtureServer,
} from "./browser_harness.mjs";

let harness;
let requestPolicy;
test.beforeEach(async ({ page }) => {
  try {
    harness = await startFixtureServer();
    requestPolicy = installOfflineRequestPolicy(page, harness);
  } catch (error) {
    const currentHarness = harness;
    harness = undefined;
    requestPolicy = undefined;
    if (currentHarness) await currentHarness.close();
    throw error;
  }
});
test.afterEach(async () => {
  const currentHarness = harness;
  const currentRequestPolicy = requestPolicy;
  harness = undefined;
  requestPolicy = undefined;
  try {
    if (currentRequestPolicy) await currentRequestPolicy.assert();
  } finally {
    if (currentHarness) await currentHarness.close();
  }
});
async function confirmStart(page, mode = "full") {
  await expect(page.locator(".entry")).toBeVisible();
  await page
    .getByRole("radio", {
      name: new RegExp(mode === "drill" ? "Focused drill" : "Full assessment"),
    })
    .check();
  await page.getByRole("button", { name: "Start practice" }).click();
  await expect(page.getByRole("dialog")).toBeVisible();
  await page.getByRole("button", { name: "Confirm and start" }).click();
}
test("loads Monaco under an explicit offline same-origin policy", async ({ page }) => {
  const requests = [];
  let attemptRequests = 0;
  page.on("request", (request) => {
    if (new URL(request.url()).pathname === "/api/attempts") attemptRequests += 1;
  });
  page.on("request", (request) => requests.push(request.url()));
  const shellResponse = await page.goto(`${harness.origin}/#token=${harness.token}`);
  assertShellHeaders(shellResponse);
  await verifyEntryAndDialog(page, () => attemptRequests);
  await confirmStart(page, "drill");
  expect(attemptRequests).toBe(1);
  await expect(page.locator(".status")).toHaveText(/Python editor ready/);
  await expect(page.locator("header")).toContainText("drill format");
  await expect(page.locator("header")).toContainText("Server deadline:");
  await expect(page.locator(".editor")).toBeVisible();
  await expect(page.locator(".fallback")).toBeHidden();
  await page.locator(".editor").click();
  await page.keyboard.type("# keyboard-only edit");
  await expect(page.locator(".sr-status")).toHaveText("Unsaved local edits");
  await verifyWorkersAndManifest(page);
  await verifyFont(page);
  await requestPolicy.assert();
  expect(requests.some((url) => url.includes("worker"))).toBe(true);
});

function assertShellHeaders(response) {
  expect(response.headers()["content-security-policy"]).toContain("worker-src 'self'");
  expect(response.headers()["x-content-type-options"]).toBe("nosniff");
  expect(response.headers()["cross-origin-resource-policy"]).toBe("same-origin");
  expect(response.headers()["referrer-policy"]).toBe("no-referrer");
  expect(response.headers()["permissions-policy"]).toContain("camera=()");
}

async function verifyEntryAndDialog(page, requestCount) {
  await expect(page.getByRole("heading", { name: "File Storage" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Four-level outline" })).toBeVisible();
  await expect(page.getByRole("radio", { name: /Full assessment/ })).toBeVisible();
  await page.getByRole("radio", { name: /Focused drill/ }).check();
  await page.getByRole("button", { name: "Start practice" }).click();
  const dialog = page.getByRole("dialog");
  await expect(dialog).toBeVisible();
  const labelledBy = await dialog.getAttribute("aria-labelledby");
  const describedBy = await dialog.getAttribute("aria-describedby");
  expect(labelledBy).toBeTruthy();
  expect(describedBy).toBeTruthy();
  await expect(page.locator(`#${labelledBy}`)).toHaveText("Confirm start");
  await expect(page.locator(`#${describedBy}`)).toContainText("timer begins immediately");
  expect(requestCount()).toBe(0);
  await page.getByRole("button", { name: "Cancel" }).click();
  expect(requestCount()).toBe(0);
}

async function verifyWorkersAndManifest(page) {
  const configured = await page.evaluate(() => {
    const environment = globalThis.MonacoEnvironment;
    const urls = ["editor", "python"].map((label) =>
      environment.getWorkerUrl("", label),
    );
    globalThis.__testWorkers = urls.map((url) => new Worker(url, { type: "module" }));
    return urls;
  });
  await expect.poll(() => page.workers().length).toBeGreaterThan(0);
  const manifest = await page.evaluate(() => fetch("/manifest.json").then((response) => response.json()));
  expect(configured).toHaveLength(2);
  for (const workerUrl of configured) {
    const worker = new URL(workerUrl);
    expect(worker.origin).toBe(harness.origin);
    expect(manifest[worker.pathname.slice(1)]).toBeDefined();
  }
  const required = ["index.html", "manifest.json", ...Object.keys(manifest).filter(
    (name) => /^(?:app|styles)-[A-Za-z0-9_-]+\.(?:js|css)$/.test(name),
  ), ...configured.map((url) => new URL(url).pathname.slice(1))];
  const lazy = Object.keys(manifest).filter((name) =>
    /^(?:app|styles)\.(?:js|css)$/.test(name) ||
    name.endsWith(".ttf") ||
    ["ASSET_PROVENANCE.txt", "NOTICE.txt", "favicon.svg"].includes(name),
  );
  await requestPolicy.assertManifestResources(manifest, required, lazy);
  await assertForbiddenAssetBytes(page, Object.keys(manifest));
}

async function assertForbiddenAssetBytes(page, names) {
  const matches = await page.evaluate(async (assetNames) => {
    const forbidden = [
      "FETCH_ONLY",
      "codesignal-fixtures",
      "assessment/file_storage",
      "/node_modules/",
      ".cache/",
      "playwright-report",
      "/Users/",
      "/tmp/",
      "file:///Users/",
      "file:///private/var",
      "BEGIN PRIVATE KEY",
    ];
    const textAssets = assetNames.filter((name) => !name.endsWith(".ttf"));
    const encoded = forbidden.map((value) => new TextEncoder().encode(value));
    const contains = (body, needle) => {
      for (let index = 0; index <= body.length - needle.length; index += 1) {
        if (needle.every((byte, offset) => body[index + offset] === byte)) return true;
      }
      return false;
    };
    const results = [];
    for (const name of textAssets) {
      const body = new Uint8Array(await fetch(`/${name}`).then((response) => response.arrayBuffer()));
      encoded.forEach((needle, index) => {
        if (contains(body, needle)) results.push(`${name}:${forbidden[index]}`);
      });
    }
    return results;
  }, names);
  expect(matches).toEqual([]);
}

async function verifyFont(page) {
  const manifest = await page.evaluate(() => fetch("/manifest.json").then((response) => response.json()));
  const fontName = Object.keys(manifest).find((name) => name.endsWith(".ttf"));
  expect(fontName).toBeDefined();
  expect(manifest[fontName].media_type).toBe("font/ttf");
  const fontResponse = await page.evaluate((name) =>
    fetch(`/${name}`).then((response) => ({
      contentType: response.headers.get("content-type"),
      nosniff: response.headers.get("x-content-type-options"),
    })), fontName);
  expect(fontResponse).toEqual({
    contentType: "font/ttf",
    nosniff: "nosniff",
  });
}
test("a captured capability outranks readable stale storage when storage write fails", async ({ page }) => {
  await page.addInitScript(() => {
    const staleStorage = {
      getItem() {
        return "stale-token";
      },
      setItem() {
        throw new Error("storage write failed for test");
      },
    };
    Object.defineProperty(window, "sessionStorage", {
      configurable: true,
      get() {
        return staleStorage;
      },
    });
  });
  await page.goto(`${harness.origin}/#token=${harness.token}`);
  await confirmStart(page);
  await expect(page.locator(".status")).toHaveText(/Python editor ready/);
  const view = new URL(page.url());
  expect(view.origin).toBe(harness.origin);
  const fragment = new URLSearchParams(view.hash.slice(1));
  expect([...fragment.keys()].sort()).toEqual(["attempt_id", "level", "tab"]);
  expect(fragment.get("token")).toBeNull();
  expect(fragment.get("attempt_id")).toBe(
    await page.locator("main").getAttribute("data-attempt-id"),
  );
  expect(fragment.get("level")).toBe("1");
  expect(fragment.get("tab")).toBe("description");
});
test("a stored capability remains usable after reload", async ({ page }) => {
  await page.goto(`${harness.origin}/#token=${harness.token}`);
  await confirmStart(page);
  await expect(page.locator(".status")).toHaveText(/Python editor ready/);
  const attemptId = await page.locator("main").getAttribute("data-attempt-id");
  let postCount = 0;
  page.on("request", (request) => {
    if (request.method() === "POST") postCount += 1;
  });
  await page.reload();
  await expect(page.locator(".entry")).toBeVisible();
  await expect(page.locator("main")).toHaveAttribute(
    "data-active-attempt-id",
    attemptId,
  );
  await page.getByRole("button", { name: "Reconnect to active session" }).click();
  await expect(page.locator(".status")).toHaveText(/Python editor ready/);
  await expect(page.locator("main")).toHaveAttribute("data-attempt-id", attemptId);
  expect(postCount).toBe(0);
});
test("keeps an exact read-only fallback when Monaco initialization fails", async ({ page }) => {
  requestPolicy.forceMonacoInitializationFailure();
  const mutationRequests = [];
  page.on("request", (request) => {
    const url = new URL(request.url());
    if (url.pathname.startsWith("/api/") && request.method() !== "GET") {
      mutationRequests.push(`${request.method()} ${url.pathname}`);
    }
  });
  await page.goto(`${harness.origin}/#token=${harness.token}`);
  const startResponsePromise = page.waitForResponse(
    (response) =>
      new URL(response.url()).pathname === "/api/attempts" &&
      response.request().method() === "POST",
  );
  await confirmStart(page);
  const startResponse = await startResponsePromise;
  const startDocument = await startResponse.json();
  const candidateSource = startDocument.data.source.content;
  await verifyReadOnlyFallback(page, candidateSource);
  await verifyFallbackWorkers(page);
  expect(mutationRequests).toEqual(["POST /api/attempts"]);
});

async function verifyReadOnlyFallback(page, candidateSource) {
  await expect(page.locator(".status")).toHaveText(/read-only fallback/);
  await expect(page.locator(".editor")).toBeHidden();
  await expect(page.locator(".fallback")).toBeVisible();
  await expect(page.locator(".fallback")).toHaveAttribute("readonly", "");
  await expect(page.locator(".fallback")).toHaveValue(candidateSource);
  const controls = await page.locator(
    '[data-mutation="true"]',
  ).evaluateAll((items) => items.filter((control) =>
    !control.hasAttribute("disabled") &&
    control.getAttribute("aria-disabled") !== "true",
  ));
  expect(controls).toHaveLength(0);
  await expect(page.getByRole("button", { name: "Skip" })).toBeEnabled();
  await expect(page.getByRole("button", { name: "Next" })).toBeEnabled();
}

async function verifyFallbackWorkers(page) {
  const workerUrls = await page.evaluate(() =>
    ["editor", "python"].map((label) =>
      globalThis.MonacoEnvironment.getWorkerUrl("", label),
    ),
  );
  const manifest = await page.evaluate(() =>
    fetch("/manifest.json").then((response) => response.json()),
  );
  for (const workerUrl of workerUrls) {
    const worker = new URL(workerUrl);
    expect(worker.origin).toBe(harness.origin);
    expect(manifest[worker.pathname.slice(1)]).toBeDefined();
  }
}

function interceptApiError(path, status, code, message) {
  requestPolicy.intercept(path, {
    status,
    contentType: "application/json",
    body: JSON.stringify({
      schema_version: "web/v1",
      ok: false,
      error: { code, message },
    }),
  });
}

function assertSafeActionableText(text, expected) {
  expect(text).toContain(expected);
  expect(text).not.toMatch(/(?:\/Users\/|\/tmp\/|browser-assessment-app|attempts\/)/);
}

test("renders a safe repair message when the selected fixture is missing", async ({ page }) => {
  interceptApiError(
    "/api/attempts",
    404,
    "session_unavailable",
    "fixture missing at /Users/private/workspace/.cache",
  );
  await page.goto(`${harness.origin}/#token=${harness.token}`);
  const response = page.waitForResponse(
    (item) => new URL(item.url()).pathname === "/api/attempts",
  );
  await confirmStart(page);
  expect((await response).status()).toBe(404);
  const message = await page.locator(".status").innerText();
  assertSafeActionableText(message, "fixture or selected session is unavailable");
});

test("renders a safe repair message for invalid bootstrap data", async ({ page }) => {
  requestPolicy.intercept("/api/bootstrap", {
    status: 200,
    contentType: "application/json",
    body: JSON.stringify({ schema_version: "web/v1", ok: true, data: {} }),
  });
  await page.goto(`${harness.origin}/#token=${harness.token}`);
  const message = await page.locator(".error-message").innerText();
  assertSafeActionableText(message, "assessment entry data is invalid");
});

test("renders a bounded internal failure with a safe recovery action", async ({ page }) => {
  requestPolicy.intercept("/api/bootstrap", {
    status: 500,
    contentType: "application/json",
    body: JSON.stringify({
      schema_version: "web/v1",
      ok: false,
      error: {
        code: "internal_error",
        message: "Traceback at /Users/private/source.py:42\nsecret test bytes",
      },
    }),
  });
  await page.goto(`${harness.origin}/#token=${harness.token}`);
  const message = await page.locator(".error-message").innerText();
  assertSafeActionableText(message, "could not be loaded safely");
  await expect(page.getByRole("button", { name: "Reload local simulator" })).toBeVisible();
  expect(message).not.toMatch(/Traceback|secret test bytes|source\.py/);
});

test("renders a safe conflict message when a start is already active", async ({ page }) => {
  interceptApiError(
    "/api/attempts",
    423,
    "lifecycle_locked",
    "active attempt is already selected at /Users/private/attempts",
  );
  await page.goto(`${harness.origin}/#token=${harness.token}`);
  const response = page.waitForResponse(
    (item) => new URL(item.url()).pathname === "/api/attempts",
  );
  await confirmStart(page);
  expect((await response).status()).toBe(423);
  const message = await page.locator(".status").innerText();
  assertSafeActionableText(message, "active session is already selected");
});

test("renders a safe reconnect failure without posting or leaking paths", async ({ page }) => {
  await page.goto(`${harness.origin}/#token=${harness.token}`);
  await confirmStart(page);
  const attemptId = await page.locator("main").getAttribute("data-attempt-id");
  let postCount = 0;
  page.on("request", (request) => {
    if (request.method() === "POST") postCount += 1;
  });
  await page.reload();
  requestPolicy.intercept("/api/source", {
    status: 404,
    contentType: "application/json",
    body: JSON.stringify({
      schema_version: "web/v1",
      ok: false,
      error: {
        code: "session_unavailable",
        message: "source missing at /Users/private/workspace/attempts",
      },
    }),
  });
  const response = page.waitForResponse(
    (item) => new URL(item.url()).pathname === "/api/source",
  );
  await page.getByRole("button", { name: "Reconnect to active session" }).click();
  expect((await response).status()).toBe(404);
  const message = await page.locator(".error-message").innerText();
  assertSafeActionableText(message, "fixture or selected session is unavailable");
  expect(postCount).toBe(0);
});
