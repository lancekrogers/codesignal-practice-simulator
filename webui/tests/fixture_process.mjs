import { Buffer } from "node:buffer";
import { StringDecoder } from "node:string_decoder";

const MAX_DIAGNOSTIC_BYTES = 4096;
const MAX_STARTUP_BYTES = 64 * 1024;
const MAX_DIAGNOSTIC_LINE_BYTES = 16 * 1024;
const diagnosticStates = new WeakMap();

export async function waitForHttpReadiness(origin) {
  const deadline = Date.now() + 10000;
  let lastError;
  while (Date.now() < deadline) {
    try {
      const response = await fetch(origin);
      if (response.ok) return;
      lastError = new Error(`readiness returned HTTP ${response.status}`);
    } catch (error) {
      lastError = error;
    }
    await new Promise((resolvePromise) => setImmediate(resolvePromise));
  }
  throw new Error(`fixture server was not HTTP-ready: ${lastError?.message}`);
}

export function readReadyLine(child) {
  const diagnostics = captureDiagnostics(child);
  return new Promise((resolvePromise, reject) => {
    let output = "";
    let settled = false;
    const timeout = setTimeout(() => fail(new Error(
      `fixture server did not start: ${diagnosticText(diagnostics)}`,
    )), 10000);
    const cleanup = () => {
      clearTimeout(timeout);
      child.stdout.off("data", onStdout);
      child.stdout.off("end", onEnd);
      child.off("error", onError);
      child.off("exit", onExit);
    };
    const fail = (error) => {
      if (settled) return;
      settled = true;
      cleanup();
      reject(error);
    };
    const onStdout = (chunk) => {
      output += chunk.toString();
      if (output.length > MAX_STARTUP_BYTES) {
        fail(new Error(
          `fixture server emitted too much startup data: ${diagnosticText(diagnostics)}`,
        ));
        return;
      }
      const newline = output.indexOf("\n");
      if (newline < 0 || settled) return;
      settled = true;
      cleanup();
      try {
        resolvePromise(JSON.parse(output.slice(0, newline)));
      } catch (error) {
        reject(new Error(
          `fixture server emitted invalid startup data: ${redactError(error)}`,
        ));
      }
    };
    const onEnd = () => fail(new Error(
      `fixture server closed stdout: ${diagnosticText(diagnostics)}`,
    ));
    const onError = (error) => fail(new Error(
      `fixture server could not start: ${redactError(error)}; ` +
      `stderr: ${diagnosticText(diagnostics)}`,
    ));
    const onExit = (code, signal) => fail(new Error(
      `fixture server exited before startup (${code ?? `signal ${signal}`}): ` +
      diagnosticText(diagnostics),
    ));
    child.stdout.on("data", onStdout);
    child.stdout.once("end", onEnd);
    child.once("error", onError);
    child.once("exit", onExit);
  });
}

export function diagnosticTail(child) {
  return diagnosticText(diagnosticStates.get(child));
}

export async function stopChild(child) {
  const exited = waitForChildClose(child);
  if (child.exitCode === null && child.signalCode === null) {
    if (!child.stdin.destroyed) child.stdin.end();
    if (await waitForChildCloseWithin(exited, 5000)) return;
    child.kill("SIGTERM");
    if (!(await waitForChildCloseWithin(exited, 1000))) child.kill("SIGKILL");
  }
  await exited;
}

function captureDiagnostics(child) {
  const existing = diagnosticStates.get(child);
  if (existing) return existing;

  const state = {
    decoder: new StringDecoder("utf8"),
    discardingOversizedLine: false,
    pending: "",
    tail: Buffer.alloc(0),
  };
  const onStderr = (chunk) => {
    state.pending += state.decoder.write(chunk);
    flushDiagnosticPrefix(state, false);
  };
  const onError = () => {};
  const onClose = () => {
    state.pending += state.decoder.end();
    flushDiagnosticPrefix(state, true);
    child.stderr.off("data", onStderr);
    child.off("error", onError);
    child.off("close", onClose);
  };
  state.onStderr = onStderr;
  child.stderr.on("data", onStderr);
  child.on("error", onError);
  child.once("close", onClose);
  diagnosticStates.set(child, state);
  return state;
}

function flushDiagnosticPrefix(state, final) {
  while (true) {
    const newline = state.pending.indexOf("\n");
    if (newline >= 0) {
      const line = state.pending.slice(0, newline).replace(/\r$/u, "");
      state.pending = state.pending.slice(newline + 1);
      if (state.discardingOversizedLine) {
        state.discardingOversizedLine = false;
      } else if (Buffer.byteLength(line, "utf8") > MAX_DIAGNOSTIC_LINE_BYTES) {
        appendDiagnostic(state, "[REDACTED]\n");
      } else {
        appendDiagnostic(state, `${redactDiagnostic(line)}\n`);
      }
      continue;
    }
    if (Buffer.byteLength(state.pending, "utf8") > MAX_DIAGNOSTIC_LINE_BYTES) {
      if (!state.discardingOversizedLine) {
        appendDiagnostic(state, "[REDACTED]\n");
        state.discardingOversizedLine = true;
      }
      state.pending = "";
      return;
    }
    if (final && state.pending) {
      if (!state.discardingOversizedLine) {
        appendDiagnostic(state, redactDiagnostic(state.pending));
      }
      state.pending = "";
    }
    return;
  }
}

function appendDiagnostic(state, value) {
  const bytes = Buffer.from(value, "utf8");
  state.tail = Buffer.concat([state.tail, bytes]).subarray(-MAX_DIAGNOSTIC_BYTES);
}

function diagnosticText(state) {
  if (!state) return "[no stderr]";
  flushDiagnosticPrefix(state, false);
  const redacted = Buffer.from(redactDiagnostic(Buffer.concat([
    state.tail,
    Buffer.from(state.pending, "utf8"),
  ]).toString("utf8")), "utf8");
  return boundDiagnosticText(redacted);
}

function redactError(error) {
  return boundDiagnosticText(Buffer.from(
    redactDiagnostic(error instanceof Error ? error.message : error),
    "utf8",
  ));
}

function boundDiagnosticText(value) {
  let text = value.subarray(-MAX_DIAGNOSTIC_BYTES).toString("utf8");
  while (Buffer.byteLength(text, "utf8") > MAX_DIAGNOSTIC_BYTES) {
    text = text.slice(1);
  }
  return text;
}

export function redactDiagnostic(value) {
  let text = String(value);
  text = text.replace(
    /(?:\b(?:bearer|token|secret|password|capability|credential|authorization)\b\s*(?:[:=]\s*|\s+)|\b(?:browser-fixture(?:-token)?|simulator-token)[-_])[A-Za-z0-9._~+/=-]*/giu,
    "[REDACTED]",
  );
  text = text.replace(/\b[A-Za-z0-9_-]{32,}\b/gu, "[REDACTED]");
  text = text.replace(
    /(?:\/Users\/|\/private\/var\/|\/var\/folders\/|\/private\/tmp\/|\/tmp\/)[^\s"'`]+/gu,
    "[PATH_REDACTED]",
  );
  return text;
}

function waitForChildClose(child) {
  if (
    (child.exitCode !== null || child.signalCode !== null) &&
    child.stdout?.destroyed &&
    child.stderr?.destroyed
  ) {
    return Promise.resolve();
  }
  return new Promise((resolvePromise) => child.once("close", resolvePromise));
}

async function waitForChildCloseWithin(exited, milliseconds) {
  let timeout;
  const deadline = new Promise((resolvePromise) => {
    timeout = setTimeout(() => resolvePromise(false), milliseconds);
  });
  try {
    return await Promise.race([exited.then(() => true), deadline]);
  } finally {
    clearTimeout(timeout);
  }
}
