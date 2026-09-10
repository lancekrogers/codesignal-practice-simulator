import { expect } from "@playwright/test";

export class EditorPage {
  constructor(page) {
    this.page = page;
  }

  pane() {
    return this.page.getByTestId("editor-pane");
  }

  source() {
    return this.page.getByLabel("Python source editor").first();
  }

  fallback() {
    return this.page.getByRole("textbox", {
      name: "Read-only Python source fallback",
    });
  }

  settingsButton() {
    return this.page.getByRole("button", { name: "Settings" });
  }

  settingsDialog() {
    return this.page.getByRole("dialog", { name: "Editor settings" });
  }

  async expectReady() {
    await expect(this.pane()).toBeVisible();
    await expect(this.pane().getByRole("status")).toContainText("Python editor ready.");
    await expect(this.source()).toBeVisible();
  }

  async openSettings() {
    await this.settingsButton().click();
    await expect(this.settingsDialog()).toBeVisible();
  }

  async applySettings(values) {
    const dialog = this.settingsDialog();
    for (const [name, value] of Object.entries(values.selects || {})) {
      await dialog.getByLabel(name).selectOption(String(value));
    }
    for (const [name, checked] of Object.entries(values.checkboxes || {})) {
      const control = dialog.getByLabel(name);
      if (await control.isChecked() !== checked) {
        await control.setChecked(checked);
      }
    }
    await dialog.getByRole("button", { name: "Apply settings" }).click();
    await expect(dialog).toBeHidden();
  }

  async expectFallback(value) {
    await expect(this.source()).toBeHidden();
    await expect(this.fallback()).toBeVisible();
    await expect(this.fallback()).toHaveValue(value);
    await expect(this.fallback()).toHaveAttribute("readonly", "");
  }
}
