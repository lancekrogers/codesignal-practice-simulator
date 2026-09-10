import { expect, test } from "@playwright/test";
import { mkdtemp, readFile, rm, writeFile } from "node:fs/promises";
import { join } from "node:path";
import { tmpdir } from "node:os";
import { writeClock } from "./clock_file.mjs";

test("clock collision cleanup never removes another writer's temp file", async () => {
  const directory = await mkdtemp(join(tmpdir(), "clock-file-test-"));
  const path = join(directory, "clock.txt");
  const collision = `${path}.collision.tmp`;
  try {
    await writeFile(collision, "owned by another writer", "utf8");
    let calls = 0;
    await writeClock(path, "2030-01-01T00:00:00+00:00", {
      randomUUID: () => calls++ === 0 ? "collision" : "unique",
    });
    await expect(readFile(path, "utf8")).resolves.toBe(
      "2030-01-01T00:00:00+00:00",
    );
    await expect(readFile(collision, "utf8")).resolves.toBe(
      "owned by another writer",
    );
  } finally {
    await rm(directory, { recursive: true, force: true });
  }
});

test("rename failure removes the owned temp and preserves the original error", async () => {
  const directory = await mkdtemp(join(tmpdir(), "clock-file-test-"));
  const path = join(directory, "clock.txt");
  const original = Object.assign(new Error("rename failed"), { code: "EIO" });
  let removed = 0;
  try {
    await expect(writeClock(path, "2030-01-01T00:00:00+00:00", {
      randomUUID: () => "owned",
      rename: async () => {
        throw original;
      },
      rm: async (...arguments_) => {
        removed += 1;
        return rm(...arguments_);
      },
    })).rejects.toBe(original);
    expect(removed).toBe(1);
    await expect(readFile(`${path}.owned.tmp`, "utf8")).rejects.toMatchObject({
      code: "ENOENT",
    });
  } finally {
    await rm(directory, { recursive: true, force: true });
  }
});
