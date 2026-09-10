import {
  chmod,
  mkdir,
  mkdtemp,
  readFile,
  realpath,
  rm,
  writeFile,
} from "node:fs/promises";
import { join, resolve } from "node:path";
import { tmpdir } from "node:os";
import { fileURLToPath } from "node:url";
import { expect, test } from "@playwright/test";
import { createContinuityControls } from "./continuity_controls.mjs";

const PROJECT_ROOT = resolve(fileURLToPath(new URL("../..", import.meta.url)));
const ENVIRONMENT_NAMES = [
  "CONTINUITY_RECORD",
  "PYTHONHOME",
  "PYTHONPATH",
  "SIMULATOR_CLI",
  "SIMULATOR_RUNTIME_PATH",
];

test("installed continuity subprocess uses isolated cwd and environment", async () => {
  const root = await mkdtemp(join(tmpdir(), "installed-continuity-"));
  const workspace = join(root, "workspace");
  const record = join(root, "record.txt");
  const command = join(root, "installed-codesignal-sim");
  const saved = new Map(ENVIRONMENT_NAMES.map((name) => [
    name,
    process.env[name],
  ]));
  try {
    await mkdir(workspace);
    await writeFile(command, `#!/bin/sh
printf '%s\\n%s\\n%s\\n%s\\n' "$PWD" "\${PYTHONPATH+x}" \
  "\${PYTHONHOME+x}" "$PATH" > "$CONTINUITY_RECORD"
printf '%s\\n' \
  '{"ok":true,"result":{"format":"json","context":{"installed":true}}}'
`, "utf8");
    await chmod(command, 0o700);
    process.env.CONTINUITY_RECORD = record;
    process.env.PYTHONHOME = join(PROJECT_ROOT, "inherited-python-home");
    process.env.PYTHONPATH = join(PROJECT_ROOT, "src");
    process.env.SIMULATOR_CLI = command;
    process.env.SIMULATOR_RUNTIME_PATH = root;

    const controls = createContinuityControls(
      PROJECT_ROOT,
      workspace,
      { installed: true },
    );
    await expect(controls.cliContext(
      "00000000-0000-4000-8000-000000000000",
    )).resolves.toEqual({ installed: true });
    const [cwd, pythonPathSet, pythonHomeSet, path] =
      (await readFile(record, "utf8")).trimEnd().split("\n");
    expect(cwd).toBe(await realpath(workspace));
    expect(pythonPathSet).toBe("");
    expect(pythonHomeSet).toBe("");
    expect(path).toBe(root);
  } finally {
    for (const [name, value] of saved) {
      if (value === undefined) delete process.env[name];
      else process.env[name] = value;
    }
    await rm(root, { recursive: true, force: true });
  }
});
