import { sanitizeArtifactDescriptorSync } from "./failure_artifacts.mjs";

const descriptor = Number(process.argv[2]);
const sensitiveValues = JSON.parse(
  process.env.FAILURE_ARTIFACT_SENSITIVE_VALUES || "[]",
);
const kind = process.env.FAILURE_ARTIFACT_KIND || "redact";

try {
  sanitizeArtifactDescriptorSync(descriptor, kind, sensitiveValues);
} catch {
  process.exitCode = 1;
}
