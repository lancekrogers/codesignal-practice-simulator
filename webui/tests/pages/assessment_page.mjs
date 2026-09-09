import { expect } from "@playwright/test";

export class AssessmentPage {
  constructor(page) {
    this.page = page;
  }

  level(number) {
    return this.page.getByRole("button", { name: `Level ${number}: Level ${number}` });
  }

  tab(name) {
    return this.page.getByRole("tab", { name });
  }

  timer() {
    return this.page.getByRole("timer", { name: "Time remaining" });
  }

  async expectShell() {
    await expect(this.page.getByRole("main")).toBeVisible();
    await expect(this.page.getByRole("navigation", { name: "Assessment levels" }))
      .toBeVisible();
    await expect(this.page.getByRole("toolbar", { name: "Assessment actions" })).toBeVisible();
    await expect(this.page.getByTestId("prompt-pane")).toBeVisible();
    await expect(this.page.getByTestId("editor-pane")).toBeVisible();
    await expect(this.page.getByTestId("output-drawer")).toBeVisible();
  }

  async expectConnected() {
    await expect(this.page.getByText("Connected", { exact: true })).toBeVisible();
  }

  async expectLifecycle(status) {
    await expect(this.page.getByText(status, { exact: true })).toBeVisible();
  }

  async expectServerDeadline(deadline) {
    await expect(this.page.getByText(`Server deadline: ${deadline}`, { exact: true }))
      .toBeVisible();
  }

  async expectNoHorizontalClipping() {
    const metrics = await this.page.evaluate(() => {
      const panes = [...document.querySelectorAll("[data-testid]")];
      return {
        documentWidth: document.documentElement.scrollWidth,
        viewportWidth: document.documentElement.clientWidth,
        panes: panes.map((pane) => {
          const box = pane.getBoundingClientRect();
          return { left: box.left, right: box.right };
        }),
      };
    });
    expect(metrics.documentWidth).toBeLessThanOrEqual(metrics.viewportWidth);
    for (const pane of metrics.panes) {
      expect(pane.left).toBeGreaterThanOrEqual(0);
      expect(pane.right).toBeLessThanOrEqual(metrics.viewportWidth);
    }
  }
}
