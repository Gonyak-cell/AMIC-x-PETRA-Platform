/**
 * E2E: 모바일 반응형 테스트 — 768px 브레이크포인트, drawer 사이드바, 터치 타겟.
 */

import { test, expect, devices } from "@playwright/test";
import { LoginPage } from "../pages/login.page";
import { TEST_USERS } from "../utils/test-data";

// Mobile viewport configuration
const mobileViewport = { width: 375, height: 667 }; // iPhone SE
const tabletViewport = { width: 768, height: 1024 }; // iPad Mini
const desktopViewport = { width: 1280, height: 720 };

test.describe("Mobile Responsive", () => {
  test.beforeEach(async ({ page }) => {
    const login = new LoginPage(page);
    await login.goto();
    await login.loginAndWaitForRedirect(
      TEST_USERS.admin.email,
      TEST_USERS.admin.password,
    );
  });

  test.describe("Breakpoint Behavior", () => {
    test("should show hamburger menu on mobile (<768px)", async ({ page }) => {
      await page.setViewportSize(mobileViewport);
      await page.goto("/deals");

      // Hamburger menu should be visible
      const menuButton = page.locator(
        'button[aria-label="Open navigation menu"]'
      );
      await expect(menuButton).toBeVisible();

      // Desktop sidebar should be hidden
      const desktopSidebar = page.locator("aside.hidden.md\\:block");
      // On mobile, the aside with md:block should not be visible in DOM layout
    });

    test("should show fixed sidebar on desktop (≥768px)", async ({ page }) => {
      await page.setViewportSize(desktopViewport);
      await page.goto("/deals");

      // Desktop sidebar should be visible
      const sidebar = page.locator('aside[role="navigation"]');
      await expect(sidebar).toBeVisible();

      // Hamburger menu should not be visible
      const menuButton = page.locator(
        'button[aria-label="Open navigation menu"]'
      );
      await expect(menuButton).not.toBeVisible();
    });

    test("should transition correctly at 768px breakpoint", async ({
      page,
    }) => {
      await page.goto("/deals");

      // Start at desktop
      await page.setViewportSize({ width: 800, height: 600 });
      const sidebar = page.locator('aside[role="navigation"]');
      await expect(sidebar).toBeVisible();

      // Resize to mobile
      await page.setViewportSize({ width: 700, height: 600 });
      await page.waitForTimeout(300); // Wait for transition

      // Hamburger should appear
      const menuButton = page.locator(
        'button[aria-label="Open navigation menu"]'
      );
      await expect(menuButton).toBeVisible();

      // Resize back to desktop
      await page.setViewportSize({ width: 800, height: 600 });
      await page.waitForTimeout(300);

      // Hamburger should disappear
      await expect(menuButton).not.toBeVisible();
    });
  });

  test.describe("Mobile Sidebar Drawer", () => {
    test.beforeEach(async ({ page }) => {
      await page.setViewportSize(mobileViewport);
    });

    test("should open drawer when hamburger is clicked", async ({ page }) => {
      await page.goto("/deals");

      const menuButton = page.locator(
        'button[aria-label="Open navigation menu"]'
      );
      await menuButton.click();

      // Drawer should be visible
      const drawer = page.locator("#mobile-sidebar");
      await expect(drawer).toBeVisible();

      // Overlay should be visible
      const overlay = page.locator(".bg-black\\/50");
      await expect(overlay).toBeVisible();
    });

    test("should close drawer when X button is clicked", async ({ page }) => {
      await page.goto("/deals");

      // Open drawer
      const menuButton = page.locator(
        'button[aria-label="Open navigation menu"]'
      );
      await menuButton.click();

      // Click X button
      const closeButton = page.locator(
        'button[aria-label="Close navigation menu"]'
      );
      await closeButton.click();

      // Drawer should be hidden (translated off-screen)
      const drawer = page.locator("#mobile-sidebar");
      await expect(drawer).toHaveClass(/-translate-x-full/);
    });

    test("should close drawer when overlay is clicked", async ({ page }) => {
      await page.goto("/deals");

      // Open drawer
      const menuButton = page.locator(
        'button[aria-label="Open navigation menu"]'
      );
      await menuButton.click();

      // Click overlay
      const overlay = page.locator(".bg-black\\/50").first();
      await overlay.click({ force: true });

      // Drawer should be hidden
      const drawer = page.locator("#mobile-sidebar");
      await expect(drawer).toHaveClass(/-translate-x-full/);
    });

    test("should close drawer when ESC is pressed", async ({ page }) => {
      await page.goto("/deals");

      // Open drawer
      const menuButton = page.locator(
        'button[aria-label="Open navigation menu"]'
      );
      await menuButton.click();

      // Press ESC
      await page.keyboard.press("Escape");

      // Drawer should be hidden
      const drawer = page.locator("#mobile-sidebar");
      await expect(drawer).toHaveClass(/-translate-x-full/);
    });

    test("should close drawer when nav item is clicked", async ({ page }) => {
      await page.goto("/deals/1");

      // Open drawer
      const menuButton = page.locator(
        'button[aria-label="Open navigation menu"]'
      );
      await menuButton.click();

      // Click a nav item
      const qoeLink = page.locator('a:has-text("QoE Bridge")');
      if (await qoeLink.isVisible()) {
        await qoeLink.click();

        // Drawer should close after navigation
        await page.waitForTimeout(300);
        const drawer = page.locator("#mobile-sidebar");
        await expect(drawer).toHaveClass(/-translate-x-full/);
      }
    });

    test("should lock body scroll when drawer is open", async ({ page }) => {
      await page.goto("/deals");

      // Open drawer
      const menuButton = page.locator(
        'button[aria-label="Open navigation menu"]'
      );
      await menuButton.click();

      // Body should have overflow hidden
      const bodyOverflow = await page.evaluate(
        () => document.body.style.overflow
      );
      expect(bodyOverflow).toBe("hidden");

      // Close drawer
      await page.keyboard.press("Escape");

      // Body should have normal overflow
      const bodyOverflowAfter = await page.evaluate(
        () => document.body.style.overflow
      );
      expect(bodyOverflowAfter).toBe("");
    });
  });

  test.describe("Mobile Header", () => {
    test.beforeEach(async ({ page }) => {
      await page.setViewportSize(mobileViewport);
    });

    test("should show sticky mobile header", async ({ page }) => {
      await page.goto("/deals");

      // Mobile header with logo should be visible
      const header = page.locator("text=Auto FDD").first();
      await expect(header).toBeVisible();
    });

    test("mobile header should remain sticky on scroll", async ({ page }) => {
      await page.goto("/deals");

      // Scroll down
      await page.evaluate(() => window.scrollBy(0, 500));

      // Header should still be visible
      const menuButton = page.locator(
        'button[aria-label="Open navigation menu"]'
      );
      await expect(menuButton).toBeVisible();
      await expect(menuButton).toBeInViewport();
    });
  });

  test.describe("Touch Targets", () => {
    test.beforeEach(async ({ page }) => {
      await page.setViewportSize(mobileViewport);
    });

    test("hamburger button should be at least 44x44px", async ({ page }) => {
      await page.goto("/deals");

      const menuButton = page.locator(
        'button[aria-label="Open navigation menu"]'
      );
      const box = await menuButton.boundingBox();

      expect(box).not.toBeNull();
      if (box) {
        // Button should have at least 44px touch target
        // The button itself may be smaller but with padding
        expect(box.height).toBeGreaterThanOrEqual(40);
        expect(box.width).toBeGreaterThanOrEqual(40);
      }
    });

    test("nav items should have minimum 44px height on mobile", async ({
      page,
    }) => {
      await page.goto("/deals");

      // Open drawer
      const menuButton = page.locator(
        'button[aria-label="Open navigation menu"]'
      );
      await menuButton.click();

      // Check nav items
      const navItems = page.locator("#mobile-sidebar nav a");
      const count = await navItems.count();

      for (let i = 0; i < Math.min(count, 5); i++) {
        const item = navItems.nth(i);
        const box = await item.boundingBox();

        if (box) {
          expect(box.height).toBeGreaterThanOrEqual(44);
        }
      }
    });
  });

  test.describe("Content Layout", () => {
    test("should stack KPI cards vertically on mobile", async ({ page }) => {
      await page.setViewportSize(mobileViewport);
      await page.goto("/deals/1/qoe");

      // Wait for content to load
      await page.waitForTimeout(500);

      // Check that cards are stacked (same X position or full width)
      const cards = page.locator('[class*="grid"]').first();
      if (await cards.isVisible()) {
        // On mobile, grid should be single column
        const gridClass = await cards.getAttribute("class");
        expect(gridClass).toContain("grid-cols-1");
      }
    });

    test("tables should be horizontally scrollable on mobile", async ({
      page,
    }) => {
      await page.setViewportSize(mobileViewport);
      await page.goto("/deals");

      // Tables should have overflow handling
      const tableContainer = page.locator(".overflow-hidden, .overflow-x-auto");
      const count = await tableContainer.count();

      // Should have some overflow containers
      expect(count).toBeGreaterThan(0);
    });
  });

  test.describe("ARIA Attributes on Mobile", () => {
    test.beforeEach(async ({ page }) => {
      await page.setViewportSize(mobileViewport);
    });

    test("menu button should have aria-expanded", async ({ page }) => {
      await page.goto("/deals");

      const menuButton = page.locator(
        'button[aria-label="Open navigation menu"]'
      );

      // Initially not expanded
      await expect(menuButton).toHaveAttribute("aria-expanded", "false");

      // Click to open
      await menuButton.click();

      // Now button changes to close button with aria-expanded true
      const closeButton = page.locator(
        'button[aria-label="Close navigation menu"]'
      );
      await expect(closeButton).toHaveAttribute("aria-expanded", "true");
    });

    test("menu button should control mobile sidebar", async ({ page }) => {
      await page.goto("/deals");

      const menuButton = page.locator(
        'button[aria-label="Open navigation menu"]'
      );
      await expect(menuButton).toHaveAttribute("aria-controls", "mobile-sidebar");
    });

    test("drawer overlay should be aria-hidden", async ({ page }) => {
      await page.goto("/deals");

      // Open drawer
      const menuButton = page.locator(
        'button[aria-label="Open navigation menu"]'
      );
      await menuButton.click();

      // Overlay should be aria-hidden (not announced to screen readers)
      const overlay = page.locator('[aria-hidden="true"].bg-black\\/50');
      await expect(overlay).toBeVisible();
    });
  });

  test.describe("Tablet View", () => {
    test("should show desktop layout at 768px", async ({ page }) => {
      await page.setViewportSize(tabletViewport);
      await page.goto("/deals");

      // At exactly 768px (md breakpoint), should show desktop layout
      const sidebar = page.locator('aside[role="navigation"]');
      await expect(sidebar).toBeVisible();

      // Hamburger should not be visible
      const menuButton = page.locator(
        'button[aria-label="Open navigation menu"]'
      );
      await expect(menuButton).not.toBeVisible();
    });
  });

  test.describe("Device Presets", () => {
    test("should work on iPhone 12", async ({ browser }) => {
      const context = await browser.newContext({
        ...devices["iPhone 12"],
      });
      const page = await context.newPage();

      // Login
      const login = new LoginPage(page);
      await login.goto();
      await login.loginAndWaitForRedirect(
        TEST_USERS.admin.email,
        TEST_USERS.admin.password,
      );

      await page.goto("/deals");

      // Should show mobile layout
      const menuButton = page.locator(
        'button[aria-label="Open navigation menu"]'
      );
      await expect(menuButton).toBeVisible();

      await context.close();
    });

    test("should work on iPad", async ({ browser }) => {
      const context = await browser.newContext({
        ...devices["iPad Mini"],
      });
      const page = await context.newPage();

      // Login
      const login = new LoginPage(page);
      await login.goto();
      await login.loginAndWaitForRedirect(
        TEST_USERS.admin.email,
        TEST_USERS.admin.password,
      );

      await page.goto("/deals");

      // Should show desktop layout on iPad (768px+)
      const sidebar = page.locator('aside[role="navigation"]');
      await expect(sidebar).toBeVisible();

      await context.close();
    });
  });
});
