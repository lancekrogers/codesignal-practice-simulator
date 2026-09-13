import { expect, test } from "@playwright/test";
import { randomUUID } from "node:crypto";
import { tmpdir } from "node:os";
import {
  redactSensitiveText,
  sanitizeFailureScreenshot,
} from "./failure_artifacts.mjs";

export const RESPONSE_SCAN_BYTES = 64 * 1024;
const MAX_RESPONSE_SCANS = 100;
const INTERCEPTED_COVERAGE_HEADER =
  "x-browser-harness-intercepted-coverage";
const FORBIDDEN_SENTINELS = [
  "BROWSER_HARNESS_FORBIDDEN_RESPONSE_SENTINEL",
  "BROWSER_HARNESS_SECRET_RESPONSE_SENTINEL",
];

export async function installOfflineRequestPolicy(page, harness) {
  const state = createPolicyState(page, harness, test.info());
  await installPolicyListeners(page, state);
  return createPolicyControls(state, harness);
}

function createPolicyState(page, harness, testInfo) {
  return {
    page,
    testInfo,
    expectedOrigin: harness.origin,
    sensitiveValues: [harness.token],
    patchApplication: false,
    blockedRequests: [],
    blockedRequestRecords: [],
    blockedRequestRawUrls: new Map(),
    requestRecords: [],
    requestRecordEntries: [],
    retiredRequestRecords: new Set(),
    relevantRequests: new Map(),
    relevantRequestOrigins: new Map(),
    relevantResponses: new Map(),
    settledRequests: new Set(),
    retiredRequests: new Set(),
    sameOriginRequests: [],
    failedRequests: [],
    failedRequestRawUrls: new Map(),
    unsuccessfulResponses: [],
    webSocketRecords: [],
    blockedWebSocketRecords: [],
    blockedWebSocketRawUrls: new Map(),
    consoleErrorRecords: [],
    requestMethods: [],
    consoleErrors: [],
    pageErrors: [],
    expectedHttpErrors: [],
    expectedConsoleErrors: [],
    expectedBlockedConsoleErrors: [],
    expectedBlockedRequests: [],
    expectedBlockedWebSockets: [],
    expectedFailedRequests: [],
    expectedResponseScanViolations: [],
    interceptions: new Map(),
    holds: new Map(),
    scanPromises: new Set(),
    networkRequests: new Map(),
    activeResponseScans: new Map(),
    forbiddenMatches: [],
    expectedForbiddenMatches: new Set(),
    responseScanSkips: [],
    responseScanViolations: [],
    responseScanDiagnostics: [],
    interceptedResponseCoverage: new Map(),
    scanCount: 0,
    navigationEpoch: 0,
    retiredRequestIds: new Set(),
    cdpSession: undefined,
    streamingSetupError: undefined,
    failureScreenshotCaptured: false,
  };
}

async function installPolicyListeners(page, state) {
  await installNetworkStreaming(page, state);
  page.on("request", (request) => trackRequest(request, state));
  page.on("response", (response) => trackResponse(response, state));
  page.on("requestfailed", (request) => trackFailure(request, state));
  page.on("console", (message) => {
    if (message.type() === "error") {
      trackConsoleError(message, state);
    }
  });
  page.on("pageerror", () => state.pageErrors.push("page error [REDACTED]"));
  await page.route("**/*", (route) => routeRequest(route, state));
  await page.routeWebSocket("**/*", (webSocket) =>
    routeWebSocket(webSocket, state),
  );
}

function createPolicyControls(state, harness) {
  return {
    refreshOrigin() {
      const nextOrigin = harness.origin;
      state.expectedOrigin = nextOrigin;
      retireRequestsOutsideOrigin(state, nextOrigin, "origin-changed");
    },
    forceMonacoInitializationFailure() {
      state.patchApplication = true;
    },
    intercept(path, response) {
      state.interceptions.set(path, normalizeInterceptedResponse(response));
    },
    clearIntercept(path) {
      state.interceptions.delete(path);
    },
    expectHttpError(expectation) {
      state.expectedHttpErrors.push(normalizeHttpErrorExpectation(expectation));
    },
    expectConsoleError(message) {
      state.expectedConsoleErrors.push(normalizeConsoleErrorExpectation(message, state));
    },
    expectBlockedConsoleError(expectation) {
      state.expectedBlockedConsoleErrors.push(
        normalizeRequestExpectation(expectation),
      );
    },
    expectBlockedRequest(urlOrExpectation, count = 1) {
      const expectation = normalizeBlockedRequestExpectation(
        urlOrExpectation,
        count,
      );
      const existing = state.expectedBlockedRequests.find(
        (candidate) => candidate.url === expectation.url,
      );
      if (existing) existing.count += expectation.count;
      else state.expectedBlockedRequests.push(expectation);
    },
    expectBlockedWebSocket(expectation) {
      state.expectedBlockedWebSockets.push(
        normalizeWebSocketExpectation(expectation),
      );
    },
    expectFailedRequest(expectation) {
      state.expectedFailedRequests.push(
        normalizeRequestExpectation(expectation, { countRequired: true }),
      );
    },
    expectResponseScanViolation(expectation) {
      state.expectedResponseScanViolations.push(
        normalizeResponseScanViolationExpectation(expectation),
      );
    },
    expectForbiddenResponse(url, sentinel) {
      state.expectedForbiddenMatches.add(`${url}\n${sentinel}`);
    },
    hold(path) {
      return createHold(state, path);
    },
    release(path) {
      releaseHold(state, path);
    },
    assertManifestResources(manifest, requiredNames, lazyNames) {
      assertManifestClassification(manifest, requiredNames, lazyNames);
      assertSuccessfulAssets(state, requiredNames);
    },
    assert() {
      return assertPolicyStateWithFailureArtifact(state);
    },
    requestRecords() {
      return state.requestRecords
        .filter((record) => !state.retiredRequestRecords.has(record))
        .map((record) => ({ ...record }));
    },
    consoleErrors() {
      return [...state.consoleErrors];
    },
    pageErrors() {
      return [...state.pageErrors];
    },
    forbiddenResponseMatches() {
      return state.forbiddenMatches.map((match) => ({ ...match }));
    },
    responseScanSkips() {
      return state.responseScanSkips.map((skip) => ({ ...skip }));
    },
    responseScanViolations() {
      return state.responseScanViolations.map((violation) => ({ ...violation }));
    },
    responseScanDiagnostics() {
      return state.responseScanDiagnostics.map((diagnostic) => ({
        ...diagnostic,
      }));
    },
    blockedRequestRecords() {
      return state.blockedRequestRecords.map((record) => ({ ...record }));
    },
    blockedWebSocketRecords() {
      return state.blockedWebSocketRecords.map((record) => ({ ...record }));
    },
  };
}

function trackRequest(request, state) {
  state.requestMethods.push({ method: request.method(), url: request.url() });
  let requestOrigin;
  try {
    const url = new URL(request.url());
    requestOrigin = url.origin;
    if (isSameOrigin(url.href, state.expectedOrigin)) {
      const record = {
        method: request.method(),
        resourceType: request.resourceType(),
        url: redactUrl(request.url(), state),
      };
      state.requestRecords.push(record);
      state.requestRecordEntries.push({
        origin: url.origin,
        record,
        request,
      });
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
    url: redactUrl(request.url(), state),
  });
  state.relevantRequestOrigins.set(request, requestOrigin);
}

async function installNetworkStreaming(page, state) {
  try {
    const cdpSession = await page.context().newCDPSession(page);
    state.cdpSession = cdpSession;
    cdpSession.on("Network.requestWillBeSent", (event) => {
      trackNetworkRequest(event, state);
    });
    cdpSession.on("Network.responseReceived", (event) => {
      queueNetworkResponseScan(event, state);
    });
    cdpSession.on("Network.dataReceived", (event) => {
      receiveNetworkResponseData(event, state);
    });
    cdpSession.on("Network.loadingFinished", (event) => {
      finishNetworkResponse(event, state, { failed: false });
    });
    cdpSession.on("Network.loadingFailed", (event) => {
      finishNetworkResponse(event, state, {
        failed: true,
        error: event.errorText,
      });
    });
    await cdpSession.send("Network.enable", {
      maxTotalBufferSize: RESPONSE_SCAN_BYTES * MAX_RESPONSE_SCANS,
      maxResourceBufferSize: RESPONSE_SCAN_BYTES,
    });
    await cdpSession.send("Network.setCacheDisabled", {
      cacheDisabled: true,
    });
  } catch (error) {
    state.streamingSetupError = {
      reason: "network-streaming-unavailable",
      error: redactDiagnostic(error?.message || String(error), state),
    };
  }
}

function trackNetworkRequest(event, state) {
  if (isDocumentRequest(event)) startNetworkNavigation(state);
  const previous = state.networkRequests.get(event.requestId);
  if (previous) {
    retireNetworkRequest(previous, state, "request-id-reused");
  }
  const request = {
    requestId: event.requestId,
    method: event.request.method,
    resourceType: event.type,
    url: event.request.url,
    origin: requestOrigin(event.request.url),
    navigationEpoch: state.navigationEpoch,
    retired: false,
    retireReason: undefined,
    settled: false,
    retirement: createRetirement(),
    streaming: undefined,
    completion: undefined,
  };
  state.networkRequests.set(event.requestId, request);
  state.retiredRequestIds.delete(event.requestId);
  if (!isStreamEligibleRequest(event.request, state.expectedOrigin)) return;
  request.streaming = {
    established: false,
    error: undefined,
    preStreamDataSeen: false,
    preResponse: createBoundedAccumulator(),
  };
  request.streaming.promise = state.cdpSession.send(
    "Network.streamResourceContent",
    { requestId: event.requestId },
  ).then((result) => {
    request.streaming.established = true;
    if (!request.retired) {
      deliverNetworkChunk(
        request,
        result?.bufferedData,
        undefined,
        "base64",
        state,
      );
    }
    return request.streaming;
  }).catch((error) => {
    request.streaming.error = error;
    return request.streaming;
  });
}

function createRetirement() {
  let resolve;
  const promise = new Promise((resolvePromise) => {
    resolve = resolvePromise;
  });
  return { promise, resolve };
}

function startNetworkNavigation(state) {
  state.navigationEpoch += 1;
  for (const request of state.networkRequests.values()) {
    if (request.navigationEpoch < state.navigationEpoch) {
      retireNetworkRequest(request, state, "navigation");
    }
  }
}

function retireRequestsOutsideOrigin(state, expectedOrigin, reason) {
  for (const request of state.networkRequests.values()) {
    if (request.origin && request.origin !== expectedOrigin) {
      retireNetworkRequest(request, state, reason);
    }
  }
  for (const [request, origin] of state.relevantRequestOrigins) {
    if (origin !== expectedOrigin) {
      state.retiredRequests.add(request);
      state.settledRequests.add(request);
    }
  }
  for (const entry of state.requestRecordEntries) {
    if (entry.origin !== expectedOrigin) {
      state.retiredRequestRecords.add(entry.record);
    }
  }
}

function retireNetworkRequest(request, state, reason) {
  if (request.retired) return;
  request.retired = true;
  request.retireReason = reason;
  state.retiredRequestIds.add(request.requestId);
  if (request.streaming) request.streaming.preResponse = undefined;
  const scan = state.activeResponseScans.get(request);
  if (scan) {
    scan.retired = true;
    scan.resolveCompletion({ failed: false, retired: true });
  }
  request.retirement.resolve({ retired: true });
}

function isDocumentRequest(event) {
  return event.type?.toLowerCase() === "document";
}

function requestOrigin(value) {
  try {
    return new URL(value).origin;
  } catch {
    return undefined;
  }
}

function trackResponse(response, state) {
  const request = response.request();
  if (state.retiredRequests.has(request)) {
    state.settledRequests.add(request);
    return;
  }
  if (isRelevantRequest(request, state.expectedOrigin)) {
    state.relevantResponses.set(request, response);
    state.settledRequests.add(request);
  }
  if (isSameOrigin(request.url(), state.expectedOrigin) &&
      (response.status() < 200 || response.status() >= 400)) {
    state.unsuccessfulResponses.push({
      method: request.method(),
      path: requestPath(response.url()),
      status: response.status(),
      resourceType: request.resourceType(),
      url: redactUrl(response.url(), state),
    });
  }
}

function trackFailure(request, state) {
  if (state.retiredRequests.has(request)) {
    state.settledRequests.add(request);
    return;
  }
  if (isRelevantRequest(request, state.expectedOrigin)) {
    state.settledRequests.add(request);
  }
  const details = {
    method: request.method(),
    path: requestPath(request.url()),
    error: redactDiagnostic(
      request.failure()?.errorText || "unknown request failure",
      state,
    ),
    resourceType: request.resourceType(),
    url: redactUrl(request.url(), state),
  };
  state.failedRequests.push(details);
  state.failedRequestRawUrls.set(details, request.url());
}

function createHold(state, path) {
  if (state.holds.has(path)) {
    throw new Error(`request hold already exists: ${path}`);
  }
  let resolveHeld;
  let resolveRelease;
  const held = new Promise((resolve) => {
    resolveHeld = resolve;
  });
  const release = new Promise((resolve) => {
    resolveRelease = resolve;
  });
  state.holds.set(path, { release, resolveHeld, resolveRelease });
  return held;
}

function releaseHold(state, path) {
  const hold = state.holds.get(path);
  if (!hold) throw new Error(`request hold does not exist: ${path}`);
  state.holds.delete(path);
  hold.resolveRelease();
}

function normalizeHttpErrorExpectation(expectation) {
  if (!Number.isInteger(expectation?.status) ||
      expectation.status < 100 ||
      expectation.status > 599) {
    throw new TypeError("HTTP error expectations require a valid status");
  }
  return {
    ...normalizeRequestExpectation(expectation),
    status: expectation.status,
  };
}

function normalizeConsoleErrorExpectation(expectation, state) {
  if (!expectation || typeof expectation !== "object" ||
      typeof expectation.message !== "string" ||
      !Number.isInteger(expectation.count) ||
      expectation.count < 1) {
    throw new TypeError(
      "console error expectations require message and positive count",
    );
  }
  return {
    message: redactDiagnostic(expectation.message, state),
    count: expectation.count,
  };
}

function normalizeWebSocketExpectation(expectation) {
  if (!expectation || typeof expectation !== "object" ||
      typeof expectation.url !== "string" ||
      !Number.isInteger(expectation.count) ||
      expectation.count < 1) {
    throw new TypeError(
      "WebSocket expectations require url and positive count",
    );
  }
  try {
    new URL(expectation.url);
  } catch {
    throw new TypeError("WebSocket expectations require an absolute URL");
  }
  return { url: expectation.url, count: expectation.count };
}

function normalizeRequestExpectation(expectation, { countRequired = false } = {}) {
  if (!expectation || typeof expectation !== "object") {
    throw new TypeError("request expectations must be objects");
  }
  const path = expectation.path ?? expectation.url;
  const count = expectation.count ?? (countRequired ? undefined : 1);
  if (
    typeof expectation.method !== "string" ||
    typeof path !== "string" ||
    !Number.isInteger(count) ||
    count < 1
  ) {
    throw new TypeError(
      "request expectations require method, path or url, and positive count",
    );
  }
  return {
    method: expectation.method.toUpperCase(),
    path,
    count,
  };
}

function normalizeResponseScanViolationExpectation(expectation) {
  if (!expectation || typeof expectation !== "object" ||
      typeof expectation.method !== "string" ||
      typeof expectation.path !== "string" ||
      !Number.isInteger(expectation.status) ||
      expectation.status < 100 ||
      expectation.status > 599 ||
      typeof expectation.reason !== "string" ||
      !Number.isInteger(expectation.count) ||
      expectation.count < 1) {
    throw new TypeError(
      "response scan violation expectations require method, path, status, " +
      "reason, and positive count",
    );
  }
  return {
    method: expectation.method.toUpperCase(),
    path: expectation.path,
    status: expectation.status,
    reason: expectation.reason,
    count: expectation.count,
  };
}

function trackConsoleError(message, state) {
  const location = message.location();
  const url = location.url || undefined;
  const record = {
    method: methodForUrl(url, state),
    path: url ? requestPath(url) : undefined,
    text: redactDiagnostic(message.text(), state),
    url: url ? redactUrl(url, state) : undefined,
  };
  state.consoleErrorRecords.push(record);
  state.consoleErrors.push(record.text);
}

function queueNetworkResponseScan(event, state) {
  const request = state.networkRequests.get(event.requestId);
  if (consumeInterceptedResponseCoverage(event, request, state)) return;
  if (state.scanCount >= MAX_RESPONSE_SCANS) return;
  const response = networkResponseDescriptor(event, request);
  if (request && request.url !== event.response.url) {
    state.responseScanSkips.push({
      ...responseScanDetails(response, state),
      reason: "request-url-mismatch",
    });
    return;
  }
  if (request?.retired || request?.settled ||
      (!request && state.retiredRequestIds.has(event.requestId))) {
    state.responseScanSkips.push({
      ...responseScanDetails(response, state),
      reason: request?.settled
        ? "request-already-settled"
        : request?.retireReason || "request-retired",
    });
    return;
  }
  const eligibility = responseScanEligibility(response, state);
  if (!eligibility.eligible) {
    if (eligibility.record) state.responseScanSkips.push(eligibility.record);
    return;
  }
  state.scanCount += 1;
  const scan = createScanAccumulator(
    responseScanDetails(response, state),
    eligibility.declaredLength,
  );
  scan.syntheticResponse = response.synthetic;
  scan.request = request;
  scan.requestId = event.requestId;
  const scanKey = request || event.requestId;
  scan.scanKey = scanKey;
  state.activeResponseScans.set(scanKey, scan);
  if (request?.streaming?.established) {
    adoptPreResponseData(scan, request.streaming);
  }
  const scanPromise = scanNetworkResponse(
    event,
    response,
    eligibility,
    state,
  ).finally(() => {
    state.scanPromises.delete(scanPromise);
  });
  state.scanPromises.add(scanPromise);
}

async function scanNetworkResponse(event, response, eligibility, state) {
  const request = state.networkRequests.get(event.requestId);
  const streaming = request?.streaming;
  const scan = state.activeResponseScans.get(request || event.requestId);
  const strict = isSyntheticResponse(response, state);
  try {
    if (request?.retired || scan.retired) return;
    if (!streaming) {
      recordScanProblem(
        state,
        scan,
        "streaming-unavailable",
        undefined,
        strict,
      );
      return;
    }
    await Promise.race([streaming.promise, request.retirement.promise]);
    if (request.retired || scan.retired) return;
    if (streaming.error) {
      recordScanProblem(
        state,
        scan,
        "streaming-unavailable",
        streaming.error,
        strict,
      );
      return;
    }
    scan.streamEstablished = true;
    if (scan.preStreamDataSeen &&
        scan.capturedBytes === 0 &&
        scan.declaredLength > 0) {
      scan.dataUnavailable = true;
    }
    const completion = request.completion || await Promise.race([
      scan.completion,
      request.retirement.promise,
    ]);
    if (request.retired || scan.retired || completion.retired) return;
    if (completion.failed) {
      recordScanProblem(
        state,
        scan,
        "streaming-failed",
        completion.error,
        strict,
      );
      return;
    }

    finalizeResponseScan(scan, state, strict);
  } catch (error) {
    recordScanProblem(state, scan, "streaming-unavailable", error, strict);
  } finally {
    if (state.activeResponseScans.get(scan.scanKey) === scan) {
      state.activeResponseScans.delete(scan.scanKey);
    }
    retainScanDiagnostic(scan, state);
  }
}

function receiveNetworkResponseData(event, state) {
  const request = state.networkRequests.get(event.requestId);
  const streaming = request?.streaming;
  if (!streaming || request.retired) return;
  const scan = state.activeResponseScans.get(request);
  if (!streaming.established) {
    streaming.preStreamDataSeen ||= event.dataLength > 0;
    if (scan) scan.preStreamDataSeen ||= event.dataLength > 0;
    return;
  }
  deliverNetworkChunk(
    request,
    event.data,
    event.dataLength,
    "base64",
    state,
  );
}

function finishNetworkResponse(event, state, completion) {
  const request = state.networkRequests.get(event.requestId);
  if (!request) return;
  request.settled = true;
  request.completion = completion;
  if (request.retired) return;
  const scan = state.activeResponseScans.get(request);
  if (!scan) return;
  if (completion.failed) {
    scan.resolveCompletion(completion);
    return;
  }
  scan.resolveCompletion({
    failed: false,
    encodedDataLength: event.encodedDataLength,
  });
}

function deliverNetworkChunk(
  requestOrId,
  chunk,
  reportedLength,
  encoding,
  state,
) {
  const request = typeof requestOrId === "object"
    ? requestOrId
    : state.networkRequests.get(requestOrId);
  const streaming = request?.streaming;
  if (!streaming || request.retired) return;
  const scan = state.activeResponseScans.get(request);
  if (scan) {
    consumeResponseChunk(scan, chunk, reportedLength, encoding);
  } else {
    consumeBoundedChunk(
      streaming.preResponse,
      chunk,
      reportedLength,
      encoding,
    );
  }
}

function networkResponseDescriptor(event, request) {
  const response = event.response;
  return {
    headers: () => ({ ...(response.headers || {}) }),
    synthetic: response.connectionId === 0,
    request: () => ({
      method: () => request?.method || "GET",
      resourceType: () => request?.resourceType || event.type,
    }),
    status: () => response.status,
    url: () => response.url,
  };
}

function isSyntheticResponse(response, state) {
  if (state.syntheticResponses || response.synthetic) return true;
  const path = requestPath(response.url());
  return [...state.interceptions.keys()].some((candidate) =>
    candidate === path || candidate === path.split("?", 1)[0],
  );
}

function createScanAccumulator(details, declaredLength) {
  let resolveCompletion;
  const completion = new Promise((resolve) => {
    resolveCompletion = resolve;
  });
  return {
    ...details,
    declaredLength,
    prefix: Buffer.alloc(RESPONSE_SCAN_BYTES),
    capturedBytes: 0,
    observedLength: 0,
    maxRetainedBytes: RESPONSE_SCAN_BYTES,
    dataUnavailable: false,
    preStreamDataSeen: false,
    streamEstablished: false,
    scanMechanism: "network-stream",
    completion,
    resolveCompletion,
  };
}

function createBoundedAccumulator() {
  return {
    prefix: Buffer.alloc(RESPONSE_SCAN_BYTES),
    capturedBytes: 0,
    observedLength: 0,
    dataUnavailable: false,
  };
}

function adoptPreResponseData(scan, streaming) {
  scan.preStreamDataSeen = streaming.preStreamDataSeen;
  scan.observedLength += streaming.preResponse.observedLength;
  scan.capturedBytes = streaming.preResponse.capturedBytes;
  scan.dataUnavailable = streaming.preResponse.dataUnavailable;
  streaming.preResponse.prefix.subarray(0, scan.capturedBytes).copy(
    scan.prefix,
    0,
  );
  streaming.preResponse = undefined;
}

function consumeResponseChunk(scan, chunk, reportedLength, encoding = "bytes") {
  const actualLength = reportedLength === undefined
    ? byteLengthOfChunk(chunk, encoding)
    : reportedLength;
  if (Number.isFinite(actualLength) && actualLength >= 0) {
    scan.observedLength += actualLength;
  }
  if (chunk === undefined || scan.capturedBytes >= RESPONSE_SCAN_BYTES) return;
  const remaining = RESPONSE_SCAN_BYTES - scan.capturedBytes;
  const copied = copyChunkPrefix(
    chunk,
    scan.prefix,
    scan.capturedBytes,
    remaining,
    encoding,
  );
  scan.capturedBytes += copied;
}

function consumeBoundedChunk(
  accumulator,
  chunk,
  reportedLength,
  encoding = "bytes",
) {
  if (!accumulator) return;
  const actualLength = reportedLength === undefined
    ? byteLengthOfChunk(chunk, encoding)
    : reportedLength;
  if (Number.isFinite(actualLength) && actualLength >= 0) {
    accumulator.observedLength += actualLength;
  }
  if (chunk === undefined || accumulator.capturedBytes >= RESPONSE_SCAN_BYTES) {
    if (actualLength > 0 && chunk === undefined) {
      accumulator.dataUnavailable = true;
    }
    return;
  }
  const remaining = RESPONSE_SCAN_BYTES - accumulator.capturedBytes;
  const copied = copyChunkPrefix(
    chunk,
    accumulator.prefix,
    accumulator.capturedBytes,
    remaining,
    encoding,
  );
  accumulator.capturedBytes += copied;
}

function finalizeResponseScan(scan, state, strict = true) {
  if (scan.dataUnavailable) {
    recordScanProblem(state, scan, "stream-data-unavailable", undefined, strict);
    return;
  }
  const actualLength = scan.observedLength;
  if (actualLength > RESPONSE_SCAN_BYTES ||
      (!scan.syntheticResponse && actualLength !== scan.declaredLength)) {
    state.responseScanViolations.push({
      ...scanDiagnostic(scan),
      actualLength,
      exceedsDeclared: actualLength > scan.declaredLength,
      exceedsPolicy: actualLength > RESPONSE_SCAN_BYTES,
      reason: "actual-body-size-mismatch",
    });
    return;
  }
  const text = new TextDecoder().decode(
    scan.prefix.subarray(0, scan.capturedBytes),
  );
  for (const sentinel of FORBIDDEN_SENTINELS) {
    if (text.includes(sentinel)) {
      state.forbiddenMatches.push({
        sentinel,
        url: scan.url,
      });
    }
  }
}

function recordStreamingViolation(state, scan, reason, error) {
  const details = scanDiagnostic(scan);
  if (error) {
    details.error = redactDiagnostic(
      error?.message || String(error),
      state,
    );
  }
  state.responseScanViolations.push({ ...details, reason });
}

function recordScanProblem(state, scan, reason, error, strict) {
  if (strict) {
    recordStreamingViolation(state, scan, reason, error);
    return;
  }
  state.responseScanSkips.push({
    ...scanDiagnostic(scan),
    reason,
    ...(error ? {
      error: redactDiagnostic(error?.message || String(error), state),
    } : {}),
  });
}

function retainScanDiagnostic(scan, state) {
  state.responseScanDiagnostics.push(scanDiagnostic(scan));
  scan.prefix = undefined;
}

function scanDiagnostic(scan) {
  return {
    method: scan.method,
    path: scan.path,
    status: scan.status,
    resourceType: scan.resourceType,
    url: scan.url,
    declaredLength: scan.declaredLength,
    observedLength: scan.observedLength,
    capturedBytes: scan.capturedBytes,
    maxRetainedBytes: scan.maxRetainedBytes,
    streamEstablished: scan.streamEstablished,
    scanMechanism: scan.scanMechanism,
  };
}

export async function scanResponseForTest(response, {
  expectedOrigin = new URL(response.url()).origin,
  sensitiveValues = [],
  streamResponse,
} = {}) {
  const state = {
    expectedOrigin,
    sensitiveValues,
    responseScanSkips: [],
    responseScanViolations: [],
    responseScanDiagnostics: [],
    forbiddenMatches: [],
    syntheticResponses: true,
  };
  const eligibility = responseScanEligibility(response, state);
  if (!eligibility.eligible) {
    if (eligibility.record) state.responseScanSkips.push(eligibility.record);
  } else {
    await scanResponseForTestTransport(
      response,
      eligibility,
      state,
      streamResponse,
    );
  }
  return {
    forbiddenMatches: state.forbiddenMatches.map((match) => ({ ...match })),
    responseScanSkips: state.responseScanSkips.map((skip) => ({ ...skip })),
    responseScanViolations: state.responseScanViolations.map((violation) => ({
      ...violation,
    })),
    responseScanDiagnostics: state.responseScanDiagnostics.map((diagnostic) => ({
      ...diagnostic,
    })),
  };
}

async function scanResponseForTestTransport(
  response,
  eligibility,
  state,
  streamResponse,
) {
  const scan = createScanAccumulator(
    responseScanDetails(response, state),
    eligibility.declaredLength,
  );
  try {
    const streamFactory = streamResponse || response.stream;
    if (typeof streamFactory !== "function") {
      recordStreamingViolation(state, scan, "streaming-unavailable");
      return;
    }
    const chunks = await streamFactory();
    scan.streamEstablished = true;
    scan.scanMechanism = "test-stream";
    for await (const chunk of chunks) consumeResponseChunk(scan, chunk);
    finalizeResponseScan(scan, state, true);
  } catch (error) {
    recordStreamingViolation(state, scan, "streaming-unavailable", error);
  } finally {
    retainScanDiagnostic(scan, state);
  }
}

function responseScanEligibility(response, state) {
  const details = responseScanDetails(response, state);
  if (!isSameOrigin(response.url(), state.expectedOrigin)) {
    return { eligible: false };
  }
  if (responseHasNoBody(response)) {
    return {
      eligible: false,
      record: { ...details, reason: "response-has-no-body" },
    };
  }

  let headers;
  try {
    headers = response.headers();
  } catch {
    return {
      eligible: false,
      record: { ...details, reason: "headers-unavailable" },
    };
  }
  const contentLength = parseContentLength(headers);
  if (!contentLength.valid) {
    return {
      eligible: false,
      record: { ...details, reason: contentLength.reason },
    };
  }
  if (contentLength.value > RESPONSE_SCAN_BYTES) {
    return {
      eligible: false,
      record: {
        ...details,
        declaredLength: contentLength.value,
        reason: "content-length-exceeds-policy",
      },
    };
  }
  if (!isScannableHeaders(headers)) {
    return { eligible: false };
  }
  return {
    eligible: true,
    declaredLength: contentLength.value,
  };
}

function responseScanDetails(response, state) {
  let request;
  try {
    request = response.request();
  } catch {
    request = undefined;
  }
  return {
    method: request?.method?.() || "GET",
    path: requestPath(response.url()),
    status: response.status(),
    resourceType: request?.resourceType?.(),
    url: redactUrl(response.url(), state),
  };
}

function responseHasNoBody(response) {
  const method = response.request().method().toUpperCase();
  const status = response.status();
  return method === "HEAD" ||
    (status >= 100 && status < 200) ||
    [204, 205, 304].includes(status);
}

function parseContentLength(headers) {
  const rawValue = Object.entries(headers || {})
    .filter(([name]) => name.toLowerCase() === "content-length")
    .map(([, value]) => value)
    .join(",");
  if (!rawValue) return { valid: false, reason: "content-length-missing" };
  const values = rawValue.split(",").map((value) => value.trim());
  if (values.some((value) => !/^\d+$/u.test(value))) {
    return { valid: false, reason: "content-length-invalid" };
  }
  const numbers = values.map(Number);
  if (numbers.some((value) => !Number.isSafeInteger(value))) {
    return { valid: false, reason: "content-length-invalid" };
  }
  if (new Set(numbers).size !== 1) {
    return { valid: false, reason: "content-length-conflicting" };
  }
  return { valid: true, value: numbers[0] };
}

function isScannableHeaders(headers) {
  const contentType = Object.entries(headers || {})
    .find(([name]) => name.toLowerCase() === "content-type")?.[1] || "";
  return /(?:html|javascript|json|css|text|xml)/iu.test(contentType);
}

function byteLengthOfChunk(value, encoding = "bytes") {
  if (value === undefined || value === null) return 0;
  if (Buffer.isBuffer(value)) return value.length;
  if (value instanceof Uint8Array) return value.byteLength;
  if (typeof value === "string") {
    return encoding === "base64"
      ? base64ByteLength(value)
      : Buffer.byteLength(value, "utf8");
  }
  throw new TypeError("response stream yielded a non-byte chunk");
}

function copyChunkPrefix(chunk, target, offset, limit, encoding = "bytes") {
  if (limit <= 0 || chunk === undefined || chunk === null) return 0;
  if (Buffer.isBuffer(chunk) || chunk instanceof Uint8Array) {
    const length = Math.min(chunk.byteLength, limit);
    target.set(chunk.subarray(0, length), offset);
    return length;
  }
  if (typeof chunk === "string") {
    const prefix = encoding === "base64"
      ? Buffer.from(chunk.slice(0, Math.ceil(limit / 3) * 4), "base64")
      : Buffer.from(chunk.slice(0, limit), "utf8");
    const length = Math.min(prefix.length, limit);
    target.set(prefix.subarray(0, length), offset);
    return length;
  }
  throw new TypeError("response stream yielded a non-byte chunk");
}

function base64ByteLength(value) {
  const padding = value.endsWith("==") ? 2 : value.endsWith("=") ? 1 : 0;
  return Math.max(0, Math.floor(value.length * 3 / 4) - padding);
}

function isRelevantRequest(request, expectedOrigin) {
  if (!isSameOrigin(request.url(), expectedOrigin)) return false;
  if (["document", "script", "stylesheet", "font", "worker"].includes(
    request.resourceType(),
  )) return true;
  try {
    const url = new URL(request.url());
    return (
      url.pathname === "/manifest.json" || /\.(?:js|css|ttf)$/.test(url.pathname)
    );
  } catch {
    return false;
  }
}

function isStreamEligibleRequest(request, expectedOrigin) {
  return request.method.toUpperCase() !== "HEAD" &&
    isSameOrigin(request.url, expectedOrigin);
}

function isSameOrigin(value, expectedOrigin) {
  try {
    return new URL(value).origin === expectedOrigin;
  } catch {
    return false;
  }
}

function redactUrl(value, state) {
  try {
    const url = new URL(value);
    if (url.protocol === "file:" || url.protocol === "data:") {
      return `${url.protocol}[redacted]`;
    }
    url.hash = "";
    for (const key of [...url.searchParams.keys()]) {
      if (/(?:token|secret|password|capability|credential|authorization)/iu.test(key)) {
        url.searchParams.set(key, "[REDACTED]");
      }
    }
    return redactDiagnostic(url.href, state);
  } catch {
    return "[invalid-url]";
  }
}

function redactDiagnostic(value, state) {
  let text = redactSensitiveText(value, state.sensitiveValues);
  if (tmpdir()) {
    const escapedTempDirectory = tmpdir().replace(/[.*+?^${}()|[\]\\]/gu, "\\$&");
    text = text.replace(
      new RegExp(
        escapedTempDirectory + "(?:[/\\\\][^\\s\"'`]+)?",
        "gu",
      ),
      "[PATH_REDACTED]",
    );
  }
  return text.length > 512 ? `${text.slice(0, 512)}…` : text;
}

async function routeRequest(route, state) {
  let url;
  try {
    url = new URL(route.request().url());
  } catch {
    const rawUrl = route.request().url();
    state.blockedRequests.push(rawUrl);
    const details = {
      method: route.request().method(),
      resourceType: route.request().resourceType(),
      url: "[invalid-url]",
    };
    state.blockedRequestRecords.push(details);
    state.blockedRequestRawUrls.set(details, rawUrl);
    await route.abort("blockedbyclient");
    return;
  }
  if (!isAllowedUrl(url, state.expectedOrigin)) {
    state.blockedRequests.push(url.href);
    const details = {
      method: route.request().method(),
      resourceType: route.request().resourceType(),
      url: redactUrl(url.href, state),
    };
    state.blockedRequestRecords.push(details);
    state.blockedRequestRawUrls.set(details, url.href);
    await route.abort("blockedbyclient");
    return;
  }
  const interception =
    state.interceptions.get(url.pathname + url.search) ||
    state.interceptions.get(url.pathname);
  const hold = state.holds.get(url.pathname + url.search) ||
    state.holds.get(url.pathname);
  if (hold) {
    hold.resolveHeld();
    await hold.release;
  }
  if (interception) {
    scanInterceptedResponse(route.request(), interception, state);
    await route.fulfill(attachInterceptedResponseCoverage(
      route.request(),
      interception,
      state,
    ));
    return;
  }
  if (state.patchApplication && /\/app(?:-[^/]+)?\.js$/.test(url.pathname)) {
    await routeWithEditorFailure(route);
    return;
  }
  await route.continue();
}

function scanInterceptedResponse(routeRequest, interception, state) {
  const response = {
    headers: () => interception.headers,
    request: () => routeRequest,
    status: () => interception.status,
    url: () => routeRequest.url(),
  };
  if (state.scanCount >= MAX_RESPONSE_SCANS) {
    state.responseScanViolations.push({
      ...responseScanDetails(response, state),
      reason: "scan-budget-exhausted",
    });
    return;
  }
  const eligibility = responseScanEligibility(response, state);
  if (!eligibility.eligible) {
    if (eligibility.record) state.responseScanSkips.push(eligibility.record);
    return;
  }
  state.scanCount += 1;
  const scan = createScanAccumulator(
    responseScanDetails(response, state),
    eligibility.declaredLength,
  );
  scan.syntheticResponse = true;
  scan.scanMechanism = "intercepted-body";
  consumeResponseChunk(scan, interception.body);
  finalizeResponseScan(scan, state, true);
  retainScanDiagnostic(scan, state);
}

function attachInterceptedResponseCoverage(routeRequest, interception, state) {
  const marker = randomUUID();
  state.interceptedResponseCoverage.set(marker, {
    method: routeRequest.method(),
    resourceType: routeRequest.resourceType().toLowerCase(),
    status: interception.status,
    url: routeRequest.url(),
  });
  return {
    ...interception,
    headers: {
      ...interception.headers,
      [INTERCEPTED_COVERAGE_HEADER]: marker,
    },
  };
}

function consumeInterceptedResponseCoverage(event, request, state) {
  const marker = headerValue(
    event.response.headers,
    INTERCEPTED_COVERAGE_HEADER,
  );
  if (!marker) return false;
  const expected = state.interceptedResponseCoverage.get(marker);
  if (
    !expected ||
    event.response.connectionId !== 0 ||
    !request ||
    request.method !== expected.method ||
    request.resourceType?.toLowerCase() !== expected.resourceType ||
    request.url !== expected.url ||
    event.response.url !== expected.url ||
    event.response.status !== expected.status
  ) {
    return false;
  }
  state.interceptedResponseCoverage.delete(marker);
  return true;
}

function headerValue(headers, expectedName) {
  const entry = Object.entries(headers || {}).find(
    ([name]) => name.toLowerCase() === expectedName,
  );
  return entry === undefined ? undefined : String(entry[1]);
}

function normalizeInterceptedResponse(options) {
  if (!options || typeof options !== "object") {
    throw new TypeError("intercepted response options must be an object");
  }
  if (options.path !== undefined || options.response !== undefined) {
    throw new TypeError(
      "intercepted response must provide bounded inline body or JSON",
    );
  }
  if (options.body !== undefined && options.json !== undefined) {
    throw new TypeError("intercepted response cannot specify both body and JSON");
  }
  let body = options.body;
  if (options.json !== undefined) body = JSON.stringify(options.json);
  if (body !== undefined && typeof body !== "string" && !Buffer.isBuffer(body)) {
    throw new TypeError("intercepted response body must be bytes or text");
  }
  const length = typeof body === "string"
    ? Buffer.byteLength(body)
    : body?.length || 0;
  const headers = {};
  for (const [name, value] of Object.entries(options.headers || {})) {
    headers[name.toLowerCase()] = String(value);
  }
  if (options.contentType) {
    headers["content-type"] = String(options.contentType);
  } else if (options.json) {
    headers["content-type"] = "application/json";
  }
  if (length && headers["content-length"] === undefined) {
    headers["content-length"] = String(length);
  }
  return {
    status: options.status || 200,
    headers,
    body,
  };
}

async function routeWebSocket(webSocket, state) {
  const url = webSocket.url();
  const details = { url: redactUrl(url, state) };
  state.webSocketRecords.push(details);
  if (isAllowedWebSocketUrl(url, state.expectedOrigin)) {
    webSocket.connectToServer();
    return;
  }
  state.blockedWebSocketRecords.push(details);
  state.blockedWebSocketRawUrls.set(details, url);
  await webSocket.close({
    code: 1008,
    reason: "WebSocket blocked by default",
  });
}

function isAllowedUrl(url, expectedOrigin) {
  return isLoopbackUrl(url) && url.origin === expectedOrigin;
}

function isAllowedWebSocketUrl(value, expectedOrigin) {
  try {
    const socketUrl = new URL(value);
    const fixtureUrl = new URL(expectedOrigin);
    const expectedProtocol = fixtureUrl.protocol === "https:"
      ? "wss:"
      : fixtureUrl.protocol === "http:"
        ? "ws:"
        : undefined;
    return expectedProtocol !== undefined &&
      socketUrl.protocol === expectedProtocol &&
      socketUrl.hostname === fixtureUrl.hostname &&
      effectivePort(socketUrl) === effectivePort(fixtureUrl);
  } catch {
    return false;
  }
}

function effectivePort(url) {
  if (url.port) return Number(url.port);
  return url.protocol === "https:" || url.protocol === "wss:" ? 443 : 80;
}

function isLoopbackUrl(url) {
  return ["127.0.0.1", "localhost", "::1"].includes(url.hostname);
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
    if (state.retiredRequests.has(request)) continue;
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

async function assertPolicyState(state) {
  await drainResponseScansForTest(state.scanPromises);
  if (state.streamingSetupError) {
    const details = {
      label: "response scan streaming",
      ...state.streamingSetupError,
    };
    const error = new Error(
      `response scan streaming could not be established: ${JSON.stringify(details)}`,
    );
    error.details = details;
    throw error;
  }
  await expect.poll(
    () => [...state.relevantRequests.entries()]
      .filter(([request]) => !state.settledRequests.has(request))
      .map(([, details]) => details),
    {
      message: "relevant same-origin static requests did not settle",
      timeout: 5000,
    },
  ).toEqual([]);
  await drainResponseScansForTest(state.scanPromises);
  assertExpectedOccurrences(
    state.failedRequests.filter((request) =>
      !state.expectedBlockedRequests.some((expectation) =>
        matchesExpectedBlockedRequest(request, state, expectation),
      ) || state.expectedFailedRequests.some((expectation) =>
        matchesExpectedFailedRequest(request, state, expectation),
      ),
    ),
    state.expectedFailedRequests,
    (request, expectation) =>
      request.method === expectation.method &&
      matchesUrlPath(
        requestPath(state.failedRequestRawUrls.get(request)),
        expectation.path,
      ),
    "failed requests",
  );
  expect(state.failedRequests.filter((request) =>
    !state.expectedBlockedRequests.some((expectation) =>
      matchesExpectedBlockedRequest(request, state, expectation),
    ) &&
    !state.expectedFailedRequests.some((expectation) =>
      matchesExpectedFailedRequest(request, state, expectation),
    ),
  )).toEqual([]);
  assertExpectedOccurrences(
    state.blockedRequestRecords,
    state.expectedBlockedRequests,
    (record, expectation) =>
      matchesExpectedBlockedRequest(record, state, expectation),
    "blocked requests",
  );
  assertExpectedOccurrences(
    state.blockedWebSocketRecords,
    state.expectedBlockedWebSockets,
    (record, expectation) =>
      state.blockedWebSocketRawUrls.get(record) === expectation.url,
    "blocked WebSockets",
  );
  assertExpectedOccurrences(
    state.unsuccessfulResponses,
    state.expectedHttpErrors,
    matchesExpectedHttpError,
    "HTTP errors",
  );
  const blockedConsoleErrors = state.consoleErrorRecords.filter((record) =>
    record.text.includes("ERR_BLOCKED_BY_CLIENT"),
  );
  assertExpectedOccurrences(
    blockedConsoleErrors,
    state.expectedBlockedConsoleErrors,
    matchesExpectedBlockedConsoleError,
    "blocked console errors",
  );
  const explicitConsoleErrors = state.expectedConsoleErrors.map(
    (expectation) => ({ ...expectation, matched: 0 }),
  );
  const httpConsoleErrors = state.expectedHttpErrors.map(
    (expectation) => ({ ...expectation, matched: 0 }),
  );
  const unexpectedConsoleErrors = [];
  for (const record of state.consoleErrorRecords) {
    const explicit = explicitConsoleErrors.find((expectation) =>
      expectation.matched < expectation.count &&
      expectation.message === record.text,
    );
    if (explicit) {
      explicit.matched += 1;
      continue;
    }
    const http = httpConsoleErrors.find((expectation) =>
      expectation.matched < expectation.count &&
      isExpectedHttpConsoleError(record, expectation),
    );
    if (http) {
      http.matched += 1;
      continue;
    }
    if (isExpectedBlockedConsoleError(
      record,
      state.expectedBlockedConsoleErrors,
    )) {
      continue;
    }
    unexpectedConsoleErrors.push(record);
  }
  for (const expectation of explicitConsoleErrors) {
    expect(
      expectation.matched,
      `expected ${expectation.count} console errors for ${expectation.message}`,
    ).toBe(expectation.count);
  }
  expect(
    unexpectedConsoleErrors.map(({ method, path, url }) => ({
      method,
      path,
      url,
    })),
    "unexpected console errors",
  ).toEqual([]);
  expect(state.pageErrors).toEqual([]);
  assertExpectedOccurrences(
    state.responseScanViolations,
    state.expectedResponseScanViolations,
    matchesExpectedResponseScanViolation,
    "response scan policy violations",
  );
  expect(state.forbiddenMatches.filter((match) =>
    !isExpectedForbiddenMatch(match, state.expectedForbiddenMatches),
  )).toEqual([]);
  for (const request of state.sameOriginRequests) {
    expect(
      isDocumentedRequest(request.path),
      `undocumented same-origin request: ${JSON.stringify(request)}`,
    ).toBe(true);
  }
  for (const [request, details] of state.relevantRequests) {
    if (state.retiredRequests.has(request)) continue;
    expect(new URL(details.url).origin).toBe(state.expectedOrigin);
  }
}

export async function drainResponseScansForTest(scanPromises) {
  while (scanPromises.size > 0) {
    await Promise.all([...scanPromises]);
  }
}

async function assertPolicyStateWithFailureArtifact(state) {
  let policyError;
  try {
    await assertPolicyState(state);
  } catch (error) {
    policyError = error;
  }
  const testFailed = state.testInfo.status !== "passed" ||
    state.testInfo.errors?.length > 0;
  if (policyError || testFailed) {
    await attachFailureScreenshot(state);
  }
  if (policyError) throw policyError;
}

async function attachFailureScreenshot(state) {
  if (state.failureScreenshotCaptured) return;
  state.failureScreenshotCaptured = true;
  try {
    const body = await state.page.screenshot({
      mask: [
        state.page.locator(
          '[data-testid="prompt-pane"], .prompt-pane, .prompt-copy',
        ),
        state.page.locator(
          '[data-testid="editor-pane"], .editor-pane, .monaco-editor, ' +
            '.fallback, [data-sensitive-content="candidate"]',
        ),
        state.page.locator(
          '[data-testid="output-drawer"], .output-drawer, .history-list, ' +
            '.source-conflict, [data-sensitive-content="output"]',
        ),
      ],
      maskColor: "#000000",
    });
    await state.testInfo.attach("sanitized-failure-screenshot", {
      body: sanitizeFailureScreenshot(body),
      contentType: "image/png",
    });
  } catch {
    // A closed page cannot produce a screenshot; the trace remains available.
  }
}

function assertExpectedOccurrences(actual, expected, matches, label) {
  const remaining = [...actual];
  const mismatches = [];
  for (const expectation of expected) {
    const matched = remaining.filter((item) => matches(item, expectation));
    if (matched.length !== expectation.count) {
      mismatches.push({
        expectation,
        expectedCount: expectation.count,
        actualCount: matched.length,
        matched,
      });
      continue;
    }
    for (const item of matched) {
      remaining.splice(remaining.indexOf(item), 1);
    }
  }
  if (mismatches.length || remaining.length) {
    const details = {
      label,
      mismatches,
      unexpected: remaining,
    };
    const error = new Error(
      `exact ${label} occurrence assertion failed: ${JSON.stringify(details)}`,
    );
    error.details = details;
    throw error;
  }
}

function isExpectedHttpConsoleError(record, expected) {
  const match = record.text.match(/status of (\d{3})/u);
  return Boolean(match && matchesExpectedHttpError(record, {
    ...expected,
    status: Number(match[1]),
  }));
}

function isExpectedBlockedConsoleError(record, expected) {
  return record.text.includes("ERR_BLOCKED_BY_CLIENT") &&
    expected.some((expectation) =>
      matchesExpectedBlockedConsoleError(record, expectation),
    );
}

function matchesExpectedHttpError(record, expectation) {
  return record.method === expectation.method &&
    matchesUrlPath(
      /^[a-z][a-z\d+.-]*:/iu.test(expectation.path)
        ? record.url
        : record.path,
      expectation.path,
    ) &&
    (record.status === expectation.status ||
      Number(record.text.match(/status of (\d{3})/u)?.[1]) === expectation.status);
}

function matchesExpectedBlockedConsoleError(record, expectation) {
  return record.method === expectation.method &&
    matchesUrlPath(record.url, expectation.path);
}

function requestPath(value) {
  try {
    const url = new URL(value);
    return `${url.pathname}${url.search}`;
  } catch {
    return value;
  }
}

function matchesUrlPath(value, expected) {
  if (!value) return false;
  if (/^[a-z][a-z\d+.-]*:/iu.test(expected)) return value === expected;
  const actualPath = requestPath(value);
  if (expected.includes("?")) return actualPath === expected;
  return actualPath.split("?", 1)[0] === expected;
}

function methodForUrl(value, state) {
  return state.requestMethods.findLast(({ url }) => url === value)?.method || "GET";
}

function matchesExpectedRequest(value, expected) {
  if (expected.has(value)) return true;
  try {
    const url = new URL(value);
    return expected.has(url.pathname) ||
      expected.has(url.pathname + url.search);
  } catch {
    return false;
  }
}

function matchesExpectedBlockedRequest(request, state, expectation) {
  const rawUrl = state.blockedRequestRawUrls.get(request) ||
    state.failedRequestRawUrls.get(request);
  return matchesExpectedRequest(rawUrl, new Set([expectation.url]));
}

function normalizeBlockedRequestExpectation(urlOrExpectation, count) {
  const expectation = typeof urlOrExpectation === "string"
    ? { url: urlOrExpectation, count }
    : urlOrExpectation;
  if (
    !expectation ||
    typeof expectation.url !== "string" ||
    !Number.isInteger(expectation.count) ||
    expectation.count < 1
  ) {
    throw new TypeError(
      "blocked request expectations require url and positive count",
    );
  }
  return { url: expectation.url, count: expectation.count };
}

function matchesExpectedFailedRequest(request, state, expectation) {
  return request.method === expectation.method &&
    matchesUrlPath(
      state.failedRequestRawUrls.get(request),
      expectation.path,
    );
}

function matchesExpectedResponseScanViolation(violation, expectation) {
  return violation.method === expectation.method &&
    matchesUrlPath(violation.path, expectation.path) &&
    violation.status === expectation.status &&
    violation.reason === expectation.reason;
}

function isExpectedForbiddenMatch(match, expected) {
  for (const value of expected) {
    const [url, sentinel] = value.split("\n");
    if (sentinel === match.sentinel &&
        matchesExpectedRequest(match.url, new Set([url]))) {
      return true;
    }
  }
  return false;
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
  // Browser application routes documented in docs/cli-contract.md ("Browser
  // routes"): the server answers them with the shell, the client validates.
  if (
    path === "/history" ||
    /^\/attempt\/[A-Za-z0-9-]+$/u.test(path) ||
    /^\/history\/review\/[A-Za-z0-9-]+$/u.test(path)
  ) {
    return true;
  }
  if (path.startsWith("/api/")) {
    return (
      [
        "/api/bootstrap",
        "/api/attempts",
        "/api/source",
        "/api/source/history",
        "/api/source/reset",
        "/api/source/restore",
        "/api/time",
        "/api/test",
        "/api/submit",
      ].includes(path) ||
      /^\/api\/prompts\/[1-4]$/u.test(path) ||
      /^\/api\/attempts\/[0-9a-f-]{36}\/(?:abandon|restart)$/u.test(path)
    );
  }
  return /^\/[A-Za-z0-9._-]+\.(?:js|css|ttf)$/u.test(path);
}
