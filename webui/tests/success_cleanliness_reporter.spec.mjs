import { expect, test } from "@playwright/test";
import { mkdir, mkdtemp, rm, writeFile } from "node:fs/promises";
import { join } from "node:path";
import { tmpdir } from "node:os";
import SuccessCleanlinessReporter from "./success_cleanliness_reporter.mjs";

test("checks each Playwright project output directory without exposing residue details", async () => {
  const root = await mkdtemp(join(tmpdir(), "success-cleanliness-"));
  const firstOutputDir = join(root, "first");
  const secondOutputDir = join(root, "second");
  const residueName = "candidate-private-output.txt";
  try {
    await mkdir(firstOutputDir);
    await mkdir(secondOutputDir);
    const reporter = new SuccessCleanlinessReporter();
    reporter.onBegin({
      projects: [
        { outputDir: firstOutputDir },
        { outputDir: secondOutputDir },
        { outputDir: firstOutputDir },
      ],
    });
    await writeFile(join(secondOutputDir, residueName), "candidate content");
    await reporter.onEnd({ status: "passed" });

    let failure;
    try {
      await reporter.onExit();
    } catch (error) {
      failure = error;
    }
    expect(failure).toBeInstanceOf(Error);
    expect(failure.message).toBe("successful browser run left unexpected output residue.");
    expect(failure.message).not.toContain(root);
    expect(failure.message).not.toContain(residueName);
    expect(failure.message).not.toContain("candidate content");

    await rm(join(secondOutputDir, residueName));
    const cleanReporter = new SuccessCleanlinessReporter();
    cleanReporter.onBegin({
      projects: [
        { outputDir: firstOutputDir },
        { outputDir: secondOutputDir },
      ],
    });
    await cleanReporter.onEnd({ status: "passed" });
    await expect(cleanReporter.onExit()).resolves.toBeUndefined();

    const invalidRoot = join(root, "private-output-path");
    await writeFile(invalidRoot, "synthetic content");
    const unreadableReporter = new SuccessCleanlinessReporter();
    unreadableReporter.onBegin({ projects: [{ outputDir: invalidRoot }] });
    await unreadableReporter.onEnd({ status: "passed" });
    await expect(unreadableReporter.onExit()).rejects.toThrow(
      "successful browser run cleanliness check failed.",
    );
  } finally {
    await rm(root, { recursive: true, force: true });
  }
});
