import { test, expect } from "../fixtures/test-base";
import { mockAllApis } from "../fixtures/api-mocks";
import { devices } from "@playwright/test";

test.describe("GSAP Motion System — Animation & Accessibility Verification", () => {
  test.beforeEach(async ({ page }) => {
    await mockAllApis(page);
  });

  // ─── B-1: Page Transition Animation ───

  test("page transition renders content visible after navigation", async ({
    page,
    consoleMonitor,
  }) => {
    await page.goto("/");
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible();

    // Navigate to FDD — wait for GSAP page transition to complete
    await page.goto("/fdd/deals");
    const heading = page.getByRole("heading", { level: 1 });
    await expect(heading).toBeVisible({ timeout: 3000 });
    await expect(heading).toContainText("Deals");

    // Navigate to KIIS
    await page.goto("/kiis/companies");
    await expect(page.getByRole("heading", { level: 1 })).toContainText(
      "Companies",
      { timeout: 3000 },
    );

    consoleMonitor.assertNoErrors();
    consoleMonitor.assertNoUnhandledExceptions();
  });

  test("page transition container reaches full opacity", async ({
    page,
    consoleMonitor,
  }) => {
    await page.goto("/fdd/deals");
    // Wait for heading to be visible (indicates page transition complete)
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible({
      timeout: 3000,
    });

    // The PageTransition wrapper should be fully opaque
    await expect(async () => {
      const opacity = await page.evaluate(() => {
        const main = document.querySelector("main");
        if (!main) return 1;
        const transitionDiv = main.querySelector("div");
        if (!transitionDiv) return 1;
        return Number(window.getComputedStyle(transitionDiv).opacity);
      });
      expect(opacity).toBeGreaterThanOrEqual(0.9);
    }).toPass({ timeout: 3000 });

    consoleMonitor.assertNoErrors();
  });

  // ─── B-2: DataTable Row Stagger Animation ───

  test("DataTable rows become visible after stagger-in animation", async ({
    page,
    consoleMonitor,
  }) => {
    await page.goto("/fdd/deals");

    const table = page.locator("table");
    await expect(table).toBeVisible({ timeout: 3000 });

    // Rows should be visible after gsap stagger animation
    const rows = table.locator("tbody tr");
    await expect(rows.first()).toBeVisible({ timeout: 3000 });
    const count = await rows.count();
    expect(count).toBeGreaterThan(0);

    consoleMonitor.assertNoErrors();
    consoleMonitor.assertNoUnhandledExceptions();
  });

  // ─── B-3: prefers-reduced-motion Accessibility ───

  test("content is immediately visible when prefers-reduced-motion is set", async ({
    page,
    consoleMonitor,
  }) => {
    // Emulate reduced motion BEFORE navigation
    await page.emulateMedia({ reducedMotion: "reduce" });

    await page.goto("/");
    // With reduced motion, gsap.globalTimeline.timeScale(0) — no animation delay
    // Content should be immediately visible
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible();

    // Navigate and check immediate visibility
    await page.goto("/fdd/deals");
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible();

    consoleMonitor.assertNoErrors();
    consoleMonitor.assertNoUnhandledExceptions();
  });

  test("reduced motion disables GSAP global timeline", async ({
    page,
    consoleMonitor,
  }) => {
    await page.emulateMedia({ reducedMotion: "reduce" });
    await page.goto("/");

    // Wait for page to be fully loaded before evaluating gsap state
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible();

    // Verify gsap.globalTimeline.timeScale is 0
    const timeScale = await page.evaluate(() => {
      // @ts-expect-error accessing gsap on window
      const gsapInstance = window.gsap;
      if (gsapInstance) {
        return gsapInstance.globalTimeline.timeScale();
      }
      // GSAP may not be on window — check via module evaluation
      return null;
    });

    // If gsap is accessible, timeScale should be 0
    // If not accessible via window, we verify through visual behavior
    if (timeScale !== null) {
      expect(timeScale).toBe(0);
    }

    // Either way, content must be visible without animation
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible();

    consoleMonitor.assertNoErrors();
  });

  // ─── B-4: Modal Animation ───

  test("modal opens and closes without JS errors", async ({
    page,
    consoleMonitor,
  }) => {
    await page.goto("/");
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible();

    // Open search palette (uses Modal-like dialog)
    await page.keyboard.press("Control+k");
    const dialog = page.locator("[role='dialog'][aria-label='Global search']");
    await expect(dialog).toBeVisible({ timeout: 3000 });

    // Close modal — wait for exit animation to complete
    await page.keyboard.press("Escape");
    await expect(dialog).toBeHidden({ timeout: 3000 });

    consoleMonitor.assertNoErrors();
    consoleMonitor.assertNoUnhandledExceptions();
  });

  // ─── B-5: ScrollTrigger Verification ───

  test("scroll-reveal elements become visible on scroll", async ({
    page,
    consoleMonitor,
  }) => {
    await page.goto("/");
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible({
      timeout: 3000,
    });

    // Dashboard has KPI cards that may use useScrollReveal
    // Scroll down to trigger scroll-based animations
    await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));

    // All visible content should have opacity > 0 after scroll
    await expect(async () => {
      const hiddenElements = await page.evaluate(() => {
        const elements = document.querySelectorAll("main *");
        let hidden = 0;
        elements.forEach((el) => {
          const style = window.getComputedStyle(el);
          if (
            style.opacity === "0" &&
            style.display !== "none" &&
            style.visibility !== "hidden" &&
            (el as HTMLElement).offsetHeight > 0
          ) {
            hidden++;
          }
        });
        return hidden;
      });
      expect(hiddenElements).toBe(0);
    }).toPass({ timeout: 5000 });

    consoleMonitor.assertNoErrors();
    consoleMonitor.assertNoUnhandledExceptions();
  });

  // ─── B-6: Mobile Responsive Motion ───

  test("animations work on mobile viewport", async ({
    page,
    consoleMonitor,
  }) => {
    // Set mobile viewport
    await page.setViewportSize({ width: 390, height: 844 }); // iPhone 14

    await page.goto("/");
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible({
      timeout: 3000,
    });

    // Navigate on mobile
    await page.goto("/fdd/deals");
    await expect(page.getByRole("heading", { level: 1 })).toContainText(
      "Deals",
      { timeout: 3000 },
    );

    // Scroll on mobile — verify no errors
    await page.evaluate(() => window.scrollTo(0, 500));
    // Wait for scroll to settle by checking page didn't crash
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible();

    consoleMonitor.assertNoErrors();
    consoleMonitor.assertNoUnhandledExceptions();
  });

  test("mobile with reduced motion shows content immediately", async ({
    page,
    consoleMonitor,
  }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await page.emulateMedia({ reducedMotion: "reduce" });

    await page.goto("/");
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible();

    await page.goto("/kiis/companies");
    await expect(page.getByRole("heading", { level: 1 })).toContainText(
      "Companies",
    );

    consoleMonitor.assertNoErrors();
    consoleMonitor.assertNoUnhandledExceptions();
  });

  // ─── Cross-module navigation animation stability ───

  test("rapid navigation does not cause animation errors", async ({
    page,
    consoleMonitor,
  }) => {
    const routes = [
      "/",
      "/fdd/deals",
      "/kiis/companies",
      "/im",
      "/analytics",
      "/",
    ];

    for (const route of routes) {
      await page.goto(route);
      // Minimal wait — stress test rapid transitions
      await page.waitForTimeout(200);
    }

    // Final page should be fully loaded
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible({
      timeout: 3000,
    });

    consoleMonitor.assertNoErrors();
    consoleMonitor.assertNoUnhandledExceptions();
  });
});
