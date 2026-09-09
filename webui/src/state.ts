import type { StaticManifest } from "./api";

export type Bootstrap = {
  assessment?: { display_name?: string };
  levels?: Array<{ level: number; label: string }>;
  session?: {
    attempt_id: string;
    status: string;
  } | null;
};

export type BrowserState = {
  bootstrap: Bootstrap | null;
  source: string;
  manifest: StaticManifest;
};

export function initialState(
  manifest: StaticManifest,
  bootstrap: Bootstrap | null,
  source = "",
): BrowserState {
  return { bootstrap, source, manifest };
}

export function workerUrls(manifest: StaticManifest): {
  editor: string;
  language: string;
} {
  const editor = findAsset(manifest, "editor.worker-");
  const language = findAsset(manifest, "language.worker-");
  return { editor: `/${editor}`, language: `/${language}` };
}

function findAsset(manifest: StaticManifest, prefix: string): string {
  const name = Object.keys(manifest).find(
    (candidate) => candidate.startsWith(prefix) && candidate.endsWith(".js"),
  );
  if (!name) throw new Error(`required packaged worker is missing: ${prefix}`);
  return name;
}
