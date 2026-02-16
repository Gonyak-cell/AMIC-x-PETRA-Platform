import type { Page } from "@playwright/test";

export class LoginPage {
  constructor(private page: Page) {}

  // ── Locators ──

  get emailInput() {
    return this.page.getByLabel("Email");
  }
  get passwordInput() {
    return this.page.getByLabel("Password");
  }
  get submitButton() {
    return this.page.getByRole("button", { name: /sign in/i });
  }
  get errorMessage() {
    return this.page.locator(".text-negative");
  }
  get heading() {
    return this.page.getByRole("heading", { name: "Auto FDD" });
  }

  // ── Actions ──

  async goto() {
    await this.page.goto("/login");
  }

  async login(email: string, password: string) {
    await this.emailInput.fill(email);
    await this.passwordInput.fill(password);
    await this.submitButton.click();
  }

  async loginAndWaitForRedirect(email: string, password: string) {
    await this.login(email, password);
    await this.page.waitForURL("**/deals**");
  }
}
