export type SourceSaveStatus = "clean" | "dirty" | "saving" | "conflict" | "failed";

export type SourceState = {
  status: SourceSaveStatus;
  authoritativeContent: string;
  authoritativeEtag: string;
  buffer: string;
  serverContent?: string;
  serverEtag?: string;
};

export function createSourceState(content: string, etag: string): SourceState {
  return {
    status: "clean",
    authoritativeContent: content,
    authoritativeEtag: etag,
    buffer: content,
  };
}
