import { expect } from "@playwright/test";
import { OutputPage } from "./output_page.mjs";

export class FinalResultsPage {
  constructor(page) {
    this.page = page;
    this.output = new OutputPage(page);
  }

  async expectSubmitted() {
    await expect(this.page.getByText("Submitted", { exact: true })).toBeVisible();
    await expect(this.output.pane()).toBeVisible();
  }

  async expectScore(passed, total) {
    await this.expectSubmitted();
    await this.output.expectFinalResult(passed, total);
  }

  async expectReadOnly() {
    for (const name of ["Save changes", "Run Tests", "Reset", "Submit"]) {
      await expect(this.page.getByRole("button", { name })).toBeDisabled();
    }
    await expect(
      this.page.getByLabel("Read-only Python source fallback"),
    ).toHaveAttribute("readonly", "");
  }
}
