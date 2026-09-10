import { expect, test } from "@playwright/test";
import { readdir } from "node:fs/promises";
import { tmpdir } from "node:os";
import { startFixtureServer } from "./browser_harness.mjs";

const WORKSPACE_PREFIX = "codesignal-browser-fixture-";

test("removes the fixture workspace when clock setup rejects", async () => {
  const before = await fixtureWorkspaces();

  await expect(startFixtureServer({ clockStart: {} })).rejects.toThrow(TypeError);

  expect(await fixtureWorkspaces()).toEqual(before);
});

async function fixtureWorkspaces() {
  return (await readdir(tmpdir()))
    .filter((name) => name.startsWith(WORKSPACE_PREFIX))
    .sort();
}
