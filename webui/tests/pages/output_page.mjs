import { expect } from "@playwright/test";

export class OutputPage {
  constructor(page) {
    this.page = page;
  }

  pane() {
    return this.page.getByTestId("output-drawer");
  }

  summary() {
    return this.pane().getByText(
      /^(?:Practice|Final) result · Passed levels: \d+ of \d+\.$/u,
    ).first();
  }

  level(level) {
    return this.pane().getByRole("listitem").filter({
      hasText: `Level ${level}:`,
    });
  }

  async expectPracticeResult(passed, total) {
    await expect(this.summary()).toHaveText(
      `Practice result · Passed levels: ${passed} of ${total}.`,
    );
  }

  async expectFinalResult(passed, total) {
    await expect(this.summary()).toHaveText(
      `Final result · Passed levels: ${passed} of ${total}.`,
    );
  }

  async expectLevel(level, text) {
    await expect(this.level(level)).toContainText(text);
  }

  async expectMessage(text) {
    await expect(this.pane()).toContainText(text);
  }
}
