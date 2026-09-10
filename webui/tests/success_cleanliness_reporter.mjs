import { readdir } from "node:fs/promises";
import { join, relative } from "node:path";

export default class SuccessCleanlinessReporter {
  async onEnd(result) {
    this.successful = result.status === "passed";
  }

  async onExit() {
    if (!this.successful) return;
    try {
      for (const outputDir of this.outputDirs ?? []) {
        const residue = (await collectFiles(outputDir)).filter((path) =>
          relative(outputDir, path) !== ".last-run.json");
        if (residue.length) {
          throw new Error("successful browser run left unexpected output residue.");
        }
      }
    } catch (error) {
      if (error.message === "successful browser run left unexpected output residue.") {
        throw error;
      }
      throw new Error("successful browser run cleanliness check failed.");
    }
  }

  onBegin(config) {
    const outputDirs = [
      ...(config.projects ?? []).map((project) => project.outputDir),
      config.outputDir,
    ];
    this.outputDirs = [...new Set(outputDirs.filter(Boolean))];
  }
}

async function collectFiles(root) {
  let entries;
  try {
    entries = await readdir(root, { withFileTypes: true });
  } catch (error) {
    if (error.code === "ENOENT") return [];
    throw error;
  }

  const files = [];
  for (const entry of entries) {
    const path = join(root, entry.name);
    if (entry.isDirectory()) {
      files.push(...await collectFiles(path));
    } else {
      files.push(path);
    }
  }
  return files.sort();
}
