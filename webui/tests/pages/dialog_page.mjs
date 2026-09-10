import { expect } from "@playwright/test";

export class DialogPage {
  constructor(page) {
    this.page = page;
  }

  dialog(name) {
    return name
      ? this.page.getByRole("dialog", { name })
      : this.page.getByRole("dialog");
  }

  async expectOpen(name) {
    const dialog = this.dialog(name);
    await expect(dialog).toBeVisible();
    return dialog;
  }

  async confirm(label, name) {
    const dialog = await this.expectOpen(name);
    await dialog.getByRole("button", { name: label }).click();
    await expect(dialog).toBeHidden();
  }

  async cancel(name) {
    const dialog = await this.expectOpen(name);
    await dialog.getByRole("button", { name: "Cancel" }).click();
    await expect(dialog).toBeHidden();
  }

  async expectFocus(label, name) {
    await expect(
      (await this.expectOpen(name)).getByRole("button", { name: label }),
    ).toBeFocused();
  }
}
