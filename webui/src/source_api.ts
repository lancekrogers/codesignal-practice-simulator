import { apiGet, apiPost, apiPut, ApiError } from "./api";

export type SourceDocument = {
  content: string;
  etag: string;
};

export type HistorySnapshot = {
  snapshot_id: string;
  created_at: string;
  operation: "save" | "restore" | "reset";
  prior_hash: string;
  new_hash: string;
  content_preview: string;
};

export type SourceHistory = {
  current: SourceDocument;
  snapshots: HistorySnapshot[];
};

export class SourceConflictError extends Error {
  readonly server: SourceDocument;

  constructor(server: SourceDocument) {
    super("candidate source changed; choose which version to keep");
    this.name = "SourceConflictError";
    this.server = server;
  }
}

export async function loadSource(
  attemptId: string,
  signal?: AbortSignal,
): Promise<SourceDocument> {
  return normalizeSource(
    (await apiGet(sourcePath(attemptId), signal)).data,
  );
}

export async function saveSource(
  attemptId: string,
  content: string,
  etag: string,
  signal?: AbortSignal,
): Promise<SourceDocument> {
  try {
    const response = await apiPut(sourcePath(attemptId), { content }, etag, signal);
    return normalizeSource(response.data?.source);
  } catch (error) {
    if (!(error instanceof ApiError) || error.status !== 409) throw error;
    throw new SourceConflictError(await loadSource(attemptId, signal));
  }
}

export async function loadSourceHistory(
  attemptId: string,
  signal?: AbortSignal,
): Promise<SourceHistory> {
  return normalizeHistory(
    (
      await apiGet(
        `/api/source/history?attempt_id=${encodeURIComponent(attemptId)}`,
        signal,
      )
    ).data,
  );
}

export async function restoreSource(
  attemptId: string,
  snapshotId: string,
  etag: string,
  signal?: AbortSignal,
): Promise<SourceDocument> {
  return sourceAction(
    attemptId,
    `/api/source/restore?attempt_id=${encodeURIComponent(attemptId)}`,
    { snapshot_id: snapshotId },
    etag,
    signal,
  );
}

export async function resetSource(
  attemptId: string,
  etag: string,
  signal?: AbortSignal,
): Promise<SourceDocument> {
  return sourceAction(
    attemptId,
    `/api/source/reset?attempt_id=${encodeURIComponent(attemptId)}`,
    {},
    etag,
    signal,
  );
}

function sourceAction(
  attemptId: string,
  path: string,
  body: Record<string, unknown>,
  etag: string,
  signal?: AbortSignal,
): Promise<SourceDocument> {
  return apiPost(path, body, etag, signal)
    .then((response) => normalizeSource(response.data?.source))
    .catch(async (error: unknown) => {
      if (!(error instanceof ApiError) || error.status !== 409) throw error;
      throw new SourceConflictError(await loadSource(attemptId, signal));
    });
}

function sourcePath(attemptId: string): string {
  return `/api/source?attempt_id=${encodeURIComponent(attemptId)}`;
}

export function normalizeSource(value: unknown): SourceDocument {
  const data = record(value, "source");
  if (
    typeof data.content !== "string" ||
    data.content.length > 2 * 1024 * 1024 ||
    typeof data.etag !== "string" ||
    !/^sha256:[0-9a-f]{64}$/u.test(data.etag)
  ) {
    throw new Error("source response is invalid");
  }
  return { content: data.content, etag: data.etag };
}

function normalizeHistory(value: unknown): SourceHistory {
  const data = record(value, "history");
  const current = normalizeSource(data.current);
  if (!Array.isArray(data.snapshots) || data.snapshots.length > 50) {
    throw new Error("history response is invalid");
  }
  const snapshots = data.snapshots.map((value) => {
    const item = record(value, "history snapshot");
    if (
      typeof item.snapshot_id !== "string" ||
      typeof item.created_at !== "string" ||
      !["save", "restore", "reset"].includes(String(item.operation)) ||
      typeof item.prior_hash !== "string" ||
      typeof item.new_hash !== "string" ||
      typeof item.content_preview !== "string" ||
      item.content_preview.length > 1024
    ) {
      throw new Error("history response is invalid");
    }
    return {
      snapshot_id: item.snapshot_id,
      created_at: item.created_at,
      operation: item.operation as HistorySnapshot["operation"],
      prior_hash: item.prior_hash,
      new_hash: item.new_hash,
      content_preview: item.content_preview,
    };
  });
  return { current, snapshots };
}

function record(value: unknown, label: string): Record<string, any> {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    throw new Error(`${label} is invalid`);
  }
  return value as Record<string, any>;
}
