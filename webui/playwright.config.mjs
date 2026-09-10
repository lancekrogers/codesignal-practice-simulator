import { defineConfig } from "@playwright/test";
import { fileURLToPath } from "node:url";

export const LOCKED_CHROMIUM = {
  browserName: "chromium",
  revision: "1243",
  version: "153.0.8010.12",
};
export const FAILURE_ARTIFACT_REPORTER = fileURLToPath(new URL(
  "./tests/failure_artifacts_reporter.mjs",
  import.meta.url,
));
export const PRIVACY_SAFE_REPORTER = fileURLToPath(new URL(
  "./tests/privacy_safe_reporter.mjs",
  import.meta.url,
));

export default defineConfig({
  testDir: "./tests",
  testIgnore: ["**/harness_failure_probe.spec.mjs"],
  outputDir: ".test-results",
  preserveOutput: "failures-only",
  reporter: [
    [FAILURE_ARTIFACT_REPORTER],
    [PRIVACY_SAFE_REPORTER],
    [fileURLToPath(new URL("./tests/success_cleanliness_reporter.mjs", import.meta.url))],
  ],
  workers: 1,
  projects: [{
    name: LOCKED_CHROMIUM.browserName,
    use: { browserName: LOCKED_CHROMIUM.browserName },
  }],
  use: {
    screenshot: "off",
    trace: "retain-on-failure",
    video: "off",
  },
});
