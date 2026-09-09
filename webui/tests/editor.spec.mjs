import { spawn } from "node:child_process";
import { delimiter, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { expect, test } from "@playwright/test";

const projectRoot = resolve(fileURLToPath(new URL("../..", import.meta.url)));
const installedServer = Boolean(process.env.SIMULATOR_SERVER_SCRIPT);
const fixtureScript = installedServer
  ? resolve(projectRoot, process.env.SIMULATOR_SERVER_SCRIPT)
  : join(projectRoot, "webui", "tests", "fixture_server.py");
let harness;
let requestPolicy;

async function startFixtureServer() {
  const child = spawn(
    process.env.SIMULATOR_PYTHON || process.env.PYTHON || "python3",
    [fixtureScript],
    {
    cwd: projectRoot,
    env: {
      ...process.env,
      PYTHONPATH: installedServer
        ? ""
        : [join(projectRoot, "src"), process.env.PYTHONPATH]
            .filter(Boolean)
            .join(delimiter),
    },
    stdio: ["pipe", "pipe", "pipe"],
    },
  );
  try {
    const details = await readReadyLine(child);
    if (
      !details ||
      typeof details.origin !== "string" ||
      typeof details.token !== "string"
    ) {
      throw new Error("fixture server emitted incomplete startup data");
    }
    let closePromise;
    return {
      origin: details.origin,
      token: details.token,
      close() {
        closePromise ??= stopChild(child);
        return closePromise;
      },
    };
  } catch (error) {
    await stopChild(child);
    throw error;
  }
}

function readReadyLine(child) {
  return new Promise((resolvePromise, reject) => {
    let output = "";
    let errorOutput = "";
    let settled = false;
    let timeout;
    const cleanup = () => {
      clearTimeout(timeout);
      child.stdout.off("data", onStdout);
      child.stdout.off("end", onStdoutEnd);
      child.stderr.off("data", onStderr);
      child.off("error", onError);
      child.off("exit", onExit);
    };
    const fail = (error) => {
      if (settled) return;
      settled = true;
      cleanup();
      reject(error);
    };
    const onStdout = (chunk) => {
      output += chunk.toString();
      const newline = output.indexOf("\n");
      if (newline < 0 || settled) return;
      settled = true;
      cleanup();
      try {
        resolvePromise(JSON.parse(output.slice(0, newline)));
      } catch (error) {
        reject(new Error(`fixture server emitted invalid startup data: ${error}`));
      }
    };
    const onStdoutEnd = () => {
      fail(
        new Error(
          `fixture server closed stdout before startup: ${errorOutput}`,
        ),
      );
    };
    const onStderr = (chunk) => {
      errorOutput += chunk.toString();
    };
    const onError = (error) => fail(error);
    const onExit = (code, signal) => {
      fail(
        new Error(
          `fixture server exited before startup (${code ?? `signal ${signal}`}): ${errorOutput}`,
        ),
      );
    };
    timeout = setTimeout(
      () =>
        fail(new Error(`fixture server did not start: ${errorOutput}`)),
      10000,
    );
    child.stdout.on("data", onStdout);
    child.stdout.once("end", onStdoutEnd);
    child.stderr.on("data", onStderr);
    child.once("error", onError);
    child.once("exit", onExit);
  });
}

async function stopChild(child) {
  const exited = waitForChildClose(child);
  if (child.exitCode === null && child.signalCode === null) {
    if (!child.stdin.destroyed) child.stdin.end();
    if (await waitForChildCloseWithin(exited, 5000)) return;
    child.kill("SIGTERM");
    if (!(await waitForChildCloseWithin(exited, 1000))) {
      child.kill("SIGKILL");
    }
  }
  await exited;
}

function waitForChildClose(child) {
  if (child.exitCode !== null || child.signalCode !== null) {
    return Promise.resolve();
  }
  return new Promise((resolvePromise) => {
    child.once("close", resolvePromise);
  });
}

async function waitForChildCloseWithin(exited, milliseconds) {
  let timeout;
  const deadline = new Promise((resolvePromise) => {
    timeout = setTimeout(() => resolvePromise(false), milliseconds);
  });
  try {
    return await Promise.race([exited.then(() => true), deadline]);
  } finally {
    clearTimeout(timeout);
  }
}

function installOfflineRequestPolicy(page) {
  const expectedOrigin = harness.origin;
  let patchApplication = false;
  const blockedRequests = [];
  const relevantRequests = new Map();
  const relevantResponses = new Map();
  const failedRequests = [];
  const unsuccessfulResponses = [];

  const isRelevantRequest = (request) => {
    if (
      ["document", "script", "stylesheet", "font", "worker"].includes(
        request.resourceType(),
      )
    ) {
      return true;
    }
    try {
      const url = new URL(request.url());
      return (
        url.origin === expectedOrigin &&
        (url.pathname === "/manifest.json" ||
          /\.(?:js|css|ttf)$/.test(url.pathname))
      );
    } catch {
      return false;
    }
  };

  page.on("request", (request) => {
    if (isRelevantRequest(request)) {
      relevantRequests.set(request, {
        resourceType: request.resourceType(),
        url: request.url(),
      });
    }
  });

  page.on("response", (response) => {
    const request = response.request();
    if (!isRelevantRequest(request)) return;
    relevantResponses.set(request, response);
    if (response.status() < 200 || response.status() >= 400) {
      unsuccessfulResponses.push({
        status: response.status(),
        resourceType: request.resourceType(),
        url: response.url(),
      });
    }
  });

  page.on("requestfailed", (request) => {
    if (isRelevantRequest(request)) {
      failedRequests.push({
        error: request.failure()?.errorText || "unknown request failure",
        resourceType: request.resourceType(),
        url: request.url(),
      });
    }
  });

  page.route("**/*", async (route) => {
    let url;
    try {
      url = new URL(route.request().url());
    } catch {
      blockedRequests.push(route.request().url());
      await route.abort("blockedbyclient");
      return;
    }
    const isLoopback =
      url.hostname === "127.0.0.1" ||
      url.hostname === "localhost" ||
      url.hostname === "::1";
    if (!isLoopback || url.origin !== expectedOrigin) {
      blockedRequests.push(url.href);
      await route.abort("blockedbyclient");
      return;
    }

    if (patchApplication && /\/app(?:-[^/]+)?\.js$/.test(url.pathname)) {
      const response = await route.fetch();
      const body = await response.text();
      const editorOptionsMarker = 'ariaLabel:"Python source editor"';
      const markerIndex = body.indexOf(editorOptionsMarker);
      const createToken = ".create(";
      const createIndex = body.lastIndexOf(createToken, markerIndex);
      if (
        markerIndex < 0 ||
        createIndex < 0 ||
        markerIndex - createIndex > 2000
      ) {
        throw new Error("could not locate the generated Monaco initialization");
      }
      const patchedBody =
        body.slice(0, createIndex) +
        '.create((()=>{throw new Error("forced Monaco initialization failure")})(),' +
        body.slice(createIndex + createToken.length);
      await route.fulfill({ response, body: patchedBody });
      return;
    }
    await route.continue();
  });

  function manifestAssetName(url) {
    const parsed = new URL(url);
    if (parsed.origin !== expectedOrigin) return undefined;
    if (parsed.pathname === "/") return "index.html";
    if (!parsed.pathname.startsWith("/")) return undefined;
    return parsed.pathname.slice(1);
  }

  return {
    forceMonacoInitializationFailure() {
      patchApplication = true;
    },
    async assertManifestResources(manifest, requiredNames, lazyNames) {
      const manifestNames = new Set(Object.keys(manifest));
      const required = new Set(requiredNames);
      const lazy = new Set(lazyNames);
      expect(
        new Set([...required, ...lazy]),
        "every manifest asset must be classified as required or intentionally lazy/unrequested",
      ).toEqual(manifestNames);

      const successfulNames = new Set();
      for (const [request, response] of relevantResponses) {
        const name = manifestAssetName(response.url());
        if (name && response.status() >= 200 && response.status() < 400) {
          successfulNames.add(name);
        }
        expect(
          new URL(response.url()).origin,
          `relevant response must be same-origin: ${response.url()}`,
        ).toBe(expectedOrigin);
      }
      for (const name of required) {
        expect(
          successfulNames,
          `required browser asset was not loaded successfully: ${name}`,
        ).toContain(name);
      }
    },
    assert() {
      expect(blockedRequests).toEqual([]);
      expect(failedRequests).toEqual([]);
      expect(unsuccessfulResponses).toEqual([]);
      const pendingRequests = [...relevantRequests.entries()]
        .filter(([request]) => !relevantResponses.has(request))
        .map(([, details]) => details);
      expect(pendingRequests).toEqual([]);
      for (const details of relevantRequests.values()) {
        expect(
          new URL(details.url).origin,
          `relevant request must be same-origin: ${details.url}`,
        ).toBe(expectedOrigin);
      }
    },
  };
}

test.beforeEach(async ({ page }) => {
  try {
    harness = await startFixtureServer();
    requestPolicy = installOfflineRequestPolicy(page);
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

test("loads Monaco under an explicit offline same-origin policy", async ({ page }) => {
  const requests = [];
  page.on("request", (request) => requests.push(request.url()));
  const shellResponse = await page.goto(`${harness.origin}/#token=${harness.token}`);
  expect(shellResponse.headers()["content-security-policy"]).toContain(
    "worker-src 'self'",
  );
  expect(shellResponse.headers()["x-content-type-options"]).toBe("nosniff");
  expect(shellResponse.headers()["cross-origin-resource-policy"]).toBe("same-origin");
  expect(shellResponse.headers()["referrer-policy"]).toBe("no-referrer");
  expect(shellResponse.headers()["permissions-policy"]).toContain("camera=()");
  await expect(page.locator(".status")).toHaveText(/Python editor ready/);
  await expect(page.locator(".editor")).toBeVisible();
  await expect(page.locator(".fallback")).toBeHidden();
  const configuredWorkerUrls = await page.evaluate(() => {
    const environment = globalThis.MonacoEnvironment;
    const urls = ["editor", "python"].map((label) =>
      environment.getWorkerUrl("", label),
    );
    globalThis.__testWorkers = urls.map(
      (url) => new Worker(url, { type: "module" }),
    );
    return urls;
  });
  await expect.poll(() => page.workers().length).toBeGreaterThan(0);

  const manifest = await page.evaluate(async () =>
    fetch("/manifest.json").then((response) => response.json()),
  );
  expect(configuredWorkerUrls).toHaveLength(2);
  for (const workerUrl of configuredWorkerUrls) {
    const worker = new URL(workerUrl);
    expect(worker.origin).toBe(harness.origin);
    expect(manifest[worker.pathname.slice(1)]).toBeDefined();
  }
  const requiredManifestAssets = [
    "index.html",
    "manifest.json",
    ...Object.keys(manifest).filter((name) =>
      /^(?:app|styles)-[A-Za-z0-9_-]+\.(?:js|css)$/.test(name),
    ),
    ...configuredWorkerUrls.map((workerUrl) =>
      new URL(workerUrl).pathname.slice(1),
    ),
  ];
  const intentionallyLazyManifestAssets = Object.keys(manifest).filter(
    (name) =>
      /^(?:app|styles)\.(?:js|css)$/.test(name) ||
      name.endsWith(".ttf") ||
      ["ASSET_PROVENANCE.txt", "NOTICE.txt", "favicon.svg"].includes(name),
  );
  await requestPolicy.assertManifestResources(
    manifest,
    requiredManifestAssets,
    intentionallyLazyManifestAssets,
  );
  const fontName = Object.keys(manifest).find((name) => name.endsWith(".ttf"));
  expect(fontName).toBeDefined();
  expect(manifest[fontName].media_type).toBe("font/ttf");
  const fontResponse = await page.evaluate((name) =>
    fetch(`/${name}`).then((response) => ({
      contentType: response.headers.get("content-type"),
      nosniff: response.headers.get("x-content-type-options"),
    })),
    fontName,
  );
  expect(fontResponse).toEqual({
    contentType: "font/ttf",
    nosniff: "nosniff",
  });
  expect(requests.some((url) => url.includes("worker"))).toBe(true);
  requestPolicy.assert();
});

test("a captured capability outranks readable stale storage when storage write fails", async ({
  page,
}) => {
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
  await expect(page.locator(".status")).toHaveText(/Python editor ready/);
  expect(page.url()).toBe(`${harness.origin}/`);
});

test("a stored capability remains usable after reload", async ({ page }) => {
  await page.goto(`${harness.origin}/#token=${harness.token}`);
  await expect(page.locator(".status")).toHaveText(/Python editor ready/);
  await page.reload();
  await expect(page.locator(".status")).toHaveText(/Python editor ready/);
});

test("keeps an exact read-only fallback when Monaco initialization fails", async ({
  page,
}) => {
  requestPolicy.forceMonacoInitializationFailure();
  const mutationRequests = [];
  page.on("request", (request) => {
    const url = new URL(request.url());
    if (url.pathname.startsWith("/api/") && request.method() !== "GET") {
      mutationRequests.push(`${request.method()} ${url.pathname}`);
    }
  });
  const sourceResponsePromise = page.waitForResponse(
    (response) =>
      new URL(response.url()).pathname === "/api/source" &&
      response.request().method() === "GET",
  );
  await page.goto(`${harness.origin}/#token=${harness.token}`);
  const sourceResponse = await sourceResponsePromise;
  const sourceDocument = await sourceResponse.json();
  const candidateSource = sourceDocument.data.content;
  await expect(page.locator(".status")).toHaveText(/read-only fallback/);
  await expect(page.locator(".editor")).toBeHidden();
  await expect(page.locator(".fallback")).toBeVisible();
  await expect(page.locator(".fallback")).toHaveAttribute("readonly", "");
  await expect(page.locator(".fallback")).toHaveValue(candidateSource);

  const resolvedWorkerUrls = await page.evaluate(() =>
    ["editor", "python"].map((label) =>
      globalThis.MonacoEnvironment.getWorkerUrl("", label),
    ),
  );
  const manifest = await page.evaluate(() =>
    fetch("/manifest.json").then((response) => response.json()),
  );
  for (const workerUrl of resolvedWorkerUrls) {
    const worker = new URL(workerUrl);
    expect(worker.origin).toBe(harness.origin);
    expect(manifest[worker.pathname.slice(1)]).toBeDefined();
  }

  const enabledActionControls = await page
    .locator(
      'button, input:not([type="hidden"]), select, [role="button"], [data-action], [data-mutation]',
    )
    .evaluateAll((controls) =>
      controls.filter(
        (control) =>
          !control.hasAttribute("disabled") &&
          control.getAttribute("aria-disabled") !== "true",
      ),
    );
  expect(enabledActionControls).toHaveLength(0);
  expect(mutationRequests).toEqual([]);
  requestPolicy.assert();
});
