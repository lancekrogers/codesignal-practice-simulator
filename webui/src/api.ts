export type ApiDocument = {
  ok: boolean;
  data?: Record<string, any>;
  error?: { code?: string; message?: string };
};

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

export async function apiGet(path: string): Promise<ApiDocument> {
  const response = await fetch(path, {
    headers: { "X-Simulator-Token": capability() },
    cache: "no-store",
  });
  const document = (await response.json()) as ApiDocument;
  if (!response.ok || !document.ok) {
    throw new Error(document.error?.message || "local simulator request failed");
  }
  return document;
}

function capability(): string {
  if (memoryToken) return memoryToken;
  try {
    return window.sessionStorage.getItem(TOKEN_KEY) || "";
  } catch {
    return "";
  }
}
