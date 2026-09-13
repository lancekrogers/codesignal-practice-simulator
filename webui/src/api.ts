export type ApiDocument = {
  ok: boolean;
  data?: Record<string, any>;
  error?: { code?: string; message?: string };
};

export type ApiAction =
  | "bootstrap"
  | "start"
  | "reconnect"
  | "testing"
  | "submitting"
  | "ending"
  | "restarting"
  | "history"
  | "review";

export type SafeApiFailure = {
  kind:
    | "conflict"
    | "unavailable"
    | "read_only"
    | "reconnect"
    | "stale"
    | "pending"
    | "internal";
  message: string;
  recovery: "reload" | "reconnect" | "refresh" | "retry" | "none";
};

export class ApiError extends Error {
  readonly code: string;
  readonly status: number;

  constructor(code: string, message: string, status = 0) {
    super(message);
    this.name = "ApiError";
    this.code = code;
    this.status = status;
  }
}

export type StaticAsset = {
  media_type: string;
  cache_control: string;
  sha256?: string;
  size?: number;
};

export type StaticManifest = Record<string, StaticAsset>;

const TOKEN_KEY = "simulator-token";
let memoryToken: string | null = null;

export function captureCapability(): void {
  const token = new URLSearchParams(window.location.hash.slice(1)).get("token");
  if (!token) return;
  memoryToken = token;
  try {
    window.sessionStorage.setItem(TOKEN_KEY, token);
  } catch {
    // The memory token keeps this tab usable when storage is unavailable.
  }
  window.history.replaceState(
    null,
    "",
    window.location.pathname + window.location.search,
  );
}

export async function loadManifest(): Promise<StaticManifest> {
  const response = await fetch("/manifest.json", { cache: "no-store" });
  if (!response.ok) throw new Error("packaged asset manifest is unavailable");
  const value = (await response.json()) as unknown;
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    throw new Error("packaged asset manifest is invalid");
  }
  return value as StaticManifest;
}

export async function apiGet(path: string, signal?: AbortSignal): Promise<ApiDocument> {
  return apiRequest("GET", path, undefined, undefined, signal);
}

export async function apiPost(
  path: string,
  body: Record<string, unknown>,
  ifMatch?: string,
  signal?: AbortSignal,
): Promise<ApiDocument> {
  return apiRequest("POST", path, body, ifMatch, signal);
}

export async function apiPut(
  path: string,
  body: Record<string, unknown>,
  ifMatch: string,
  signal?: AbortSignal,
): Promise<ApiDocument> {
  return apiRequest("PUT", path, body, ifMatch, signal);
}

export function testAttempt(
  attemptId: string,
  content: string,
  etag: string,
  signal?: AbortSignal,
): Promise<ApiDocument> {
  return apiPost(
    `/api/test?attempt_id=${encodeURIComponent(attemptId)}`,
    { content },
    etag,
    signal,
  );
}

export function submitAttempt(
  attemptId: string,
  content: string,
  etag: string,
  signal?: AbortSignal,
): Promise<ApiDocument> {
  return apiPost(
    `/api/submit?attempt_id=${encodeURIComponent(attemptId)}`,
    { content },
    etag,
    signal,
  );
}

/** End an active attempt without scoring (D001 abandon). */
export function abandonAttempt(
  attemptId: string,
  expectedRevision: number,
  signal?: AbortSignal,
): Promise<ApiDocument> {
  return apiPost(
    `/api/attempts/${encodeURIComponent(attemptId)}/abandon`,
    { expected_revision: expectedRevision },
    undefined,
    signal,
  );
}

/**
 * Run the restart transaction. The operation ID must be minted once per user
 * decision and reused on every retry so the server replays instead of creating
 * a second replacement (D001).
 */
export function restartAttempt(
  attemptId: string,
  operationId: string,
  expectedRevision: number,
  signal?: AbortSignal,
): Promise<ApiDocument> {
  return apiPost(
    `/api/attempts/${encodeURIComponent(attemptId)}/restart`,
    { operation_id: operationId, expected_revision: expectedRevision },
    undefined,
    signal,
  );
}

async function apiRequest(
  method: "GET" | "POST" | "PUT",
  path: string,
  body?: Record<string, unknown>,
  ifMatch?: string,
  signal?: AbortSignal,
): Promise<ApiDocument> {
  let response: Response;
  try {
    response = await fetch(path, {
      method,
      headers: {
        "X-Simulator-Token": capability(),
        ...(ifMatch ? { "If-Match": ifMatch } : {}),
        ...(body ? { "Content-Type": "application/json" } : {}),
      },
      ...(body ? { body: JSON.stringify(body) } : {}),
      signal,
      cache: "no-store",
    });
  } catch (error) {
    if (signal?.aborted) throw error;
    throw new ApiError("reconnect", "the local simulator could not be reached");
  }
  let document: ApiDocument;
  try {
    document = (await response.json()) as ApiDocument;
  } catch {
    throw new ApiError("invalid_response", "the local simulator returned invalid data");
  }
  if (!response.ok || !document.ok) {
    throw new ApiError(
      document.error?.code || "request_failed",
      document.error?.message || "the local simulator rejected the request",
      response.status,
    );
  }
  return document;
}

export function describeApiError(
  error: unknown,
  action: ApiAction,
): SafeApiFailure {
  if (!(error instanceof ApiError)) {
    return {
      kind: "internal",
      message: action === "bootstrap"
        ? "The assessment entry data is invalid. Reload the local simulator and try again."
        : genericMessage(action),
      recovery: action === "start" ? "reload" : "reconnect",
    };
  }
  if (action === "ending" || action === "restarting") {
    return describeLifecycleError(error, action);
  }
  if (action === "history") return describeHistoryError(error);
  if (action === "review") return describeReviewError(error);
  switch (error.code) {
    case "session_unavailable":
      return {
        kind: "unavailable",
        message: "The local assessment fixture or selected session is unavailable. Reconnect after preparing the local simulator.",
        recovery: "reconnect",
      };
    case "lifecycle_locked":
      return {
        kind: action === "start" ? "conflict" : "read_only",
        message: action === "start"
          ? "An active session is already selected. Reconnect before starting another."
          : "This session is no longer accepting changes. The visible source remains available for review.",
        recovery: action === "start" ? "reconnect" : "none",
      };
    case "reconnect":
      if (action === "testing" || action === "submitting") {
        return {
          kind: "internal",
          message: genericMessage(action),
          recovery: "reconnect",
        };
      }
      return {
        kind: "reconnect",
        message: "The local simulator could not be reached. Check that it is running, then reconnect.",
        recovery: "reconnect",
      };
    default:
      return {
        kind: "internal",
        message: genericMessage(action),
        recovery: action === "start" || action === "bootstrap"
          ? "reload"
          : "reconnect",
      };
  }
}

function describeReviewError(error: ApiError): SafeApiFailure {
  switch (error.code) {
    case "session_unavailable":
      return {
        kind: "unavailable",
        message: "No attempt with this address is stored locally. It may have been removed, or the address may be mistyped.",
        recovery: "none",
      };
    case "review_pending":
      return {
        kind: "pending",
        message: "This attempt is still being finalized. Retry loading in a moment; nothing is changed by waiting.",
        recovery: "retry",
      };
    case "invalid_input":
      return {
        kind: "stale",
        message: "This review address is not valid.",
        recovery: "none",
      };
    case "reconnect":
      return {
        kind: "reconnect",
        message: "The local simulator could not be reached. Check that it is running, then retry loading.",
        recovery: "retry",
      };
    default:
      return {
        kind: "internal",
        message: "The stored review could not be read safely. It may be incomplete or altered; nothing was changed. Retry loading, or return to history.",
        recovery: "retry",
      };
  }
}

function describeHistoryError(error: ApiError): SafeApiFailure {
  switch (error.code) {
    case "invalid_input":
    case "invalid_query":
      return {
        kind: "stale",
        message: "The page position or filters in this address are not valid. Show the newest attempts to continue.",
        recovery: "refresh",
      };
    case "history_unavailable":
      return {
        kind: "unavailable",
        message: "Attempt history is unavailable: the local attempts folder could not be read safely. Check the workspace, then retry.",
        recovery: "retry",
      };
    case "reconnect":
      return {
        kind: "reconnect",
        message: "The local simulator could not be reached. Check that it is running, then retry.",
        recovery: "retry",
      };
    default:
      return {
        kind: "internal",
        message: "Attempt history could not be loaded safely. Retry, or show the newest attempts.",
        recovery: "retry",
      };
  }
}

function describeLifecycleError(
  error: ApiError,
  action: "ending" | "restarting",
): SafeApiFailure {
  const verb = action === "ending" ? "End attempt" : "Restart";
  switch (error.code) {
    case "stale_revision":
      return {
        kind: "stale",
        message: `${verb} did not apply: this attempt changed elsewhere. The view has been refreshed; review it and choose again.`,
        recovery: "refresh",
      };
    case "operation_conflict":
      return {
        kind: "conflict",
        message: "A restart for this attempt is already in progress. Wait a moment, then choose Restart again to continue it.",
        recovery: "retry",
      };
    case "recovery_pending":
      return {
        kind: "pending",
        message: "The restart is recorded but not finished. Choose Restart again to complete it; no second attempt will be created.",
        recovery: "retry",
      };
    case "lifecycle_locked":
      return {
        kind: "read_only",
        message: `${verb} is not available: this attempt is no longer active. The view has been refreshed.`,
        recovery: "refresh",
      };
    case "reconnect":
      return {
        kind: "reconnect",
        message: `${verb} could not reach the local simulator. Check that it is running, then choose ${verb} again.`,
        recovery: "retry",
      };
    default:
      return {
        kind: "internal",
        message: genericMessage(action),
        recovery: "retry",
      };
  }
}

function genericMessage(action: ApiAction): string {
  if (action === "bootstrap") {
    return "The assessment entry data could not be loaded safely. Reload the local simulator.";
  }
  if (action === "start") {
    return "Start could not be confirmed safely. Reload to reconnect; do not press Start again.";
  }
  if (action === "reconnect") {
    return "The selected session could not be restored safely. Reconnect to the local simulator.";
  }
  if (action === "testing") {
    return "The local practice check could not complete safely. Try again.";
  }
  if (action === "submitting") {
    return "The submission could not complete safely. Try again.";
  }
  if (action === "ending") {
    return "End attempt could not complete safely. The attempt is unchanged; try again.";
  }
  if (action === "restarting") {
    return "Restart could not complete safely. Choose Restart again; the same operation is retried.";
  }
  if (action === "history") {
    return "Attempt history could not be loaded safely. Retry, or show the newest attempts.";
  }
  if (action === "review") {
    return "The stored review could not be read safely. It may be incomplete or altered; nothing was changed. Retry loading, or return to history.";
  }
  return "The local simulator could not complete this entry action safely. Reconnect and try again.";
}

function capability(): string {
  if (memoryToken) return memoryToken;
  try {
    return window.sessionStorage.getItem(TOKEN_KEY) || "";
  } catch {
    return "";
  }
}
