import { expect, test } from "@playwright/test";
import {
  installOfflineRequestPolicy,
  startFixtureServer,
} from "./browser_harness.mjs";

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

test("rejects unsafe direct HTTP requests with safe envelopes and fixed routes", async () => {
  const shell = await directRequest("/");
  expect(shell.status).toBe(200);
  expect(shell.headers["cache-control"]).toBe("no-store");
  expect(shell.headers["content-security-policy"]).toContain("default-src 'self'");
  expect(shell.headers["content-security-policy"]).toContain("connect-src 'self'");
  expect(shell.headers["content-security-policy"]).toContain("frame-ancestors 'none'");
  expect(shell.headers["permissions-policy"]).toContain("camera=()");

  const bootstrap = await directRequest("/api/bootstrap", {
    headers: capabilityHeaders(),
  });
  expect(bootstrap.status).toBe(200);
  expect(bootstrap.headers["cache-control"]).toBe("no-store");
  expect(bootstrap.headers["x-content-type-options"]).toBe("nosniff");
  expect(bootstrap.headers["access-control-allow-origin"]).toBeUndefined();

  const missingToken = await directRequest("/api/bootstrap");
  const wrongToken = await directRequest("/api/bootstrap", {
    headers: capabilityHeaders({ token: "wrong-capability" }),
  });
  const rejectedOrigin = await directRequest("/api/attempts", {
    method: "POST",
    headers: mutationHeaders({ origin: "http://127.0.0.1:9" }),
    body: JSON.stringify({}),
  });
  const rejectedMethod = await directRequest("/api/bootstrap", {
    method: "DELETE",
    headers: capabilityHeaders(),
  });
  expect(rejectedMethod.headers.allow).toBe("GET");

  const started = await directRequest("/api/attempts", {
    method: "POST",
    headers: mutationHeaders(),
    body: JSON.stringify({ mode: "drill", drill_duration_seconds: 60 }),
  });
  expect(started.status).toBe(201);
  const attemptId = started.document.data.session.attempt_id;

  const source = await directRequest(`/api/source?attempt_id=${attemptId}`, {
    headers: capabilityHeaders(),
  });
  expect(source.status).toBe(200);
  expect(source.headers.etag).toBe(source.document.data.etag);

  const badUuid = await directRequest("/api/source?attempt_id=not-a-uuid", {
    headers: capabilityHeaders(),
  });
  const malformedBody = await directRequest(`/api/test?attempt_id=${attemptId}`, {
    method: "POST",
    headers: mutationHeaders({ etag: source.headers.etag }),
    body: '{"content":',
  });
  const invalidContentType = await directRequest(
    `/api/test?attempt_id=${attemptId}`,
    {
      method: "POST",
      headers: mutationHeaders({
        contentType: "text/plain",
        etag: source.headers.etag,
      }),
      body: '{"content":"synthetic request body"}',
    },
  );
  const missingEtag = await directRequest(`/api/source?attempt_id=${attemptId}`, {
    method: "PUT",
    headers: mutationHeaders(),
    body: '{"content":"synthetic request body"}',
  });

  await expectFailures([
    [missingToken, 401, "unauthorized"],
    [wrongToken, 401, "unauthorized"],
    [rejectedOrigin, 403, "forbidden_origin"],
    [rejectedMethod, 405, "method_not_allowed"],
    [badUuid, 422, "invalid_input"],
    [malformedBody, 400, "invalid_json"],
    [invalidContentType, 400, "invalid_body"],
    [missingEtag, 422, "invalid_input"],
  ]);

  const forbiddenPaths = [
    "/api/files",
    "/api/terminal",
    "/api/upload",
    "/api/proxy",
    "/api/commands",
    "/FETCH_ONLY",
  ];
  const forbiddenResponses = await Promise.all(forbiddenPaths.map((path) =>
    directRequest(path, {
      headers: path.startsWith("/api/") ? capabilityHeaders() : {},
    }),
  ));
  await expectFailures(forbiddenResponses.map((response) =>
    [response, 404, "not_found"],
  ));
});

function capabilityHeaders({ token = harness.token } = {}) {
  return { "X-Simulator-Token": token };
}

function mutationHeaders({
  contentType = "application/json",
  etag,
  origin = harness.origin,
  token = harness.token,
} = {}) {
  return {
    "Content-Type": contentType,
    ...(etag ? { "If-Match": etag } : {}),
    Origin: origin,
    "X-Simulator-Token": token,
  };
}

async function directRequest(path, { method = "GET", headers = {}, body } = {}) {
  const response = await fetch(`${harness.origin}${path}`, { method, headers, body });
  const text = await response.text();
  return {
    document: response.headers.get("content-type")?.startsWith("application/json")
      ? JSON.parse(text)
      : undefined,
    headers: Object.fromEntries(response.headers),
    status: response.status,
  };
}

async function expectFailures(cases) {
  for (const [response, status, code] of cases) {
    expect(response.status).toBe(status);
    expect(response.document).toEqual({
      schema_version: "web/v1",
      ok: false,
      error: { code, message: expect.any(String) },
    });
    const serialized = JSON.stringify(response.document);
    expect(serialized).not.toContain(harness.token);
    expect(serialized).not.toMatch(/FETCH_ONLY|\/Users\/|Traceback/iu);
  }
}
