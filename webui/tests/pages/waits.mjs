import { expect } from "@playwright/test";

export function apiRequest(path, method = "GET") {
  return (request) =>
    request.method() === method &&
    new URL(request.url()).pathname + search(request.url()) === path;
}

export function waitForApiRequest(page, path, method = "GET") {
  return page.waitForRequest(apiRequest(path, method));
}

export function waitForApiResponse(page, path, method = "GET") {
  return page.waitForResponse((response) =>
    apiRequest(path, method)(response.request()) &&
    response.url() === response.request().url()
  );
}

export async function waitForAuthoritativeState(
  page,
  attemptId,
  expectedStatus,
  options = {},
) {
  await expect.poll(
    () => readAuthoritativeStatus(page, attemptId),
    {
      message: `authoritative session did not reach ${expectedStatus}`,
      timeout: options.timeout ?? 5000,
      intervals: [100, 250, 500],
    },
  ).toBe(expectedStatus);
}

async function readAuthoritativeStatus(page, attemptId) {
  return page.evaluate(async (id) => {
    const token = sessionStorage.getItem("simulator-token") || "";
    const response = await fetch(
      `/api/time?attempt_id=${encodeURIComponent(id)}`,
      {
        headers: { "X-Simulator-Token": token },
        cache: "no-store",
      },
    );
    if (!response.ok) return `http-${response.status}`;
    const document = await response.json();
    return document?.data?.session?.status || "invalid";
  }, attemptId);
}

function search(value) {
  return new URL(value).search;
}
