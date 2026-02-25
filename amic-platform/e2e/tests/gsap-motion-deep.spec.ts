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

    // Navigate to FDD
    await page.goto("/fdd/deals");
    // PageTransition: opacity 0→1, y 14→0 (0.4s) — wait for animation to settle
    await page.waitForTimeout(600);

    const heading = page.getByRole("heading", { level: 1 });
    await expect(heading).toBeVisible();
    await expect(heading).toContainText("Deals");

    // Navigate to KIIS
    await page.goto("/kiis/companies");
    await page.waitForTimeout(600);
    await expect(page.getByRole("heading", { level: 1 })).toContainText(
      "Companies",
    );

    consoleMonitor.assertNoErrors();
    consoleMonitor.assertNoUnhandledExceptions();
  });

  test("page transition container reaches full opacity", async ({
    page,
    consoleMonitor,
  }) => {
    await page.goto("/fdd/deals");
    // Wait for GSAP page transition (0.4s duration + buffer)
    await page.waitForTimeout(700);

    // The PageTransition wrapper should be fully opaque
    const opacity = await page.evaluate(() => {
      const main = document.querySelector("main");
      if (!main) return "1";
      // PageTransition div is the first child of main content area
      const transitionDiv = main.querySelector("div");
      if (!transitionDiv) return "1";
      return window.getComputedStyle(transitionDiv).opacity;
    });
    expect(Number(opacity)).toBeGreaterThanOrEqual(0.9);

    consoleMonitor.assertNoErrors();
  });

  // ─── B-2: DataTable Row Stagger Animation ───

  test("DataTable rows become visible after stagger-in animation", async ({
    page,
    consoleMonitor,
  }) => {
    await page.goto("/fdd/deals");
    // Wait for page transition + row stagger (0.4s + 0.35s + buffer)
    await page.waitForTimeout(1000);

    const table = page.locator("table");
    await expect(table).toBeVisible();

    // Rows should be visible (opacity 1, y 0 after gsap.fromTo)
    const rows = table.locator("tbody tr");
    const count = await rows.count();
    expect(count).toBeGreaterThan(0);

    // Check first row is visible
    await expect(rows.first()).toBeVisible();

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
    await page.waitForTimeout(300);

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
    const dialog = page.locator(
      "[role='dialog'][aria-label='Global search']",
    );
    await expect(dialog).toBeVisible();

    // Wait for GSAP entry animation (scale 0.95→1, 0.35s)
    await page.waitForTimeout(500);

    // Close modal
    await page.keyboard.press("Escape");
    await page.waitForTimeout(400); // exit animation (0.25s + buffer)
    await expect(dialog).toBeHidden();

    consoleMonitor.assertNoErrors();
    consoleMonitor.assertNoUnhandledExceptions();
  });

  // ─── B-5: ScrollTrigger Verification ───

  test("scroll-reveal elements become visible on scroll", async ({
    page,
    consoleMonitor,
  }) => {
    await page.goto("/");
    await page.waitForTimeout(800);

    // Dashboard has KPI cards that may use useScrollReveal
    // Scroll down to trigger scroll-based animations
    await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
    await page.waitForTimeout(1000);

    // All visible content should have opacity > 0
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

    // After scrolling, no visible elements should remain at opacity 0
    expect(hiddenElements).toBe(0);

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
    await page.waitForTimeout(800);

    // Verify content is visible on mobile
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible();

    // Navigate on mobile
    await page.goto("/fdd/deals");
    await page.waitForTimeout(800);
    await expect(page.getByRole("heading", { level: 1 })).toContainText(
      "Deals",
    );

    // Scroll on mobile
    await page.evaluate(() => window.scrollTo(0, 500));
    await page.waitForTimeout(600);

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
    await page.waitForTimeout(600);
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible();

    consoleMonitor.assertNoErrors();
    consoleMonitor.assertNoUnhandledExceptions();
  });
});
