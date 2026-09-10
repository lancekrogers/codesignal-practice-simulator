import { spawn } from "node:child_process";
import { readFile, writeFile } from "node:fs/promises";
import { delimiter, join } from "node:path";

const ATTEMPT_ID_PATTERN =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/iu;

export function createContinuityControls(projectRoot, workspace, {
  installed = false,
} = {}) {
  return {
    workspaceRoot: workspace,
    async cliContext(attemptId) {
      const args = [
        "context",
        "--workspace-root",
        workspace,
        "--format",
        "json",
        "--json",
        "--attempt",
        attemptId,
      ];
      const output = await runPublicCli(projectRoot, workspace, installed, args);
      const document = JSON.parse(output);
      if (!document.ok || document.result?.format !== "json") {
        throw new Error(`public CLI returned an invalid context: ${output}`);
      }
      return document.result.context;
    },
    async readStatus(attemptId) {
      return readFile(attemptFile(workspace, attemptId, "STATUS.md"), "utf8");
    },
    async readGuidance(attemptId) {
      const root = attemptDirectory(workspace, attemptId);
      return {
        agents: await readFile(join(root, "AGENTS.md"), "utf8"),
        coaching: await readFile(join(root, "COACHING.md"), "utf8"),
      };
    },
    async writeCoaching(attemptId, content) {
      await writeFile(
        attemptFile(workspace, attemptId, "COACHING.md"),
        content,
        "utf8",
      );
    },
    async readCoaching(attemptId) {
      return readFile(attemptFile(workspace, attemptId, "COACHING.md"), "utf8");
    },
  };
}

function attemptDirectory(workspace, attemptId) {
  if (!ATTEMPT_ID_PATTERN.test(attemptId)) {
    throw new Error(`invalid attempt ID for test control: ${attemptId}`);
  }
  return join(workspace, "attempts", attemptId);
}

function attemptFile(workspace, attemptId, filename) {
  return join(attemptDirectory(workspace, attemptId), filename);
}

function runPublicCli(projectRoot, workspace, installed, args) {
  const configured = process.env.SIMULATOR_CLI;
  const command = configured || process.env.SIMULATOR_PYTHON || "python3";
  const commandArgs = configured
    ? args
    : ["-m", "codesignal_practice_simulator", ...args];
  const environment = {
    ...process.env,
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
  return new Promise((resolve, reject) => {
    const child = spawn(command, commandArgs, {
      cwd: installed ? workspace : projectRoot,
      env: environment,
      stdio: ["ignore", "pipe", "pipe"],
    });
    let stdout = "";
    let stderr = "";
    child.stdout.on("data", (chunk) => {
      stdout += chunk.toString();
    });
    child.stderr.on("data", (chunk) => {
      stderr += chunk.toString();
    });
    child.once("error", reject);
    child.once("close", (code, signal) => {
      if (code !== 0) {
        reject(new Error(
          `public CLI exited with ${code ?? `signal ${signal}`}: ${stderr}`,
        ));
        return;
      }
      resolve(stdout.trim());
    });
  });
}
