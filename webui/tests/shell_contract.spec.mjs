import { expect, test } from "@playwright/test";
import {
  installOfflineRequestPolicy,
  startFixtureServer,
} from "./browser_harness.mjs";
import { AssessmentPage } from "./pages/assessment_page.mjs";
import { EntryPage } from "./pages/entry_page.mjs";
import { timeResponse, timerSeconds } from "./shell_test_support.mjs";

let harness;
let requestPolicy;

test.beforeEach(async () => {
  harness = await startFixtureServer();
});

test.beforeEach(async ({ page }) => {
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

for (const profile of [
  { mode: "full", profileId: "full-90m", duration: 5400 },
  { mode: "drill", profileId: "drill-30m", duration: 1800 },
]) {
  test(`requires confirmation and starts the exact ${profile.mode} profile`, async ({
    page,
  }) => {
    const entry = new EntryPage(page);
    const attempts = [];
    page.on("request", (request) => {
      if (new URL(request.url()).pathname === "/api/attempts") attempts.push(request);
    });
    await page.goto(`${harness.origin}/#token=${harness.token}`);
    await entry.expectLoaded();
    await entry.choose(profile.mode);
    await entry.openStartDialog();
    expect(attempts).toHaveLength(0);
    await entry.cancelStart();
    expect(attempts).toHaveLength(0);
    await entry.openStartDialog();
    const responsePromise = page.waitForResponse((response) =>
      new URL(response.url()).pathname === "/api/attempts" &&
      response.request().method() === "POST"
    );
    await entry.confirmStart();
    const response = await responsePromise;
    const document = await response.json();
    const session = document.data.session;
    expect(attempts).toHaveLength(1);
    expect(attempts[0].postDataJSON()).toEqual({
      assessment: "file_storage",
      mode: profile.mode,
      ...(profile.mode === "drill"
        ? { drill_duration_seconds: profile.duration }
        : {}),
    });
    expect(session.profile).toEqual({
      mode: profile.mode,
      profile_id: profile.profileId,
      duration_seconds: profile.duration,
    });
    expect(Date.parse(session.deadline_at) - Date.parse(session.started_at))
      .toBe(profile.duration * 1000);
    await expect(page.getByTestId("editor-pane")).toBeVisible();
    await expect(page.getByRole("main")).toContainText(
      `Local practice session · ${profile.mode} format`,
    );
  });
}

test("shows booting and reconnecting while preserving the selected session", async ({
  page,
}) => {
  const entry = new EntryPage(page);
  const assessment = new AssessmentPage(page);
  const posts = [];
  page.on("request", (request) => {
    if (request.method() === "POST") posts.push(request);
  });
  const bootstrapHeld = requestPolicy.hold("/api/bootstrap");
  const navigation = page.goto(`${harness.origin}/#token=${harness.token}`);
  await expect(page.getByText("Loading the local assessment…", { exact: true })).toBeVisible();
  await bootstrapHeld;
  requestPolicy.release("/api/bootstrap");
  await navigation;
  const started = await startWithResponse(page, entry, "full");
  const session = started.data.session;
  const attemptId = session.attempt_id;
  await page.reload();
  await expect(page.getByRole("main")).toHaveAttribute(
    "data-active-attempt-id",
    attemptId,
  );
  await entry.expectReconnectAction();
  const timePath = `/api/time?attempt_id=${attemptId}`;
  const timeHeld = requestPolicy.hold(timePath);
  await page.getByRole("button", { name: "Reconnect to active session" }).click();
  await expect(page.getByText("Reconnecting to the selected session…", { exact: true }))
    .toBeVisible();
  await timeHeld;
  requestPolicy.release(timePath);
  await assessment.expectShell();
  await assessment.expectConnected();
  await assessment.expectServerDeadline(session.deadline_at);
  expect(posts).toHaveLength(1);
});

test("resynchronizes the timer from a server snapshot without writing lifecycle state", async ({
  page,
}) => {
  const entry = new EntryPage(page);
  const assessment = new AssessmentPage(page);
  const mutations = [];
  page.on("request", (request) => {
    if (request.method() !== "GET") mutations.push(request);
  });
  await page.goto(`${harness.origin}/#token=${harness.token}`);
  await page.clock.install();
  const started = await startWithResponse(page, entry, "drill");
  const session = started.data.session;
  const time = {
    observed_at: session.started_at,
    elapsed_seconds: 0,
    remaining_seconds: 20,
  };
  requestPolicy.intercept(
    `/api/time?attempt_id=${session.attempt_id}`,
    timeResponse(session, time),
  );
  await page.clock.fastForward("00:15");
  await expect.poll(async () => timerSeconds(await assessment.timer().innerText()))
    .toBeLessThanOrEqual(20);
  await assessment.expectServerDeadline(session.deadline_at);
  expect(mutations).toHaveLength(1);
  expect(mutations[0].postDataJSON().mode).toBe("drill");
});

test("traverses entry, dialog, tabs, and levels without narrow viewport clipping", async ({
  page,
}) => {
  requestPolicy.expectFailedRequest({
    method: "GET",
    path: "/api/prompts/2",
    count: 1,
  });
  await page.setViewportSize({ width: 560, height: 900 });
  const entry = new EntryPage(page);
  const assessment = new AssessmentPage(page);
  await page.goto(`${harness.origin}/#token=${harness.token}`);
  await entry.expectLoaded();
  const start = page.getByRole("button", { name: "Start practice" });
  await start.focus();
  await page.keyboard.press("Enter");
  await expect(page.getByRole("button", { name: "Confirm and start" })).toBeFocused();
  await page.keyboard.press("Tab");
  await expect(page.getByRole("button", { name: "Cancel" })).toBeFocused();
  await page.keyboard.press("Shift+Tab");
  await expect(page.getByRole("button", { name: "Confirm and start" })).toBeFocused();
  await page.keyboard.press("Escape");
  await expect(start).toBeFocused();
  await start.press("Enter");
  await page.getByRole("button", { name: "Confirm and start" }).press("Enter");
  await assessment.expectShell();
  await expect(assessment.level(1)).toBeFocused();
  const promptFailure = page.waitForEvent("requestfailed", {
    predicate: (request) =>
      request.method() === "GET" &&
      new URL(request.url()).pathname === "/api/prompts/2",
  });
  const promptHeld = requestPolicy.hold("/api/prompts/2");
  await page.keyboard.press("ArrowRight");
  await expect(assessment.level(2)).toBeFocused();
  await promptHeld;
  await page.keyboard.press("Tab");
  await expect(assessment.tab("Description")).toBeFocused();
  await page.keyboard.press("ArrowRight");
  await expect(assessment.tab("History")).toBeFocused();
  await expect(assessment.tab("History")).toHaveAttribute("aria-selected", "true");
  await page.keyboard.press("Tab");
  await expect(page.getByRole("tabpanel")).toBeFocused();
  await expect(page.locator(".prompt-copy")).toHaveText(
    "No saved candidate versions yet.",
  );
  requestPolicy.release("/api/prompts/2");
  await promptFailure;
  await assessment.expectNoHorizontalClipping();
});

test("keeps expired sessions read-only and free of forbidden browser text", async ({
  page,
}) => {
  const entry = new EntryPage(page);
  const assessment = new AssessmentPage(page);
  await page.goto(`${harness.origin}/#token=${harness.token}`);
  await page.clock.install();
  const started = await startWithResponse(page, entry, "full");
  const session = started.data.session;
  requestPolicy.intercept(
    `/api/time?attempt_id=${session.attempt_id}`,
    timeResponse({ ...session, status: "expired" }, started.data.time),
  );
  await page.clock.fastForward("00:15");
  await assessment.expectLifecycle("Expired");
  await expect(page.getByRole("button", { name: "Submit" })).toBeDisabled();
  await expect(page.getByTestId("output-drawer")).toContainText(
    "attempt has expired",
  );
  const forbidden = [
    "/Users/private",
    "/tmp/private",
    "FETCH_ONLY",
    "SCORER_INTERNAL_SENTINEL",
  ];
  const domText = await page.getByRole("main").innerText();
  for (const sentinel of forbidden) {
    expect(domText).not.toContain(sentinel);
  }
  expect(requestPolicy.requestRecords().every(({ url }) =>
    new URL(url).origin === harness.origin,
  )).toBe(true);
});

async function startWithResponse(page, entry, mode) {
  const responsePromise = page.waitForResponse((response) =>
    new URL(response.url()).pathname === "/api/attempts" &&
    response.request().method() === "POST"
  );
  await entry.start(mode);
  return (await responsePromise).json();
}
