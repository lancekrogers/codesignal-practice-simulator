import { readFile } from "node:fs/promises";
import { join } from "node:path";
import { expect, test } from "@playwright/test";
import {
  installOfflineRequestPolicy,
  startFixtureServer,
} from "./browser_harness.mjs";

test.describe.configure({ mode: "serial" });

const COACHING_SENTINEL = "CONTINUITY_COACHING_SENTINEL_7f3c";
const CONTEXT_KEYS = [
  "assessment",
  "attempt_id",
  "events",
  "lifecycle",
  "next_legal_commands",
  "schema_version",
  "score",
];
const ASSESSMENT_KEYS = ["display_name", "id", "mode", "profile"];
const LIFECYCLE_KEYS = ["deadline_at", "started_at", "status", "submitted_at"];
const SCORE_KEYS = ["highest_contiguous_level", "levels", "passed_levels"];
const EVENT_KEYS = ["name", "occurred_at", "outcome", "revision"];
const LEVEL_SCORE_KEYS = ["level", "outcome"];

let harness;
let requestPolicy;

test.beforeEach(async ({ page }) => {
  harness = await startFixtureServer({
    clockStart: "2030-01-01T00:00:00+00:00",
  });
  requestPolicy = await installOfflineRequestPolicy(page, harness);
});

test.afterEach(async () => {
  const currentHarness = harness;
  const currentPolicy = requestPolicy;
  harness = undefined;
  requestPolicy = undefined;
  try {
    if (currentPolicy) await currentPolicy.assert();
  } finally {
    if (currentHarness) await currentHarness.close();
  }
});

test("keeps one real browser attempt continuous with the public CLI", async ({
  page,
}) => {
  const started = await startBrowserAttempt(page, harness);
  const attemptId = started.data.session.attempt_id;
  await verifyCoachingJourney(page, harness, started.data.session, attemptId);
  const tested = await runBrowserTest(page, harness, attemptId);
  await submitBrowserAttempt(page, harness, tested, attemptId);
});

async function startBrowserAttempt(page, server) {
  await page.goto(`${server.origin}/#token=${server.token}`);
  const startResponse = page.waitForResponse(isPostTo("/api/attempts"));
  await page.getByRole("button", { name: "Start practice" }).click();
  await page.getByRole("button", { name: "Confirm and start" }).click();
  const started = await (await startResponse).json();
  await expect(page.getByTestId("editor-pane")).toBeVisible();
  return started;
}

async function verifyCoachingJourney(page, server, session, attemptId) {
  const guidance = await server.readGuidance(attemptId);
  expect(guidance.agents).toContain(
    "Ask explicit permission before reading candidate source or source history",
  );
  expect(guidance.agents).toContain("ask separately before editing source");
  expect(guidance.coaching).toContain("Candidate-owned, non-executable notes");
  await server.writeCoaching(
    attemptId,
    `# Candidate note\n- ${COACHING_SENTINEL}: review the approach.\n`,
  );
  expect(await server.readCoaching(attemptId)).toContain(COACHING_SENTINEL);
  await assertContinuity(server, session, attemptId, ["started"]);
  await assertNoCoachingInReadSurfaces(page, server, attemptId);
  const browserTime = await readBrowserTime(page, server, attemptId);
  expect(browserTime.status).toBe(200);
  await assertContinuity(
    server,
    browserTime.document.data.session,
    attemptId,
    ["started"],
  );
}

async function runBrowserTest(page, server, attemptId) {
  const testResponse = page.waitForResponse(isPostTo("/api/test"));
  await page.getByRole("button", { name: "Run Tests" }).click();
  const tested = await (await testResponse).json();
  expect(JSON.stringify(tested)).not.toContain(COACHING_SENTINEL);
  await expect(page.getByTestId("output-drawer")).toContainText("Practice result");
  await expect(page.getByTestId("output-drawer")).not.toContainText(
    COACHING_SENTINEL,
  );
  await assertContinuity(
    server,
    tested.data.session,
    attemptId,
    ["started", "tested"],
  );
  return tested;
}

async function submitBrowserAttempt(page, server, tested, attemptId) {
  const submitResponse = page.waitForResponse(isPostTo("/api/submit"));
  await page.getByRole("button", { name: "Submit" }).click();
  await page.getByRole("button", { name: "Submit attempt" }).click();
  const submitted = await (await submitResponse).json();
  expect(JSON.stringify(submitted)).not.toContain(COACHING_SENTINEL);
  await expect(page.getByText("Submitted", { exact: true })).toBeVisible();
  await expect(page.getByTestId("output-drawer")).toContainText("Final result");
  await expect(page.getByTestId("output-drawer")).not.toContainText(
    COACHING_SENTINEL,
  );
  await assertContinuity(
    server,
    submitted.data.session,
    attemptId,
    ["started", "tested", "submitted"],
  );
  await assertRepeatSubmitStable(page, server, attemptId);
  await assertTerminalBrowserState(page, server, attemptId);
}

async function assertRepeatSubmitStable(page, server, attemptId) {
  const beforeContext = await server.cliContext(attemptId);
  const beforeStatus = await server.readStatus(attemptId);
  const repeated = await page.evaluate(async ({ attemptId, token }) => {
    const response = await fetch(`/api/submit?attempt_id=${attemptId}`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "If-Match": `sha256:${"f".repeat(64)}`,
        "X-Simulator-Token": token,
      },
      body: JSON.stringify({ content: "must not replace final source\n" }),
    });
    return { status: response.status, document: await response.json() };
  }, { attemptId, token: server.token });
  expect(repeated.status).toBe(200);
  expect(repeated.document.data.newly_submitted).toBe(false);
  expect(await server.cliContext(attemptId)).toEqual(beforeContext);
  expect(await server.readStatus(attemptId)).toBe(beforeStatus);
}

async function assertTerminalBrowserState(page, server, attemptId) {
  const simulation = await readFile(
    join(server.workspaceRoot, "attempts", attemptId, "simulation.py"),
    "utf8",
  );
  expect(simulation).not.toContain(COACHING_SENTINEL);
  for (const name of ["Save changes", "Run Tests", "Reset", "Submit"]) {
    await expect(page.getByRole("button", { name })).toBeDisabled();
  }
  await expect(page.locator(".fallback")).toHaveAttribute("readonly", "");
  const finalContext = await server.cliContext(attemptId);
  expect(finalContext.next_legal_commands).toEqual(legalCommands(
    attemptId,
    "submitted",
  ));
  expect(JSON.stringify(finalContext)).not.toContain(COACHING_SENTINEL);
  expect(await server.readStatus(attemptId)).not.toContain(COACHING_SENTINEL);
  expect(await page.locator("body").innerText()).not.toContain(
    COACHING_SENTINEL,
  );
  expect(await server.readCoaching(attemptId)).toContain(COACHING_SENTINEL);
  expect(await server.attemptEvents(attemptId)).toEqual([
    "started",
    "tested",
    "submitted",
  ]);
}

function isPostTo(pathname) {
  return (response) =>
    new URL(response.url()).pathname === pathname &&
    response.request().method() === "POST";
}

async function assertContinuity(server, browserSession, attemptId, events) {
  const context = await server.cliContext(attemptId);
  assertContextSchema(context);
  expect(context.attempt_id).toBe(browserSession.attempt_id);
  expect(context.attempt_id).toBe(attemptId);
  expect(context.lifecycle.status).toBe(browserSession.status);
  expect(context.lifecycle.deadline_at).toBe(browserSession.deadline_at);
  expect(context.score).toEqual(browserSession.score || emptyScore());
  expect(context.events.map((event) => event.name)).toEqual(events);
  expect(context.next_legal_commands).toEqual(legalCommands(
    attemptId,
    browserSession.status,
  ));
  expect(JSON.stringify(context)).not.toContain(COACHING_SENTINEL);
  expect(await server.readStatus(attemptId)).not.toContain(COACHING_SENTINEL);
  return context;
}

function assertContextSchema(context) {
  assertExactKeys(context, CONTEXT_KEYS);
  assertExactKeys(context.assessment, ASSESSMENT_KEYS);
  assertExactKeys(context.lifecycle, LIFECYCLE_KEYS);
  assertExactKeys(context.score, SCORE_KEYS);
  for (const level of context.score.levels) {
    assertExactKeys(level, LEVEL_SCORE_KEYS);
  }
  for (const event of context.events) {
    assertExactKeys(event, EVENT_KEYS);
  }
}

function assertExactKeys(value, expected) {
  expect(Object.keys(value).sort()).toEqual([...expected].sort());
}

async function assertNoCoachingInReadSurfaces(page, server, attemptId) {
  const responses = await page.evaluate(async ({ attemptId, token }) => {
    const headers = { "X-Simulator-Token": token };
    const paths = [
      `/api/source?attempt_id=${attemptId}`,
      `/api/source/history?attempt_id=${attemptId}`,
      ...[1, 2, 3, 4].map(
        (level) => `/api/prompts/${level}?attempt_id=${attemptId}`,
      ),
    ];
    return Promise.all(paths.map(async (path) => {
      const response = await fetch(path, { headers });
      return { status: response.status, body: await response.text() };
    }));
  }, { attemptId, token: server.token });
  expect(responses.every((response) => response.status === 200)).toBe(true);
  expect(JSON.stringify(responses)).not.toContain(COACHING_SENTINEL);
}

async function readBrowserTime(page, server, attemptId) {
  return page.evaluate(async ({ attemptId, token }) => {
    const response = await fetch(`/api/time?attempt_id=${attemptId}`, {
      headers: { "X-Simulator-Token": token },
    });
    return { status: response.status, document: await response.json() };
  }, { attemptId, token: server.token });
}

function emptyScore() {
  return {
    levels: [],
    passed_levels: 0,
    highest_contiguous_level: 0,
  };
}

function legalCommands(attemptId, status) {
  const selected = `--attempt ${attemptId}`;
  const commands = [
    `codesignal-sim status ${selected}`,
    `codesignal-sim context ${selected}`,
  ];
  if (status === "active") {
    commands.push(
      `codesignal-sim resume ${selected}`,
      `codesignal-sim time ${selected}`,
      `codesignal-sim test ${selected}`,
      `codesignal-sim submit ${selected}`,
    );
  }
  return commands;
}
