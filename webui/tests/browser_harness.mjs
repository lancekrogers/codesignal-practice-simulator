import { spawn } from "node:child_process";
import { delimiter, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { expect } from "@playwright/test";

const projectRoot = resolve(fileURLToPath(new URL("../..", import.meta.url)));

export async function startFixtureServer() {
  const installed = Boolean(process.env.SIMULATOR_SERVER_SCRIPT);
  const script = installed
    ? resolve(projectRoot, process.env.SIMULATOR_SERVER_SCRIPT)
    : join(projectRoot, "webui", "tests", "fixture_server.py");
  const child = spawn(
    process.env.SIMULATOR_PYTHON || process.env.PYTHON || "python3",
    [script],
    {
      cwd: projectRoot,
      env: fixtureEnvironment(installed),
      stdio: ["pipe", "pipe", "pipe"],
    },
  );
  try {
    const details = await readReadyLine(child);
    if (!details?.origin || !details?.token) {
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

function fixtureEnvironment(installed) {
  return {
    ...process.env,
    PYTHONPATH: installed
      ? ""
      : [join(projectRoot, "src"), process.env.PYTHONPATH]
          .filter(Boolean)
          .join(delimiter),
  };
}

function readReadyLine(child) {
  return new Promise((resolvePromise, reject) => {
    let output = "";
    let errors = "";
    let settled = false;
    const timeout = setTimeout(() => fail(new Error(
      `fixture server did not start: ${errors}`,
    )), 10000);
    const cleanup = () => {
      clearTimeout(timeout);
      child.stdout.off("data", onStdout);
      child.stdout.off("end", onEnd);
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
    const onEnd = () => fail(new Error(`fixture server closed stdout: ${errors}`));
    const onStderr = (chunk) => {
      errors += chunk.toString();
    };
    const onError = (error) => fail(error);
    const onExit = (code, signal) => fail(new Error(
      `fixture server exited before startup (${code ?? `signal ${signal}`}): ${errors}`,
    ));
    child.stdout.on("data", onStdout);
    child.stdout.once("end", onEnd);
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
    if (!(await waitForChildCloseWithin(exited, 1000))) child.kill("SIGKILL");
  }
  await exited;
}

function waitForChildClose(child) {
  if (child.exitCode !== null || child.signalCode !== null) {
    return Promise.resolve();
  }
  return new Promise((resolvePromise) => child.once("close", resolvePromise));
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

export function installOfflineRequestPolicy(page, harness) {
  const state = {
    expectedOrigin: harness.origin,
    patchApplication: false,
    blockedRequests: [],
    relevantRequests: new Map(),
    relevantResponses: new Map(),
    sameOriginRequests: [],
    failedRequests: [],
    unsuccessfulResponses: [],
    consoleErrors: [],
    pageErrors: [],
    expectedHttpErrors: new Set(),
    interceptions: new Map(),
    delays: new Map(),
  };
  page.on("request", (request) => trackRequest(request, state));
  page.on("response", (response) => trackResponse(response, state));
  page.on("requestfailed", (request) => trackFailure(request, state));
  page.on("console", (message) => {
    if (message.type() === "error") state.consoleErrors.push(message.text());
  });
  page.on("pageerror", (error) => state.pageErrors.push(error.message));
  page.route("**/*", (route) => routeRequest(route, state));
  return {
    forceMonacoInitializationFailure() {
      state.patchApplication = true;
    },
    intercept(path, response) {
      state.interceptions.set(path, response);
    },
    delay(path, milliseconds) {
      state.delays.set(path, milliseconds);
    },
    assertManifestResources(manifest, requiredNames, lazyNames) {
      assertManifestClassification(manifest, requiredNames, lazyNames);
      assertSuccessfulAssets(state, requiredNames);
    },
    assert() {
      assertPolicyState(state);
    },
  };
}

function trackRequest(request, state) {
  try {
    const url = new URL(request.url());
    if (url.origin === state.expectedOrigin) {
      state.sameOriginRequests.push({
        method: request.method(),
        path: url.pathname,
        resourceType: request.resourceType(),
      });
    }
  } catch {
    // The route handler records malformed URLs as blocked requests.
  }
  if (!isRelevantRequest(request, state.expectedOrigin)) return;
  state.relevantRequests.set(request, {
    resourceType: request.resourceType(),
    url: request.url(),
  });
}

function trackResponse(response, state) {
  const request = response.request();
  if (!isRelevantRequest(request, state.expectedOrigin)) return;
  state.relevantResponses.set(request, response);
  if (response.status() < 200 || response.status() >= 400) {
    state.unsuccessfulResponses.push({
      status: response.status(),
      resourceType: request.resourceType(),
      url: response.url(),
    });
  }
}

function trackFailure(request, state) {
  if (!isRelevantRequest(request, state.expectedOrigin)) return;
  state.failedRequests.push({
    error: request.failure()?.errorText || "unknown request failure",
    resourceType: request.resourceType(),
    url: request.url(),
  });
}

function isRelevantRequest(request, expectedOrigin) {
  if (["document", "script", "stylesheet", "font", "worker"].includes(
    request.resourceType(),
  )) return true;
  try {
    const url = new URL(request.url());
    return url.origin === expectedOrigin && (
      url.pathname === "/manifest.json" || /\.(?:js|css|ttf)$/.test(url.pathname)
    );
  } catch {
    return false;
  }
}

async function routeRequest(route, state) {
  let url;
  try {
    url = new URL(route.request().url());
  } catch {
    state.blockedRequests.push(route.request().url());
    await route.abort("blockedbyclient");
    return;
  }
  if (!isAllowedUrl(url, state.expectedOrigin)) {
    state.blockedRequests.push(url.href);
    await route.abort("blockedbyclient");
    return;
  }
  const interception =
    state.interceptions.get(url.pathname + url.search) ||
    state.interceptions.get(url.pathname);
  const delay = state.delays.get(url.pathname + url.search) ||
    state.delays.get(url.pathname);
  if (delay) await new Promise((resolvePromise) => setTimeout(resolvePromise, delay));
  if (interception) {
    if (interception.status >= 400) state.expectedHttpErrors.add(interception.status);
    await route.fulfill(interception);
    return;
  }
  if (state.patchApplication && /\/app(?:-[^/]+)?\.js$/.test(url.pathname)) {
    await routeWithEditorFailure(route);
    return;
  }
  await route.continue();
}

function isAllowedUrl(url, expectedOrigin) {
  const loopback = ["127.0.0.1", "localhost", "::1"].includes(url.hostname);
  return loopback && url.origin === expectedOrigin;
}

async function routeWithEditorFailure(route) {
  const response = await route.fetch();
  const body = await response.text();
  const marker = 'ariaLabel:"Python source editor"';
  const markerIndex = body.indexOf(marker);
  const createToken = ".create(";
  const createIndex = body.lastIndexOf(createToken, markerIndex);
  if (markerIndex < 0 || createIndex < 0 || markerIndex - createIndex > 2000) {
    throw new Error("could not locate the generated Monaco initialization");
  }
  const patchedBody = body.slice(0, createIndex) +
    '.create((()=>{throw new Error("forced Monaco initialization failure")})(),' +
    body.slice(createIndex + createToken.length);
  await route.fulfill({ response, body: patchedBody });
}

function assertManifestClassification(manifest, requiredNames, lazyNames) {
  const names = new Set(Object.keys(manifest));
  const classified = new Set([...requiredNames, ...lazyNames]);
  expect(classified).toEqual(names);
}

function assertSuccessfulAssets(state, requiredNames) {
  const successful = new Set();
  for (const [request, response] of state.relevantResponses) {
    const name = assetName(response.url(), state.expectedOrigin);
    if (name && response.status() >= 200 && response.status() < 400) {
      successful.add(name);
    }
    expect(new URL(response.url()).origin).toBe(state.expectedOrigin);
  }
  for (const name of requiredNames) {
    expect(successful, `asset was not loaded successfully: ${name}`).toContain(name);
  }
}

function assetName(value, expectedOrigin) {
  const url = new URL(value);
  if (url.origin !== expectedOrigin) return undefined;
  if (url.pathname === "/") return "index.html";
  return url.pathname.startsWith("/") ? url.pathname.slice(1) : undefined;
}

function assertPolicyState(state) {
  expect(state.blockedRequests).toEqual([]);
  expect(state.failedRequests).toEqual([]);
  expect(state.unsuccessfulResponses).toEqual([]);
  expect(state.consoleErrors.filter(
    (message) => !isExpectedHttpConsoleError(message, state.expectedHttpErrors),
  )).toEqual([]);
  expect(state.pageErrors).toEqual([]);
  for (const request of state.sameOriginRequests) {
    expect(
      isDocumentedRequest(request.path),
      `undocumented same-origin request: ${JSON.stringify(request)}`,
    ).toBe(true);
  }
  const pending = [...state.relevantRequests.entries()]
    .filter(([request]) => !state.relevantResponses.has(request))
    .map(([, details]) => details);
  expect(pending).toEqual([]);
  for (const details of state.relevantRequests.values()) {
    expect(new URL(details.url).origin).toBe(state.expectedOrigin);
  }
}

function isExpectedHttpConsoleError(message, expectedStatuses) {
  const match = message.match(/status of (\d{3})/u);
  return Boolean(match && expectedStatuses.has(Number(match[1])));
}

function isDocumentedRequest(path) {
  if (
    [
      "/",
      "/index.html",
      "/manifest.json",
      "/favicon.svg",
      "/ASSET_PROVENANCE.txt",
      "/NOTICE.txt",
    ]
      .includes(path)
  ) {
    return true;
  }
  if (path.startsWith("/api/")) {
    return (
      ["/api/bootstrap", "/api/attempts", "/api/source", "/api/time"].includes(path) ||
      /^\/api\/prompts\/[1-4]$/u.test(path)
    );
  }
  return /^\/[A-Za-z0-9._-]+\.(?:js|css|ttf)$/u.test(path);
}
