import { createHash } from "node:crypto";
import { expect, test } from "@playwright/test";
import {
  installOfflineRequestPolicy,
  startFixtureServer,
} from "./browser_harness.mjs";
import { AssessmentPage } from "./pages/assessment_page.mjs";
import { EditorPage } from "./pages/editor_page.mjs";
import { EntryPage } from "./pages/entry_page.mjs";

let harness;
let requestPolicy;

test.beforeEach(async ({ page }) => {
  harness = await startFixtureServer();
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

test("shows duration, first-party rules, and no-pause terms before start", async ({
  page,
}) => {
  const entry = new EntryPage(page);
  await entry.open(harness.origin, harness.token);

  await expect(page.getByText("Full assessment · 90 minutes", { exact: true }))
    .toBeVisible();
  await expect(page.getByText("Focused drill · 30 minutes", { exact: true }))
    .toBeVisible();
  const rules = page.getByRole("region", { name: "Before you start" });
  await expect(rules).toBeVisible();
  await expect(rules).toContainText(
    "The timer is authoritative and cannot be paused.",
  );
  await expect(rules).toContainText(
    "Source changes are saved with optimistic concurrency.",
  );
  await expect(rules).toContainText(
    "Test and submit use the latest saved source.",
  );
  await expect(rules).toContainText(
    "No pause: the server timer starts with your confirmed choice and remains authoritative.",
  );

  await entry.openStartDialog();
  await expect(page.getByRole("dialog", { name: "Confirm start" })).toContainText(
    "The timer begins immediately and cannot be paused.",
  );
  await entry.cancelStart();
});

test("provides Python syntax, indentation, and bracket completion in Monaco", async ({
  page,
}) => {
  const entry = new EntryPage(page);
  const editorPage = new EditorPage(page);
  const started = await startAttempt(page, entry);
  await editorPage.expectReady();

  const editor = page.locator(".monaco-editor");
  await editor.click();
  await page.keyboard.press("Meta+A");
  await page.keyboard.type("def syntax_probe():");
  await page.keyboard.press("Enter");
  await page.keyboard.type("result = ");
  // Wait for tokenization of the preceding Python line before testing the
  // language-aware auto-closing operation, not just editor initialization.
  await expect.poll(async () => {
    const tokens = await computedLineTokens(page, "def syntax_probe");
    const keyword = tokens.find(({ text }) => text.trim() === "def");
    const name = tokens.find(({ text }) => text.includes("syntax_probe"));
    return keyword && name ? keyword.color !== name.color : false;
  }).toBe(true);
  await expect.poll(() => lineTokenText(page, "result =")).toContain("result = ");
  await page.keyboard.type("(");
  await expect.poll(() => lineTokenText(page, "result =")).toContain("result = ()");
  await page.keyboard.type("1");
  await expect.poll(() => lineTokenText(page, "result =")).toContain("result = (1)");

  const expectedSource = "def syntax_probe():\n    result = (1)";
  const attemptId = started.data.session.attempt_id;
  await expect.poll(async () => {
    const persisted = await readSource(page, attemptId, harness.token);
    return persisted.document.data.content;
  }).toContain(expectedSource);
  await expect(saveStatus(page)).toHaveText("Saved snapshot");
});

test("returns timestamped and hashed candidate history through the public envelope", async ({
  page,
}) => {
  const entry = new EntryPage(page);
  const started = await startAttempt(page, entry);
  const { attempt_id: attemptId } = started.data.session;
  const firstSavedAt = "2030-01-01T00:05:00+00:00";
  const secondSavedAt = "2030-01-01T00:06:00+00:00";
  const firstEdit = "\n# first timestamped candidate edit";
  const secondEdit = "\n# second timestamped candidate edit";
  const initialContent = started.data.source.content;
  const firstContent = `${initialContent}${firstEdit}`;
  const secondContent = `${firstContent}${secondEdit}`;

  await harness.setClock(firstSavedAt);
  await append(page, firstEdit);
  await expect.poll(async () =>
    (await readSource(page, attemptId, harness.token)).document.data.content
  ).toBe(firstContent);
  await harness.setClock(secondSavedAt);
  await append(page, secondEdit);
  await expect.poll(async () =>
    (await readSource(page, attemptId, harness.token)).document.data.content
  ).toBe(secondContent);
  await expect(saveStatus(page)).toHaveText("Saved snapshot");

  const history = await readHistory(page, attemptId, harness.token);
  expect(history.status).toBe(200);
  expect(history.document).toMatchObject({
    schema_version: "web/v1",
    ok: true,
    data: { current: { content: expect.any(String), etag: expect.any(String) } },
  });
  const snapshots = history.document.data.snapshots;
  expect(snapshots).toHaveLength(2);
  expect(snapshots.map((snapshot) => Date.parse(snapshot.created_at))).toEqual([
    Date.parse(secondSavedAt),
    Date.parse(firstSavedAt),
  ]);
  expect(history.document.data.current.content).toBe(secondContent);
  expect(snapshots).toMatchObject([
    {
      operation: "save",
      prior_hash: hashFor(firstContent),
      new_hash: hashFor(secondContent),
    },
    {
      operation: "save",
      prior_hash: hashFor(initialContent),
      new_hash: hashFor(firstContent),
    },
  ]);
  expect(history.document.data.current.etag).toBe(hashFor(secondContent));
});

test("restores the oldest repeated-content predecessor through history UI", async ({
  page,
}) => {
  const entry = new EntryPage(page);
  const editorPage = new EditorPage(page);
  const started = await startAttempt(page, entry);
  const { attempt_id: attemptId } = started.data.session;
  const initialContent = started.data.source.content;
  const firstContent = `${initialContent}\n# repeated first`;
  const secondContent = `${firstContent}\n# repeated second`;
  const sequence = [firstContent, secondContent, firstContent, firstContent];
  let etag = started.data.source.etag;

  for (const content of sequence) {
    const saved = await saveSource(page, attemptId, harness.token, content, etag);
    expect(saved.status).toBe(200);
    etag = saved.document.data.source.etag;
  }

  await page.reload();
  await entry.expectReconnectAction();
  await page.getByRole("button", { name: "Reconnect to active session" }).click();
  await editorPage.expectReady();
  await page.getByRole("tab", { name: "History" }).click();
  const historyItems = page.locator(".history-item");
  await expect(historyItems).toHaveCount(3);
  await expect(historyItems.nth(2).locator("pre")).toContainText(initialContent);

  const restoreResponse = page.waitForResponse((response) =>
    new URL(response.url()).pathname === "/api/source/restore" &&
    response.request().method() === "POST",
  );
  await historyItems.nth(2)
    .getByRole("button", { name: "Restore this version" })
    .click();
  await page.getByRole("dialog")
    .getByRole("button", { name: "Restore version" })
    .click();
  expect((await restoreResponse).status()).toBe(200);

  await expect.poll(async () =>
    (await readSource(page, attemptId, harness.token)).document.data.content
  ).toBe(initialContent);
  const persisted = await readHistory(page, attemptId, harness.token);
  expect(persisted.document.data.current).toMatchObject({
    content: initialContent,
    etag: hashFor(initialContent),
  });
});

test("recovers the active source and server deadline after refresh", async ({ page }) => {
  const entry = new EntryPage(page);
  const assessment = new AssessmentPage(page);
  const editorPage = new EditorPage(page);
  const started = await startAttempt(page, entry);
  const { attempt_id: attemptId, deadline_at: deadline } = started.data.session;
  const marker = "# durable refreshed source";

  await append(page, `\n${marker}`);
  await expect.poll(async () =>
    (await readSource(page, attemptId, harness.token)).document.data.content
  ).toContain(marker);
  await page.reload();
  await entry.expectReconnectAction();
  await page.getByRole("button", { name: "Reconnect to active session" }).click();
  await assessment.expectServerDeadline(deadline);
  await editorPage.expectReady();
  await expect(page.getByRole("main")).toHaveAttribute("data-attempt-id", attemptId);
  await expect(editorPage.pane().locator(".view-lines")).toContainText(marker);
});

test("recovers the active source and server deadline after a process restart", async ({
  page,
}) => {
  const entry = new EntryPage(page);
  const assessment = new AssessmentPage(page);
  const editorPage = new EditorPage(page);
  const started = await startAttempt(page, entry);
  const { attempt_id: attemptId, deadline_at: deadline } = started.data.session;
  const marker = "# durable active source";

  await append(page, `\n${marker}`);
  await expect.poll(async () =>
    (await readSource(page, attemptId, harness.token)).document.data.content
  ).toContain(marker);
  await assessment.level(3).click();
  await assessment.tab("Info").click();
  await expect(assessment.promptPane()).toContainText("Selected level: 3 of 4");
  await page.evaluate(() => document.fonts.ready);
  await harness.restart();
  requestPolicy.refreshOrigin();
  await page.goto(`${harness.origin}/#token=${harness.token}`);
  const reconnect = page.getByRole("button", { name: "Reconnect to active session" });
  await page.waitForFunction(() =>
    Boolean(document.querySelector('[role="timer"]')) ||
    [...document.querySelectorAll("button")]
      .some((button) => button.textContent === "Reconnect to active session"),
  );
  if (await reconnect.isVisible()) await reconnect.click();
  await assessment.expectServerDeadline(deadline);
  await editorPage.expectReady();
  await expect(page.getByRole("main")).toHaveAttribute("data-attempt-id", attemptId);
  await expect(editorPage.pane().locator(".view-lines")).toContainText(marker);
});

async function startAttempt(page, entry) {
  const response = entry.confirmStartResponse();
  await entry.open(harness.origin, harness.token);
  await entry.openStartDialog();
  await entry.confirmStart();
  return (await response).json();
}

async function append(page, value) {
  await page.locator(".monaco-editor").click();
  await page.keyboard.press("Control+End");
  await page.keyboard.type(value);
}

function saveStatus(page) {
  return page.locator(".assessment-header .header-status").nth(1).locator("strong");
}

async function computedLineTokens(page, containing) {
  return page.locator(".monaco-editor .view-line").evaluateAll((lines, needle) => {
    const normalize = (value) => value?.replace(/\u00a0/gu, " ") || "";
    const line = lines.find((candidate) => normalize(candidate.textContent).includes(needle));
    if (!line) return [];
    return [...line.querySelectorAll("span")]
      .filter((token) => !token.querySelector("span"))
      .map((token) => ({
        text: normalize(token.textContent),
        color: getComputedStyle(token).color,
      }));
  }, containing);
}

async function lineTokenText(page, containing) {
  return (await computedLineTokens(page, containing))
    .map(({ text }) => text)
    .join("");
}

function hashFor(content) {
  return `sha256:${createHash("sha256").update(content).digest("hex")}`;
}

async function readSource(page, attemptId, token) {
  return page.evaluate(async ({ id, capability }) => {
    const response = await fetch(`/api/source?attempt_id=${encodeURIComponent(id)}`, {
      headers: { "X-Simulator-Token": capability },
    });
    return { status: response.status, document: await response.json() };
  }, { id: attemptId, capability: token });
}

async function saveSource(page, attemptId, token, content, etag) {
  return page.evaluate(async ({ id, capability, source, expected }) => {
    const response = await fetch(`/api/source?attempt_id=${encodeURIComponent(id)}`, {
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
        "If-Match": expected,
        "X-Simulator-Token": capability,
      },
      body: JSON.stringify({ content: source }),
    });
    return { status: response.status, document: await response.json() };
  }, { id: attemptId, capability: token, source: content, expected: etag });
}

async function readHistory(page, attemptId, token) {
  return page.evaluate(async ({ id, capability }) => {
    const response = await fetch(`/api/source/history?attempt_id=${encodeURIComponent(id)}`, {
      headers: { "X-Simulator-Token": capability },
    });
    return { status: response.status, document: await response.json() };
  }, { id: attemptId, capability: token });
}
