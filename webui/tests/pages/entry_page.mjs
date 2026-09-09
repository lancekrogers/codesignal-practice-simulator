import { expect } from "@playwright/test";

export class EntryPage {
  constructor(page) {
    this.page = page;
  }

  main() {
    return this.page.getByRole("main");
  }

  profile(mode) {
    const name = mode === "drill" ? /Focused drill/ : /Full assessment/;
    return this.page.getByRole("radio", { name });
  }

  async expectLoaded() {
    await expect(this.main()).toBeVisible();
    await expect(this.page.getByRole("heading", { name: "File Storage" })).toBeVisible();
    await expect(this.page.getByRole("status")).toContainText("No attempt has started.");
  }

  async choose(mode) {
    await this.profile(mode).check();
    await expect(this.profile(mode)).toBeChecked();
  }

  async openStartDialog() {
    await this.page.getByRole("button", { name: "Start practice" }).click();
    await expect(this.page.getByRole("dialog", { name: "Confirm start" })).toBeVisible();
  }

  async confirmStart() {
    await this.page.getByRole("button", { name: "Confirm and start" }).click();
  }

  async cancelStart() {
    await this.page.getByRole("button", { name: "Cancel" }).click();
    await expect(this.page.getByRole("dialog", { name: "Confirm start" })).toBeHidden();
  }

  async start(mode = "full") {
    await this.choose(mode);
    await this.openStartDialog();
    await this.confirmStart();
  }

  async expectReconnectAction(active = true) {
    const label = active ? "Reconnect to active session" : "View final session";
    await expect(this.page.getByRole("button", { name: label })).toBeVisible();
  }
}
