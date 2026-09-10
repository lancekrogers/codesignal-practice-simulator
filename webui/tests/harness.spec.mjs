import { spawn, spawnSync } from "node:child_process";
import {
  access,
  mkdtemp,
  readdir,
  readFile,
  rm,
  symlink,
  writeFile,
} from "node:fs/promises";
import { chromium, expect, test } from "@playwright/test";
import { basename, join, relative } from "node:path";
import { tmpdir } from "node:os";
import { fileURLToPath } from "node:url";
import {
  FAILURE_ARTIFACT_REPORTER,
  LOCKED_CHROMIUM,
  PRIVACY_SAFE_REPORTER,
} from "../playwright.config.mjs";
import {
  installOfflineRequestPolicy,
  startFixtureServer,
} from "./browser_harness.mjs";
import {
  drainResponseScansForTest,
  RESPONSE_SCAN_BYTES,
  scanResponseForTest,
} from "./network_guard.mjs";
import { AssessmentPage } from "./pages/assessment_page.mjs";
import { EditorPage } from "./pages/editor_page.mjs";
import { EntryPage } from "./pages/entry_page.mjs";
import { OutputPage } from "./pages/output_page.mjs";
import { redactSensitiveText } from "./failure_artifacts.mjs";
import { OWNERSHIP_FAILURE_MESSAGE } from "./failure_artifacts_reporter.mjs";

const WEBUI_ROOT = fileURLToPath(new URL("..", import.meta.url));
const PLAYWRIGHT_CLI = fileURLToPath(new URL(
  "../node_modules/@playwright/test/cli.js",
  import.meta.url,
));
const HARNESS_FAILURE_PROBE_TOKEN = [
  "browser-fixture-token",
  "failure",
  "probe",
  "00000000000000000000000000000000",
].join("-");
const HARNESS_FAILURE_PROBE_SENTINELS = [
  HARNESS_FAILURE_PROBE_TOKEN,
  "/Users/lancerogers/private/diagnostic.py",
  "SYNTHETIC_PROMPT_CONTENT_SENTINEL",
  "SYNTHETIC_CANDIDATE_SOURCE_SENTINEL",
  "SYNTHETIC_RESPONSE_BODY_SENTINEL",
  "SYNTHETIC_REFERENCE_FETCH_ONLY_SENTINEL",
  "FETCH_ONLY",
];
const RESPONSE_SCAN_CAP = 100;

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

test("browser harness stays deterministic across bootstrap, restart, expiry, and submitted final state", async ({
  page,
}) => {
  expect(test.info().project.name).toBe(LOCKED_CHROMIUM.browserName);
  expect(chromium.executablePath()).toContain(`chromium-${LOCKED_CHROMIUM.revision}`);
  expect(page.context().browser()?.version()).toBe(LOCKED_CHROMIUM.version);
  const entry = new EntryPage(page);
  const assessment = new AssessmentPage(page);
  const editor = new EditorPage(page);
  const output = new OutputPage(page);

  const second = await startFixtureServer();
  try {
    expect(second.workspaceRoot).not.toBe(harness.workspaceRoot);
  } finally {
    await second.close();
  }

  const firstLoad = await bootstrapSnapshot(page, entry);
  const secondLoad = await bootstrapSnapshot(page, entry, true);
  expect(secondLoad).toEqual(firstLoad);
  const openerCallsBeforeRestart = await harness.browserOpenerCalls();
  expect(openerCallsBeforeRestart.every((origin) => origin === harness.origin))
    .toBe(true);

  await harness.restart();
  requestPolicy.refreshOrigin();

  const reopenedLoad = await bootstrapSnapshot(page, entry, true);
  expect(reopenedLoad).toEqual(firstLoad);
  assertSafeResponseScanState(requestPolicy);
  const openerCallsAfterRestart = await harness.browserOpenerCalls();
  expect(openerCallsAfterRestart.every((origin) => origin === harness.origin))
    .toBe(true);
  expect(openerCallsAfterRestart.length).toBeGreaterThan(
    openerCallsBeforeRestart.length,
  );

  await page.clock.install();
  await entry.choose("drill");
  await entry.openStartDialog();
  const startResponse = entry.confirmStartResponse();
  await entry.confirmStart();
  const started = await (await startResponse).json();
  await assessment.expectShell();
  await editor.expectReady();
  await expect(output.pane()).toBeVisible();
  const attemptId = started.data.session.attempt_id;
  expect(attemptId).toMatch(
    /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/iu,
  );
  expect((await harness.browserOpenerCalls()).every((origin) => origin === harness.origin))
    .toBe(true);
  await assessment.waitForState(attemptId, "active");
  await harness.setClock(started.data.session.deadline_at);
  await page.clock.fastForward("00:15");
  await assessment.waitForState(attemptId, "expired");
  await assessment.expectLifecycle("Expired");
  await expect(page.getByRole("button", { name: "Submit" })).toBeDisabled();
  assertSafeResponseScanState(requestPolicy);
  expect(requestPolicy.requestRecords().every(({ url }) =>
    new URL(url).origin === harness.origin,
  )).toBe(true);

  const submittedHarness = await startFixtureServer();
  const submittedPage = await page.context().newPage();
  const submittedPolicy = await installOfflineRequestPolicy(
    submittedPage,
    submittedHarness,
  );
  const submittedEntry = new EntryPage(submittedPage);
  const submittedAssessment = new AssessmentPage(submittedPage);
  const submittedEditor = new EditorPage(submittedPage);
  const submittedOutput = new OutputPage(submittedPage);
  try {
    await submittedEntry.open(submittedHarness.origin, submittedHarness.token);
    await submittedEntry.choose("drill");
    await submittedEntry.openStartDialog();
    const submittedStartResponse = submittedEntry.confirmStartResponse();
    await submittedEntry.confirmStart();
    const submittedStarted = await (await submittedStartResponse).json();
    const submittedAttemptId = submittedStarted.data.session.attempt_id;
    await submittedAssessment.expectShell();
    await submittedEditor.expectReady();
    await submittedAssessment.waitForState(submittedAttemptId, "active");

    const submitResponse = submittedPage.waitForResponse(
      (response) =>
        new URL(response.url()).pathname === "/api/submit" &&
        response.request().method() === "POST",
    );
    await submittedPage.getByRole("button", { name: "Submit" }).click();
    await submittedPage.getByRole("button", { name: "Submit attempt" }).click();
    const submitted = await (await submitResponse).json();
    expect(submitted.data.session.status).toBe("submitted");
    await submittedAssessment.waitForState(submittedAttemptId, "submitted");
    await submittedPage.reload();
    await expect(
      submittedPage.getByRole("button", { name: "View final session" }),
    ).toBeVisible();
    await submittedPage.getByRole("button", { name: "View final session" }).click();
    await submittedOutput.expectFinalResult(4, 4);
    await submittedAssessment.expectLifecycle("Submitted");
    assertSafeResponseScanState(submittedPolicy);
  } finally {
    try {
      await submittedPolicy.assert();
    } finally {
      await submittedPage.close();
      await submittedHarness.close();
    }
  }
});

test("denies an external browser request before network access", async ({ page }) => {
  const externalUrl = "https://example.invalid/blocked";
  requestPolicy.expectBlockedRequest(externalUrl);
  requestPolicy.expectBlockedConsoleError({
    method: "GET",
    url: externalUrl,
  });
  const blocked = await page.evaluate(async (url) => {
    try {
      await fetch(url);
      return false;
    } catch {
      return true;
    }
  }, externalUrl);
  expect(blocked).toBe(true);
});

test("rejects and records an external script request", async ({ page }) => {
  const externalUrl = "https://example.invalid/blocked-script.js";
  requestPolicy.expectBlockedRequest(externalUrl);
  requestPolicy.expectBlockedConsoleError({
    method: "GET",
    url: externalUrl,
  });
  await page.goto("about:blank");
  const result = await page.evaluate((url) => new Promise((resolve) => {
    const script = document.createElement("script");
    script.src = url;
    script.onload = () => resolve("loaded");
    script.onerror = () => resolve("blocked");
    document.head.append(script);
  }), externalUrl);
  expect(result).toBe("blocked");
  await expect.poll(() => requestPolicy.blockedRequestRecords()).toEqual([{
    method: "GET",
    resourceType: "script",
    url: externalUrl,
  }]);
});

test("rejects duplicate blocked requests beyond the declared count", async ({
  page,
}) => {
  const externalUrl = "https://example.invalid/blocked-duplicate";
  requestPolicy.expectBlockedRequest(externalUrl);
  requestPolicy.expectBlockedConsoleError({
    method: "GET",
    url: externalUrl,
    count: 2,
  });
  await page.goto("about:blank");
  await page.evaluate(async (url) => {
    await Promise.all([
      fetch(url).catch(() => undefined),
      fetch(url).catch(() => undefined),
    ]);
  }, externalUrl);
  let assertionError;
  try {
    await requestPolicy.assert();
  } catch (error) {
    assertionError = error;
  }
  expect(assertionError).toBeDefined();
  expect(assertionError.details).toMatchObject({
    label: "blocked requests",
    mismatches: [{
      expectation: { url: externalUrl, count: 1 },
      expectedCount: 1,
      actualCount: 2,
    }],
  });
  expect(assertionError.message).toContain('"actualCount":2');
  requestPolicy.expectBlockedRequest(externalUrl);
});

test("rejects and records an external WebSocket", async ({ page }) => {
  const externalUrl = "wss://example.invalid/blocked";
  requestPolicy.expectBlockedWebSocket({ url: externalUrl, count: 1 });
  await page.goto(`${harness.origin}/#token=${harness.token}`);
  const result = await page.evaluate((url) => new Promise((resolve) => {
    const socket = new WebSocket(url);
    socket.onerror = () => resolve("error");
    socket.onclose = () => resolve("closed");
  }), externalUrl);
  expect(["error", "closed"]).toContain(result);
  await expect.poll(() => requestPolicy.blockedWebSocketRecords()).toEqual([{
    url: externalUrl,
  }]);
});

test("rejects a same-loopback WebSocket on an unexpected port", async ({ page }) => {
  const localUrl = "ws://127.0.0.1:9/blocked";
  requestPolicy.expectBlockedWebSocket({ url: localUrl, count: 1 });
  await page.goto(`${harness.origin}/#token=${harness.token}`);
  const result = await page.evaluate((url) => new Promise((resolve) => {
    const socket = new WebSocket(url);
    socket.onerror = () => resolve("error");
    socket.onclose = () => resolve("closed");
  }), localUrl);
  expect(["error", "closed"]).toContain(result);
  await expect.poll(() => requestPolicy.blockedWebSocketRecords()).toEqual([{
    url: localUrl,
  }]);
});

test("allows a same-origin WebSocket through the policy when the fixture rejects it", async ({
  page,
}) => {
  const sameOrigin = new URL(harness.origin);
  sameOrigin.protocol = sameOrigin.protocol === "https:" ? "wss:" : "ws:";
  sameOrigin.pathname = "/unsupported-websocket";
  requestPolicy.expectConsoleError({
    message: `WebSocket connection to '${sameOrigin.href}' failed: ` +
      "Error during WebSocket handshake: Unexpected response code: 404",
    count: 1,
  });
  await page.goto(`${harness.origin}/#token=${harness.token}`);
  const result = await page.evaluate((url) => new Promise((resolve) => {
    const socket = new WebSocket(url);
    socket.onerror = () => resolve("error");
    socket.onclose = () => resolve("closed");
  }), sameOrigin.href);
  expect(["error", "closed"]).toContain(result);
  expect(requestPolicy.blockedWebSocketRecords()).toEqual([]);
});

test("scans only bounded synthetic response prefixes without retaining content", async ({
  page,
}) => {
  const sentinel = "BROWSER_HARNESS_FORBIDDEN_RESPONSE_SENTINEL";
  requestPolicy.expectForbiddenResponse("/favicon.svg", sentinel);
  requestPolicy.intercept("/favicon.svg", {
    status: 200,
    contentType: "image/svg+xml",
    body: `<svg>${sentinel}</svg>`,
  });
  await page.goto(`${harness.origin}/#token=${harness.token}`);
  await page.evaluate(() => fetch("/favicon.svg").then((response) => response.ok));
  await expect.poll(() => requestPolicy.forbiddenResponseMatches()).toEqual([{
    sentinel,
    url: `${harness.origin}/favicon.svg`,
  }]);
});

test("scans bounded intercepted bytes before fast responses finish", async ({
  page,
}) => {
  const paths = Array.from(
    { length: 8 },
    (_, index) => `/favicon.svg?fast=${index}`,
  );
  requestPolicy.intercept("/favicon.svg", {
    status: 200,
    contentType: "text/plain",
    body: "fast same-origin response",
  });
  await page.goto(`${harness.origin}/#token=${harness.token}`);
  await page.evaluate((urls) => Promise.all(
    urls.map((url) => fetch(url).then((response) => response.text())),
  ), paths);

  await expect.poll(() => requestPolicy.responseScanDiagnostics()
    .filter(({ path }) => path.startsWith("/favicon.svg?fast=")).length
  ).toBe(paths.length);
  expect(requestPolicy.responseScanDiagnostics()
    .filter(({ path }) => path.startsWith("/favicon.svg?fast="))
    .every(({ scanMechanism, streamEstablished }) =>
      scanMechanism === "intercepted-body" &&
      !streamEstablished
    )).toBe(true);
  expect(requestPolicy.responseScanViolations()).toEqual([]);
});

test("scans each repeated same-URL intercepted response", async ({ page }) => {
  const path = "/favicon.svg?repeated=1";
  const sentinel = "BROWSER_HARNESS_FORBIDDEN_RESPONSE_SENTINEL";
  requestPolicy.expectForbiddenResponse(path, sentinel);
  await page.goto(`${harness.origin}/#token=${harness.token}`);
  requestPolicy.intercept(path, {
    status: 200,
    contentType: "text/plain",
    body: "safe first response",
  });
  await page.evaluate(
    (url) => fetch(url).then((response) => response.text()),
    path,
  );
  requestPolicy.intercept(path, {
    status: 200,
    contentType: "text/plain",
    body: `forbidden later response: ${sentinel}`,
  });
  await page.evaluate(
    (url) => fetch(url).then((response) => response.text()),
    path,
  );

  await expect.poll(() => requestPolicy.forbiddenResponseMatches()).toEqual([{
    sentinel,
    url: `${harness.origin}${path}`,
  }]);
  expect(requestPolicy.responseScanDiagnostics()
    .filter((diagnostic) => diagnostic.path === path)
  ).toEqual([
    expect.objectContaining({ scanMechanism: "intercepted-body" }),
    expect.objectContaining({ scanMechanism: "intercepted-body" }),
  ]);
});

test("fails closed past the intercepted response scan cap without retaining the body", async ({
  page,
}) => {
  const path = "/favicon.svg?scan-budget";
  const exhaustedPath = `${path}=${RESPONSE_SCAN_CAP}`;
  const unscannedSentinel = "BROWSER_HARNESS_FORBIDDEN_RESPONSE_SENTINEL";
  requestPolicy.expectResponseScanViolation({
    method: "GET",
    path: exhaustedPath,
    status: 200,
    reason: "scan-budget-exhausted",
    count: 1,
  });
  requestPolicy.intercept("/favicon.svg", {
    status: 200,
    contentType: "text/plain",
    body: "bounded response",
  });

  await page.evaluate(async ({ origin, path, count }) => {
    for (let index = 0; index < count; index += 1) {
      await fetch(`${origin}${path}=${index}`, { mode: "no-cors" });
    }
  }, { origin: harness.origin, path, count: RESPONSE_SCAN_CAP });
  requestPolicy.intercept("/favicon.svg", {
    status: 200,
    contentType: "text/plain",
    body: unscannedSentinel,
  });
  await page.evaluate(
    (url) => fetch(url, { mode: "no-cors" }),
    `${harness.origin}${exhaustedPath}`,
  );
  await requestPolicy.assert();

  expect(requestPolicy.responseScanDiagnostics()).toHaveLength(
    RESPONSE_SCAN_CAP,
  );
  expect(requestPolicy.responseScanViolations()).toEqual([
    expect.objectContaining({
      path: exhaustedPath,
      reason: "scan-budget-exhausted",
    }),
  ]);
  expect(requestPolicy.forbiddenResponseMatches()).toEqual([]);
  expect(JSON.stringify({
    diagnostics: requestPolicy.responseScanDiagnostics(),
    violations: requestPolicy.responseScanViolations(),
  })).not.toContain(unscannedSentinel);
});

test("does not let a settled ordinary same-URL response lend intercepted coverage", async ({
  page,
}) => {
  const path = "/api/bootstrap?mixed-settled=1";
  const url = `${harness.origin}${path}`;
  requestPolicy.expectHttpError({
    method: "GET",
    path,
    status: 400,
  });
  await page.goto(`${harness.origin}/#token=${harness.token}`);
  await page.evaluate(
    async ({ requestUrl, token }) => {
      const response = await fetch(requestUrl, {
        headers: { "X-Simulator-Token": token },
      });
      await response.text();
    },
    { requestUrl: url, token: harness.token },
  );
  await expect.poll(() => requestPolicy.responseScanDiagnostics()
    .filter((diagnostic) => diagnostic.path === path)
  ).toHaveLength(1);
  const [ordinaryScan] = requestPolicy.responseScanDiagnostics()
    .filter((diagnostic) => diagnostic.path === path);
  expect(ordinaryScan.scanMechanism).toBe("network-stream");

  requestPolicy.intercept(path, {
    status: 200,
    contentType: "text/plain",
    body: "covered intercepted response",
  });
  await page.evaluate(
    (requestUrl) => fetch(requestUrl).then((response) => response.text()),
    url,
  );
  await requestPolicy.assert();

  expect(requestPolicy.responseScanDiagnostics()
    .filter((diagnostic) => diagnostic.path === path)
  ).toEqual([
    ordinaryScan,
    expect.objectContaining({ scanMechanism: "intercepted-body" }),
  ]);
});

test("does not let an inflight ordinary same-URL response lend intercepted coverage", async ({
  page,
}) => {
  const path = "/api/bootstrap?mixed-inflight=1";
  const url = `${harness.origin}${path}`;
  const metadataPath = "/api/bootstrap?mixed-inflight-metadata=1";
  requestPolicy.expectHttpError({
    method: "GET",
    path: metadataPath,
    status: 400,
  });
  requestPolicy.expectHttpError({
    method: "GET",
    path,
    status: 400,
  });
  await page.goto(`${harness.origin}/#token=${harness.token}`);
  await page.evaluate(
    async ({ requestUrl, token }) => {
      const response = await fetch(requestUrl, {
        headers: { "X-Simulator-Token": token },
      });
      await response.text();
    },
    {
      requestUrl: `${harness.origin}${metadataPath}`,
      token: harness.token,
    },
  );
  await expect.poll(() => requestPolicy.responseScanDiagnostics()
    .find((diagnostic) => diagnostic.path === metadataPath)
  ).toBeDefined();
  const ordinaryLength = requestPolicy.responseScanDiagnostics()
    .find((diagnostic) => diagnostic.path === metadataPath).declaredLength;
  const interceptedBody = "covered inflight intercepted response";
  expect(Buffer.byteLength(interceptedBody)).not.toBe(ordinaryLength);

  const firstHeld = requestPolicy.hold(path);
  const ordinaryFetch = page.evaluate(
    ({ requestUrl, token }) => fetch(requestUrl, {
      headers: { "X-Simulator-Token": token },
    }).then((response) => response.text()),
    { requestUrl: url, token: harness.token },
  );
  await firstHeld;
  requestPolicy.intercept(path, {
    status: 200,
    contentType: "text/plain",
    body: interceptedBody,
  });
  const interceptedRequest = page.waitForRequest((request) =>
    request.url() === url
  );
  const interceptedFetch = page.evaluate(
    (requestUrl) => fetch(requestUrl).then((response) => response.text()),
    url,
  );
  await interceptedRequest;
  requestPolicy.release(path);
  await Promise.all([ordinaryFetch, interceptedFetch]);
  await requestPolicy.assert();

  expect(requestPolicy.responseScanDiagnostics()
    .filter((diagnostic) => diagnostic.path === path)
  ).toEqual(expect.arrayContaining([
    expect.objectContaining({
      declaredLength: ordinaryLength,
      scanMechanism: "network-stream",
    }),
    expect.objectContaining({
      declaredLength: Buffer.byteLength(interceptedBody),
      scanMechanism: "intercepted-body",
    }),
  ]));
  expect(requestPolicy.responseScanDiagnostics()
    .filter((diagnostic) => diagnostic.path === path)
  ).toHaveLength(2);
});

test("does not let an independently mocked same-URL response borrow coverage", async ({
  page,
}) => {
  const path = "/api/bootstrap?independent-coverage=1";
  const url = `${harness.origin}${path}`;
  await page.goto(`${harness.origin}/#token=${harness.token}`);
  requestPolicy.intercept(path, {
    status: 200,
    contentType: "text/plain",
    body: "covered intercepted response",
  });
  await page.evaluate(
    (requestUrl) => fetch(requestUrl).then((response) => response.text()),
    url,
  );
  requestPolicy.clearIntercept(path);
  await page.route(url, (route) => route.fulfill({
    status: 204,
    headers: {
      "x-browser-harness-intercepted-coverage": "independent-marker",
    },
  }));
  await page.evaluate(
    (requestUrl) => fetch(requestUrl).then((response) => response.text()),
    url,
  );
  await requestPolicy.assert();

  expect(requestPolicy.responseScanSkips()).toContainEqual(
    expect.objectContaining({
      path,
      reason: "response-has-no-body",
      status: 204,
    }),
  );
});

test("scans effective JSON content types before fulfillment", async ({ page }) => {
  const sentinel = "BROWSER_HARNESS_FORBIDDEN_RESPONSE_SENTINEL";
  const jsonPath = "/favicon.svg?json-body=1";
  const overridePath = "/favicon.svg?content-type-override=1";
  requestPolicy.expectForbiddenResponse(jsonPath, sentinel);
  requestPolicy.expectForbiddenResponse(overridePath, sentinel);
  await page.goto(`${harness.origin}/#token=${harness.token}`);
  requestPolicy.intercept(jsonPath, {
    status: 200,
    json: { message: sentinel },
  });
  requestPolicy.intercept(overridePath, {
    status: 200,
    headers: { "Content-Type": "application/octet-stream" },
    contentType: "application/json",
    body: JSON.stringify({ message: sentinel }),
  });

  await page.evaluate(
    (paths) => Promise.all(paths.map((path) =>
      fetch(path).then((response) => response.json())
    )),
    [jsonPath, overridePath],
  );

  await expect.poll(() => requestPolicy.forbiddenResponseMatches()
    .sort((left, right) => left.url.localeCompare(right.url))
  ).toEqual([
    { sentinel, url: `${harness.origin}${overridePath}` },
    { sentinel, url: `${harness.origin}${jsonPath}` },
  ]);
});

test("rejects unsupported intercepted response options", () => {
  expect(() => requestPolicy.intercept("/unsupported-path", {
    path: "synthetic-response.txt",
  })).toThrow("bounded inline body or JSON");
  expect(() => requestPolicy.intercept("/unsupported-response", {
    response: {},
  })).toThrow("bounded inline body or JSON");
  expect(() => requestPolicy.intercept("/ambiguous-body", {
    body: "body",
    json: { message: "json" },
  })).toThrow("cannot specify both body and JSON");
  expect(() => requestPolicy.intercept("/unsupported-body", {
    body: { message: "not inline bytes" },
  })).toThrow("body must be bytes or text");
});

test("waits for response scans queued while assertion is draining", async () => {
  const scans = new Set();
  const violations = [];
  let resolveFirst;
  let resolveSecond;
  const first = new Promise((resolve) => {
    resolveFirst = resolve;
  });
  const second = new Promise((resolve) => {
    resolveSecond = resolve;
  });
  const track = (pending) => {
    const tracked = pending.finally(() => scans.delete(tracked));
    scans.add(tracked);
  };
  track(first);
  const assertion = (async () => {
    await drainResponseScansForTest(scans);
    expect(violations).toEqual([]);
  })();
  let assertionSettled = false;
  assertion.finally(() => {
    assertionSettled = true;
  }).catch(() => undefined);
  track(second);

  resolveFirst();
  await new Promise((resolve) => setImmediate(resolve));
  expect(assertionSettled).toBe(false);
  violations.push({ reason: "synthetic deferred violation" });
  resolveSecond();
  await expect(assertion).rejects.toThrow();
});

test("does not retrieve bodies with unsafe or ambiguous declared lengths", async () => {
  const cases = [
    {
      contentLength: String(RESPONSE_SCAN_BYTES + 1),
      reason: "content-length-exceeds-policy",
    },
    { contentLength: undefined, reason: "content-length-missing" },
    { contentLength: "not-a-length", reason: "content-length-invalid" },
    { contentLength: "8, 9", reason: "content-length-conflicting" },
  ];
  for (const { contentLength, reason } of cases) {
    const headers = { "content-type": "text/plain" };
    if (contentLength !== undefined) headers["content-length"] = contentLength;
    const fake = fakeResponse({
      headers,
      body: () => {
        throw new Error("body must not be retrieved");
      },
    });
    const result = await scanResponseForTest(fake.response);
    expect(fake.bodyCalls()).toBe(0);
    expect(result.responseScanSkips).toEqual([
      expect.objectContaining({ reason }),
    ]);
    expect(result.responseScanViolations).toEqual([]);
  }
});

test("fails closed when response stream setup is missing or rejected", async () => {
  const missing = fakeResponse({});
  delete missing.response.stream;
  const rejected = fakeResponse({
    stream: () => {
      throw new Error("synthetic stream setup rejected");
    },
  });

  const missingResult = await scanResponseForTest(missing.response);
  const rejectedResult = await scanResponseForTest(rejected.response);

  expect(missing.bodyCalls()).toBe(0);
  expect(rejected.bodyCalls()).toBe(0);
  expect(missingResult.responseScanViolations).toEqual([
    expect.objectContaining({ reason: "streaming-unavailable" }),
  ]);
  expect(rejectedResult.responseScanViolations).toEqual([
    expect.objectContaining({ reason: "streaming-unavailable" }),
  ]);
  expect(rejectedResult.responseScanDiagnostics).toEqual([
    expect.objectContaining({ streamEstablished: false }),
  ]);
});

test("skips responses whose method or status forbids a body", async () => {
  for (const options of [{ method: "HEAD" }, { status: 204 }, { status: 304 }]) {
    const fake = fakeResponse({
      ...options,
      headers: { "content-type": "text/plain" },
      body: () => {
        throw new Error("body must not be retrieved");
      },
    });
    const result = await scanResponseForTest(fake.response);
    expect(fake.bodyCalls()).toBe(0);
    expect(result.responseScanSkips).toEqual([
      expect.objectContaining({ reason: "response-has-no-body" }),
    ]);
  }
});

test("bounds retained prefix for large, chunked, and lying streams", async () => {
  const overLimit = fakeResponse({
    headers: {
      "content-type": "text/plain",
      "content-length": String(RESPONSE_SCAN_BYTES),
    },
    stream: () => chunkStream([
      Buffer.alloc(RESPONSE_SCAN_BYTES - 4, "a"),
      Buffer.from("later"),
    ]),
  });
  const short = fakeResponse({
    headers: {
      "content-type": "text/plain",
      "content-length": "4",
    },
    stream: () => prefixedLargeChunkStream(
      Buffer.from("abc"),
      32,
      RESPONSE_SCAN_BYTES,
    ),
  });
  const chunked = fakeResponse({
    headers: { "content-type": "text/plain" },
    stream: () => chunkStream(largeChunkSequence(4, RESPONSE_SCAN_BYTES)),
  });

  const overLimitResult = await scanResponseForTest(overLimit.response);
  const shortResult = await scanResponseForTest(short.response);
  const chunkedResult = await scanResponseForTest(chunked.response);

  expect(overLimit.bodyCalls()).toBe(0);
  expect(overLimit.streamCalls()).toBe(1);
  expect(overLimitResult.responseScanViolations).toEqual([
    expect.objectContaining({
      actualLength: RESPONSE_SCAN_BYTES + 1,
      declaredLength: RESPONSE_SCAN_BYTES,
      exceedsDeclared: true,
      exceedsPolicy: true,
      reason: "actual-body-size-mismatch",
    }),
  ]);
  expect(overLimitResult.responseScanDiagnostics).toEqual([
    expect.objectContaining({
      capturedBytes: RESPONSE_SCAN_BYTES,
      maxRetainedBytes: RESPONSE_SCAN_BYTES,
      observedLength: RESPONSE_SCAN_BYTES + 1,
      streamEstablished: true,
    }),
  ]);
  expect(short.bodyCalls()).toBe(0);
  expect(short.streamCalls()).toBe(1);
  expect(shortResult.responseScanViolations).toEqual([
    expect.objectContaining({
      actualLength: 3 + 32 * RESPONSE_SCAN_BYTES,
      declaredLength: 4,
      exceedsDeclared: true,
      exceedsPolicy: true,
      reason: "actual-body-size-mismatch",
    }),
  ]);
  expect(shortResult.responseScanDiagnostics).toEqual([
    expect.objectContaining({
      capturedBytes: RESPONSE_SCAN_BYTES,
      maxRetainedBytes: RESPONSE_SCAN_BYTES,
      observedLength: 3 + 32 * RESPONSE_SCAN_BYTES,
      streamEstablished: true,
    }),
  ]);
  expect(chunked.bodyCalls()).toBe(0);
  expect(chunked.streamCalls()).toBe(0);
  expect(chunkedResult.responseScanSkips).toEqual([
    expect.objectContaining({ reason: "content-length-missing" }),
  ]);
  expect(chunkedResult.responseScanDiagnostics).toEqual([]);
});

test("redacts synthetic failure details through the network guard", async ({ page }) => {
  const forbiddenBody = JSON.stringify({
    error: {
      message: "synthetic bootstrap failure",
      prompt: "prompt text",
      body: "body text",
    },
  });
  const consoleMessage = `browser harness secret ${harness.token} from ${tmpdir()}/diagnostic.py`;
  requestPolicy.expectHttpError({
    method: "GET",
    path: "/api/bootstrap",
    status: 500,
  });
  requestPolicy.expectConsoleError({ message: consoleMessage, count: 1 });
  await page.route("**/api/bootstrap", async (route) => {
    await route.fulfill({
      status: 500,
      contentType: "application/json",
      body: forbiddenBody,
    });
  });

  await page.goto(`${harness.origin}/#token=${harness.token}`);
  await page.evaluate((message) => console.error(message), consoleMessage);

  const consoleErrors = requestPolicy.consoleErrors();
  expect(consoleErrors).toContain(
    "browser harness secret [REDACTED] from [PATH_REDACTED]",
  );
  for (const forbidden of [
    harness.token,
    `${tmpdir()}/diagnostic.py`,
    "prompt text",
    "body text",
  ]) {
    expect(consoleErrors.join("\n")).not.toContain(forbidden);
  }
});

test("rejects duplicate structured console errors beyond the declared count", async ({
  page,
}) => {
  const message = "synthetic duplicate console error";
  requestPolicy.expectConsoleError({ message, count: 1 });
  await page.goto(`${harness.origin}/#token=${harness.token}`);
  await page.evaluate((value) => {
    console.error(value);
    console.error(value);
  }, message);
  await expect(requestPolicy.assert()).rejects.toThrow(/unexpected console errors/u);
  requestPolicy.expectConsoleError({ message, count: 1 });
});

test("rejects a declared failed request that has not occurred", async ({ page }) => {
  const externalUrl = "https://example.invalid/missing";
  requestPolicy.expectBlockedRequest(externalUrl);
  requestPolicy.expectBlockedConsoleError({
    method: "GET",
    url: externalUrl,
    count: 1,
  });
  requestPolicy.expectFailedRequest({
    method: "GET",
    path: "/missing",
    count: 1,
  });
  await expect(requestPolicy.assert()).rejects.toThrow(/failed requests/u);
  const failedRequest = page.waitForEvent("requestfailed");
  await page.evaluate(async () => {
    try {
      await fetch("https://example.invalid/missing");
    } catch {
      // Expected for this contract test.
    }
  });
  await failedRequest;
});

test("removes the temporary workspace after a failed operation", async () => {
  const workspace = harness.workspaceRoot;
  try {
    throw new Error("synthetic fixture failure");
  } catch (error) {
    await harness.close();
    harness = undefined;
    expect(error.message).toBe("synthetic fixture failure");
  }
  expect(await pathExists(workspace)).toBe(false);
});

async function pathExists(path) {
  try {
    await access(path);
    return true;
  } catch (error) {
    if (error.code === "ENOENT") return false;
    throw error;
  }
}

async function runHarnessFailureProbe(configPath) {
  return runPlaywrightProbe(configPath, {
    HARNESS_FAILURE_PROBE: "1",
    HARNESS_FAILURE_PROBE_TOKEN,
  });
}

async function runPlaywrightProbe(configPath, environment) {
  const child = spawn(
    process.execPath,
    [
      PLAYWRIGHT_CLI,
      "test",
      "--config",
      configPath,
      "tests/harness_failure_probe.spec.mjs",
    ],
    {
      cwd: WEBUI_ROOT,
      env: {
        ...process.env,
        ...environment,
      },
      stdio: ["ignore", "pipe", "pipe"],
    },
  );
  let stdout = "";
  let stderr = "";
  child.stdout.on("data", (chunk) => {
    stdout += chunk.toString();
  });
  child.stderr.on("data", (chunk) => {
    stderr += chunk.toString();
  });
  const result = await new Promise((resolvePromise, reject) => {
    child.once("error", reject);
    child.once("close", (exitCode, signal) => {
      resolvePromise({ exitCode, signal, stdout, stderr });
    });
  });
  return {
    ...result,
    logText: redactSensitiveText(
      `${stdout}${stderr}`,
      [HARNESS_FAILURE_PROBE_TOKEN],
      { truncate: false },
    ),
  };
}

async function collectFiles(root) {
  const files = [];
  await visitFiles(root, root, files);
  return files.sort();
}

async function readTextEntriesFromZip(zipPath) {
  const result = spawnSync("python3", [
    "-c",
    `
import sys
import zipfile

text_suffixes = (".trace", ".json", ".txt", ".html", ".js", ".css", ".svg", ".md", ".yaml", ".yml", ".ts", ".mjs")
with zipfile.ZipFile(sys.argv[1]) as archive:
    for name in archive.namelist():
        if name.endswith(text_suffixes):
            data = archive.read(name)
            sys.stdout.buffer.write(data)
            sys.stdout.buffer.write(b"\\n")
`,
    zipPath,
  ], { encoding: "utf8" });
  if (result.status !== 0) {
    throw new Error(`failed to read trace zip: ${result.stderr || result.error?.message}`);
  }
  return result.stdout;
}

async function readRetainedTextArtifacts(outputDir, traceZip) {
  const text = [];
  for (const relativePath of await collectFiles(outputDir)) {
    const path = join(outputDir, relativePath);
    if (path.endsWith(".png")) continue;
    if (basename(relativePath) === "trace.zip") {
      text.push(await readTextEntriesFromZip(path));
      continue;
    }
    text.push(await readFile(path, "utf8"));
  }
  if (!text.length) throw new Error(`no retained text artifacts found for ${traceZip}`);
  return text.join("\n");
}

function compareMaskedScreenshots(rawScreenshot, sanitizedScreenshot, boxes) {
  const result = spawnSync("python3", [
    "-c",
    `
import json
import struct
import sys
import zlib

def decode(path):
    data = open(path, "rb").read()
    assert data[:8] == b"\\x89PNG\\r\\n\\x1a\\n"
    offset = 8
    idat = b""
    width = height = channels = None
    while offset < len(data):
        length = struct.unpack(">I", data[offset:offset + 4])[0]
        kind = data[offset + 4:offset + 8]
        chunk = data[offset + 8:offset + 8 + length]
        offset += 12 + length
        if kind == b"IHDR":
            width, height, depth, color_type, _, _, interlace = struct.unpack(">IIBBBBB", chunk)
            assert depth == 8 and interlace == 0 and color_type in (2, 6)
            channels = 3 if color_type == 2 else 4
        elif kind == b"IDAT":
            idat += chunk
        elif kind == b"IEND":
            break
    raw = zlib.decompress(idat)
    row_size = width * channels
    rows = []
    previous = bytearray(row_size)
    offset = 0
    for _ in range(height):
        filter_type = raw[offset]
        current = bytearray(raw[offset + 1:offset + 1 + row_size])
        offset += row_size + 1
        for i in range(row_size):
            left = current[i - channels] if i >= channels else 0
            up = previous[i]
            upper_left = previous[i - channels] if i >= channels else 0
            if filter_type == 1:
                current[i] = (current[i] + left) & 255
            elif filter_type == 2:
                current[i] = (current[i] + up) & 255
            elif filter_type == 3:
                current[i] = (current[i] + ((left + up) // 2)) & 255
            elif filter_type == 4:
                p = left + up - upper_left
                pa = abs(p - left)
                pb = abs(p - up)
                pc = abs(p - upper_left)
                predictor = left if pa <= pb and pa <= pc else (up if pb <= pc else upper_left)
                current[i] = (current[i] + predictor) & 255
            else:
                assert filter_type == 0
        rows.append(current)
        previous = current
    return width, height, channels, rows

raw = decode(sys.argv[1])
safe = decode(sys.argv[2])
assert raw[:2] == safe[:2], f"raw={raw[:2]} safe={safe[:2]}"
width, height, raw_channels, raw_rows = raw
_, _, safe_channels, safe_rows = safe
different = 0
black = 0
for y in range(height):
    for x in range(width):
        raw_pixel = raw_rows[y][x * raw_channels:x * raw_channels + 3]
        safe_pixel = safe_rows[y][x * safe_channels:x * safe_channels + 3]
        different += raw_pixel != safe_pixel
        black += safe_pixel == b"\\x00\\x00\\x00"
boxes = []
for box in json.loads(sys.argv[3]):
    x0 = max(0, int(box["x"]))
    y0 = max(0, int(box["y"]))
    x1 = min(width, int(box["x"] + box["width"]))
    y1 = min(height, int(box["y"] + box["height"]))
    total = max(1, (x1 - x0) * (y1 - y0))
    changed = box_black = 0
    for y in range(y0, y1):
        for x in range(x0, x1):
            raw_start = x * raw_channels
            safe_start = x * safe_channels
            raw_pixel = raw_rows[y][raw_start:raw_start + 3]
            safe_pixel = safe_rows[y][safe_start:safe_start + 3]
            changed += raw_pixel != safe_pixel
            box_black += safe_pixel == b"\\x00\\x00\\x00"
    boxes.append({
        "differentFraction": changed / total,
        "blackFraction": box_black / total,
    })
print(json.dumps({
    "differentPixels": different,
    "dimensions": [width, height],
    "sameDimensions": raw[:2] == safe[:2],
    "blackFraction": black / (width * height),
    "boxes": boxes,
}))
`,
    rawScreenshot,
    sanitizedScreenshot,
    JSON.stringify(boxes),
  ], { encoding: "utf8" });
  if (result.status !== 0) {
    throw new Error(`failed to compare failure screenshots: ${result.stderr}`);
  }
  return JSON.parse(result.stdout);
}

async function visitFiles(root, current, files) {
  let entries;
  try {
    entries = await readdir(current, { withFileTypes: true });
  } catch (error) {
    if (error.code === "ENOENT") return;
    throw error;
  }
  for (const entry of entries) {
    const entryPath = join(current, entry.name);
    if (entry.isDirectory()) {
      await visitFiles(root, entryPath, files);
      continue;
    }
    files.push(relative(root, entryPath));
  }
}

test("captures actual Playwright failure artifacts from the opt-in probe", async () => {
  const diagnosticsRoot = await mkdtemp(join(tmpdir(), "browser-harness-probe-"));
  const outputDir = join(diagnosticsRoot, "playwright-output");
  const configPath = join(diagnosticsRoot, "playwright.config.mjs");
  const logPath = join(diagnosticsRoot, "probe.log");
  await writeFile(configPath, `
import { LOCKED_CHROMIUM } from ${JSON.stringify(
    new URL("../playwright.config.mjs", import.meta.url).href,
  )};

export default {
  testDir: ${JSON.stringify(join(WEBUI_ROOT, "tests"))},
  outputDir: ${JSON.stringify(outputDir)},
  preserveOutput: "failures-only",
  reporter: [
    [${JSON.stringify(FAILURE_ARTIFACT_REPORTER)}],
    [${JSON.stringify(PRIVACY_SAFE_REPORTER)}],
  ],
  workers: 1,
  projects: [{
    name: LOCKED_CHROMIUM.browserName,
    use: { browserName: LOCKED_CHROMIUM.browserName },
  }],
  use: {
    screenshot: "off",
    trace: "retain-on-failure",
    video: "off",
  },
};
`, "utf8");
  try {
    const result = await runHarnessFailureProbe(configPath);
    await writeFile(logPath, result.logText, "utf8");

    const artifactNames = await collectFiles(outputDir);

    expect(result.exitCode).not.toBe(0);
    expect(result.logText).toContain("Test failed; inspect sanitized artifacts.");
    expect(result.logText).toContain("1 failed");
    expect(await pathExists(outputDir)).toBe(true);
    expect(await pathExists(logPath)).toBe(true);

    const artifacts = artifactNames;
    expect(artifacts.filter((file) => file.endsWith("trace.zip"))).toHaveLength(1);
    expect(artifacts.filter((file) => file.endsWith(".png"))).toHaveLength(0);
    expect(artifacts.some((file) => basename(file) === "stdout")).toBe(true);
    expect(artifacts.some((file) => basename(file) === "synthetic.txt")).toBe(true);
    expect(artifacts.some((file) => file.endsWith("error-context.md"))).toBe(true);

    const traceZip = artifacts.find((file) => file.endsWith("trace.zip"));
    expect(traceZip).toBeDefined();

    const traceText = await readTextEntriesFromZip(join(outputDir, traceZip));

    expect(traceText).toContain("[REDACTED]");
    expect(traceText).toMatch(/"type":"before"/u);
    expect(traceText).toMatch(/"type":"after"/u);
    let retainedText = await readRetainedTextArtifacts(outputDir, traceZip);
    retainedText += await readFile(logPath, "utf8");
    expect(retainedText).not.toContain("SYNTHETIC");
    for (const forbidden of HARNESS_FAILURE_PROBE_SENTINELS) {
      expect(traceText).not.toContain(forbidden);
      expect(retainedText).not.toContain(forbidden);
      expect(result.logText).not.toContain(forbidden);
    }
  } finally {
    await rm(diagnosticsRoot, { recursive: true, force: true });
  }

  expect(await pathExists(diagnosticsRoot)).toBe(false);
});

test("terminates the runner before an output ownership probe body can write", async () => {
  const diagnosticsRoot = await mkdtemp(join(tmpdir(), "output-ownership-probe-"));
  const outsideRoot = await mkdtemp(join(tmpdir(), "output-ownership-outside-"));
  const outputLink = join(diagnosticsRoot, "linked-output");
  const preservedPath = join(outsideRoot, "preserved.txt");
  const configPath = join(diagnosticsRoot, "playwright.config.mjs");
  await writeFile(preservedPath, "PRESERVED_SYMLINK_TARGET_DATA", "utf8");
  await symlink(outsideRoot, outputLink);
  await writeFile(configPath, `
export default {
  testDir: ${JSON.stringify(join(WEBUI_ROOT, "tests"))},
  outputDir: ${JSON.stringify(join(outputLink, "playwright-output"))},
  reporter: [
    [${JSON.stringify(FAILURE_ARTIFACT_REPORTER)}],
    [${JSON.stringify(PRIVACY_SAFE_REPORTER)}],
  ],
  workers: 1,
};
`, "utf8");
  try {
    const result = await runPlaywrightProbe(configPath, {
      HARNESS_OUTPUT_OWNERSHIP_FAILURE_PROBE: "1",
    });

    expect(result.signal).toBeNull();
    expect(result.exitCode).toBe(1);
    expect(result.logText).toContain(OWNERSHIP_FAILURE_MESSAGE);
    expect(result.logText).not.toContain("RAW_OUTPUT_OWNERSHIP_PROBE_SENTINEL");
    expect(await collectFiles(outsideRoot)).toEqual(["preserved.txt"]);
    expect(await readFile(preservedPath, "utf8")).toBe(
      "PRESERVED_SYMLINK_TARGET_DATA",
    );
  } finally {
    await rm(diagnosticsRoot, { recursive: true, force: true });
    await rm(outsideRoot, { recursive: true, force: true });
  }
});

test("returns a nonzero runner status when reporter cleanup fails after a pass", async () => {
  const diagnosticsRoot = await mkdtemp(join(tmpdir(), "browser-cleanup-probe-"));
  const outputDir = join(diagnosticsRoot, "playwright-output");
  const reporterPath = join(diagnosticsRoot, "cleanup-failure-reporter.mjs");
  const configPath = join(diagnosticsRoot, "playwright.config.mjs");
  await writeFile(reporterPath, `
import { closeSync } from "node:fs";
import FailureArtifactsReporter from ${JSON.stringify(
    new URL("./failure_artifacts_reporter.mjs", import.meta.url).href,
  )};

export default class CleanupFailureReporter extends FailureArtifactsReporter {
  onEnd(result) {
    const root = this.outputRoots?.[0];
    if (!Number.isInteger(root?.descriptor)) {
      throw new Error("cleanup probe did not acquire output ownership");
    }
    closeSync(root.descriptor);
    root.descriptor = -1;
    root.tainted = true;
    return super.onEnd(result);
  }
}
`, "utf8");
  await writeFile(configPath, `
import { LOCKED_CHROMIUM } from ${JSON.stringify(
    new URL("../playwright.config.mjs", import.meta.url).href,
  )};

export default {
  testDir: ${JSON.stringify(join(WEBUI_ROOT, "tests"))},
  outputDir: ${JSON.stringify(outputDir)},
  preserveOutput: "failures-only",
  reporter: [
    [${JSON.stringify(reporterPath)}],
    [${JSON.stringify(PRIVACY_SAFE_REPORTER)}],
  ],
  workers: 1,
  projects: [{
    name: LOCKED_CHROMIUM.browserName,
    use: { browserName: LOCKED_CHROMIUM.browserName },
  }],
};
`, "utf8");
  try {
    const result = await runPlaywrightProbe(configPath, {
      HARNESS_CLEANUP_FAILURE_PROBE: "1",
    });

    expect(result.signal).toBeNull();
    expect(result.exitCode).not.toBe(0);
    expect(result.logText).toContain("test passed");
    expect(result.logText).toContain("1 passed");
    expect(result.logText).toContain(
      "Failure artifact cleanup failed; residual artifacts may remain.",
    );
    expect(result.logText).not.toContain("cleanup probe did not acquire");
  } finally {
    await rm(diagnosticsRoot, { recursive: true, force: true });
  }
});

async function bootstrapSnapshot(page, entry, viaReload = false) {
  const before = requestPolicy.requestRecords().length;
  if (viaReload) {
    await page.reload();
    await entry.expectLoaded();
  } else {
    await entry.open(harness.origin, harness.token);
  }
  return requestSnapshot(requestPolicy.requestRecords().slice(before));
}

function requestSnapshot(records) {
  return records.map(({ method, resourceType, url }) =>
    `${method} ${resourceType} ${new URL(url).pathname}`
  ).sort();
}

function assertSafeResponseScanState(policy) {
  expect(policy.responseScanViolations()).toEqual([]);
  expect(policy.responseScanDiagnostics().every((diagnostic) =>
    Number.isInteger(diagnostic.capturedBytes) &&
    diagnostic.capturedBytes >= 0 &&
    diagnostic.capturedBytes <= RESPONSE_SCAN_BYTES &&
    diagnostic.maxRetainedBytes === RESPONSE_SCAN_BYTES &&
    diagnostic.observedLength >= diagnostic.capturedBytes &&
    typeof diagnostic.method === "string" &&
    typeof diagnostic.path === "string" &&
    Number.isInteger(diagnostic.status)
  )).toBe(true);
  expect(policy.responseScanSkips().every((skip) =>
    typeof skip.reason === "string" &&
    typeof skip.path === "string" &&
    Number.isInteger(skip.status)
  )).toBe(true);
}

function fakeResponse({
  body = Buffer.alloc(0),
  headers = { "content-type": "text/plain", "content-length": "0" },
  method = "GET",
  status = 200,
  url = "http://127.0.0.1:4173/synthetic-response",
  stream = async function* () {},
}) {
  let bodyCalls = 0;
  let streamCalls = 0;
  const bodyProvider = typeof body === "function" ? body : () => body;
  const streamProvider = typeof stream === "function" ? stream : () => stream;
  return {
    bodyCalls: () => bodyCalls,
    streamCalls: () => streamCalls,
    response: {
      body: async () => {
        bodyCalls += 1;
        return bodyProvider();
      },
      stream: async () => {
        streamCalls += 1;
        return streamProvider();
      },
      headers: () => ({ ...headers }),
      request: () => ({
        method: () => method,
        resourceType: () => "document",
      }),
      status: () => status,
      url: () => url,
    },
  };
}

function chunkStream(chunks) {
  return (async function* () {
    for (const chunk of chunks) yield chunk;
  })();
}

function* largeChunkSequence(count, chunkSize) {
  for (let index = 0; index < count; index += 1) {
    yield Buffer.alloc(chunkSize, "x");
  }
}

function prefixedLargeChunkStream(prefix, count, chunkSize) {
  return (async function* () {
    yield prefix;
    yield* largeChunkSequence(count, chunkSize);
  })();
}
