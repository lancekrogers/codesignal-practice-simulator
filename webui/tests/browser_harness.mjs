import { randomBytes } from "node:crypto";
import { spawn } from "node:child_process";
import { mkdtemp, readFile, rm, writeFile } from "node:fs/promises";
import { readFileSync } from "node:fs";
import { delimiter, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { tmpdir } from "node:os";
import { writeClock } from "./clock_file.mjs";
import { createContinuityControls } from "./continuity_controls.mjs";
import {
  readReadyLine,
  stopChild,
  waitForHttpReadiness,
} from "./fixture_process.mjs";

export { installOfflineRequestPolicy } from "./network_guard.mjs";

const projectRoot = resolve(fileURLToPath(new URL("../..", import.meta.url)));
const DEFAULT_CLOCK_START = "2030-01-01T00:00:00+00:00";

export async function startFixtureServer(options = {}) {
  const fixture = await prepareFixture(options);
  const runtime = { child: undefined, details: undefined, port: 0 };
  try {
    await launchFixture(runtime, fixture);
    return createFixtureHandle(fixture, runtime);
  } catch (error) {
    await cleanupFixture(runtime.child, fixture.workspace);
    throw error;
  }
}

async function prepareFixture(options) {
  const installed = Boolean(process.env.SIMULATOR_SERVER_SCRIPT);
  const script = installed
    ? resolve(projectRoot, process.env.SIMULATOR_SERVER_SCRIPT)
    : join(projectRoot, "webui", "tests", "fixture_server.py");
  const workspace = await mkdtemp(join(tmpdir(), "codesignal-browser-fixture-"));
  try {
    const clockFile = join(workspace, "test-clock.txt");
    const openerFile = join(workspace, "browser-opens.txt");
    const scoreCallsFile = join(workspace, "score-calls.txt");
    const clockStart = options.clockStart ?? DEFAULT_CLOCK_START;
    const token = options.token ?? createFixtureToken();
    await writeFile(clockFile, clockStart, "utf8");
    return {
      clockFile,
      clockStart,
      installed,
      openerFile,
      script,
      scoreCallsFile,
      token,
      workspace,
    };
  } catch (error) {
    await rm(workspace, { recursive: true, force: true });
    throw error;
  }
}

async function launchFixture(runtime, fixture) {
  runtime.child = spawn(
    process.env.SIMULATOR_PYTHON || process.env.PYTHON || "python3",
    [fixture.script],
    {
      cwd: fixture.installed ? fixture.workspace : projectRoot,
      env: fixtureEnvironment(fixture.installed, fixture.workspace, runtime.port, {
        clockFile: fixture.clockFile,
        openerFile: fixture.openerFile,
        scoreCallsFile: fixture.scoreCallsFile,
        token: fixture.token,
      }),
      stdio: ["pipe", "pipe", "pipe"],
    },
  );
  runtime.details = await readReadyLine(runtime.child);
  if (!runtime.details?.origin) {
    throw new Error("fixture server emitted incomplete startup data");
  }
  runtime.port = Number(new URL(runtime.details.origin).port);
  await waitForHttpReadiness(runtime.details.origin);
}

function createFixtureHandle(fixture, runtime) {
  const handle = {
    ...createContinuityControls(projectRoot, fixture.workspace, {
      installed: fixture.installed,
    }),
    ...fixtureControls(fixture, runtime),
  };
  Object.defineProperties(handle, fixtureMetadata(fixture, runtime));
  return handle;
}

function fixtureMetadata(fixture, runtime) {
  return {
    origin: {
      enumerable: true,
      get: () => runtime.details.origin,
    },
    token: {
      enumerable: true,
      get: () => fixture.token,
    },
    attemptId: {
      enumerable: true,
      get: () => readAttemptId(fixture.workspace),
    },
  };
}

function readAttemptId(workspace) {
  try {
    return JSON.parse(readFileSync(
      join(workspace, "attempts", "active.json"),
      "utf8",
    )).attempt_id;
  } catch (error) {
    if (error.code === "ENOENT") return undefined;
    throw error;
  }
}

function fixtureControls(fixture, runtime) {
  let closePromise;
  return {
    async setClock(value) {
      await writeClock(fixture.clockFile, value);
    },
    async browserOpenerCalls() {
      try {
        return (await readFile(fixture.openerFile, "utf8")).trim().split("\n")
          .filter(Boolean);
      } catch (error) {
        if (error.code === "ENOENT") return [];
        throw error;
      }
    },
    async scoreCalls() {
      try {
        return (await readFile(fixture.scoreCallsFile, "utf8")).trim().split("\n")
          .filter(Boolean).length;
      } catch (error) {
        if (error.code === "ENOENT") return 0;
        throw error;
      }
    },
    async attemptEvents(attemptId) {
      const path = join(fixture.workspace, "attempts", attemptId, "events.jsonl");
      const lines = (await readFile(path, "utf8")).trim().split("\n").filter(Boolean);
      return lines.map((line) => JSON.parse(line).name);
    },
    async restart() {
      await stopChild(runtime.child);
      await launchFixture(runtime, fixture);
    },
    async close() {
      closePromise ??= cleanupFixture(runtime.child, fixture.workspace);
      return closePromise;
    },
  };
}

function createFixtureToken() {
  return `browser-fixture-${randomBytes(32).toString("base64url")}`;
}

async function cleanupFixture(child, workspace) {
  try {
    if (child) await stopChild(child);
  } finally {
    await rm(workspace, { recursive: true, force: true });
  }
}

function fixtureEnvironment(installed, workspace, port, options) {
  const environment = {
    ...process.env,
    SIMULATOR_WORKSPACE: workspace,
    SIMULATOR_SERVER_PORT: String(port || 0),
    SIMULATOR_FIXTURE_TOKEN: options.token,
    SIMULATOR_BROWSER_OPENER_FILE: options.openerFile,
  };
  if (installed) {
    delete environment.PYTHONHOME;
    delete environment.PYTHONPATH;
    if (process.env.SIMULATOR_RUNTIME_PATH) {
      environment.PATH = process.env.SIMULATOR_RUNTIME_PATH;
    }
  } else {
    environment.PYTHONPATH = [
      join(projectRoot, "src"),
      process.env.PYTHONPATH,
    ].filter(Boolean).join(delimiter);
  }
  environment.SIMULATOR_CLOCK_FILE = options.clockFile;
  environment.SIMULATOR_SCORE_CALLS_FILE = options.scoreCallsFile;
  return environment;
}
