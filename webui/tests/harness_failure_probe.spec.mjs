import { expect, test } from "@playwright/test";
import { writeFile } from "node:fs/promises";
import {
  installOfflineRequestPolicy,
  startFixtureServer,
} from "./browser_harness.mjs";
import { EntryPage } from "./pages/entry_page.mjs";

const FAILURE_PROBE = process.env.HARNESS_FAILURE_PROBE === "1";
const CLEANUP_FAILURE_PROBE =
  process.env.HARNESS_CLEANUP_FAILURE_PROBE === "1";
const OUTPUT_OWNERSHIP_FAILURE_PROBE =
  process.env.HARNESS_OUTPUT_OWNERSHIP_FAILURE_PROBE === "1";
const PROBE_TOKEN = process.env.HARNESS_FAILURE_PROBE_TOKEN;
const PROBE_RAW_SCREENSHOT = process.env.HARNESS_FAILURE_PROBE_RAW_SCREENSHOT;
const PROBE_MASK_BOXES = process.env.HARNESS_FAILURE_PROBE_MASK_BOXES;
const PROMPT_SENTINEL = "SYNTHETIC_PROMPT_CONTENT_SENTINEL";
const SOURCE_SENTINEL = "SYNTHETIC_CANDIDATE_SOURCE_SENTINEL";
const RESPONSE_SENTINEL = "SYNTHETIC_RESPONSE_BODY_SENTINEL";
const REFERENCE_SENTINEL = "SYNTHETIC_REFERENCE_FETCH_ONLY_SENTINEL";
const PRIVATE_PATH_SENTINEL = "/Users/lancerogers/private/diagnostic.py";

if (FAILURE_PROBE && !PROBE_TOKEN) {
  throw new Error("missing failure probe token");
}

test.describe("synthetic output ownership failure probe", () => {
  test.skip(
    !OUTPUT_OWNERSHIP_FAILURE_PROBE,
    "opt-in output ownership failure probe",
  );

  test("would write a raw artifact if its body were allowed to run", async (
    {},
    testInfo,
  ) => {
    await writeFile(
      testInfo.outputPath("raw-synthetic-artifact.txt"),
      "RAW_OUTPUT_OWNERSHIP_PROBE_SENTINEL",
      "utf8",
    );
  });
});

test.describe("synthetic failure probe", () => {
  test.skip(!FAILURE_PROBE, "opt-in failure probe");

  let harness;
  let requestPolicy;

  test.beforeEach(async ({ page }) => {
    harness = await startFixtureServer({ token: PROBE_TOKEN });
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

  test("intentionally fails after a tokenized synthetic assessment", async ({
    page,
  }, testInfo) => {
    const entry = new EntryPage(page);
    await entry.open(harness.origin, PROBE_TOKEN);
    const startResponse = entry.confirmStartResponse();
    await entry.start("drill");
    const started = await (await startResponse).json();
    expect(started.data.session.status).toBe("active");
    await expect(page.getByText("Python editor ready.", { exact: false })).toBeVisible();

    await page.route("**/favicon.svg", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "text/html",
        body: `<main>${RESPONSE_SENTINEL}</main>`,
      });
    });
    await page.evaluate(() => fetch("/favicon.svg").then((response) => response.text()));
    await page.locator(".monaco-editor").click();
    await page.keyboard.press("Control+End");
    await page.keyboard.type(
      `\n# ${SOURCE_SENTINEL}\n# ${REFERENCE_SENTINEL}\n# ${PRIVATE_PATH_SENTINEL}`,
    );
    await page.evaluate((values) => {
      const promptPane = document.querySelector('[data-testid="prompt-pane"]');
      const prompt = promptPane?.querySelector(".prompt-copy") || promptPane;
      if (prompt) {
        prompt.textContent =
          `${values.prompt}\n${values.reference}\n${values.path}`;
      }
      const output = document.querySelector('[data-testid="output-drawer"]');
      if (output) {
        const marker = document.createElement("pre");
        marker.dataset.sensitiveContent = "output";
        marker.textContent =
          `${values.response}\n${values.reference}\n${values.path}`;
        output.append(marker);
      }
    }, {
      path: PRIVATE_PATH_SENTINEL,
      prompt: PROMPT_SENTINEL,
      reference: REFERENCE_SENTINEL,
      response: RESPONSE_SENTINEL,
    });

    const attachmentText = [
      PROMPT_SENTINEL,
      SOURCE_SENTINEL,
      RESPONSE_SENTINEL,
      REFERENCE_SENTINEL,
      PRIVATE_PATH_SENTINEL,
    ].join("\n");
    for (const name of ["stdout", "synthetic.txt"]) {
      const path = testInfo.outputPath(name);
      await writeFile(path, attachmentText, "utf8");
      await testInfo.attach(name, { path, contentType: "text/plain" });
    }

    const boxes = await page.locator(
      '[data-testid="prompt-pane"], [data-testid="editor-pane"], ' +
        '[data-testid="output-drawer"]',
    ).evaluateAll((elements) => elements.map((element) => {
      const box = element.getBoundingClientRect();
      return { x: box.x, y: box.y, width: box.width, height: box.height };
    }));
    if (PROBE_RAW_SCREENSHOT) {
      await writeFile(PROBE_RAW_SCREENSHOT, await page.screenshot());
    }
    if (PROBE_MASK_BOXES) {
      await writeFile(PROBE_MASK_BOXES, JSON.stringify(boxes), "utf8");
    }
    await page.evaluate(() => console.error("unexpected synthetic guard failure"));
    throw new Error("intentional failure probe");
  });
});

test.describe("synthetic cleanup-failure probe", () => {
  test.skip(!CLEANUP_FAILURE_PROBE, "opt-in cleanup-failure probe");

  test("passes before reporter cleanup fails", () => {
    expect(true).toBe(true);
  });
});
