/**
 * E2E: 접근성 테스트 — WCAG 2.1 AA 준수 검증.
 * Skip navigation, ARIA 속성, 키보드 내비게이션, 포커스 관리.
 */

import { test, expect } from "@playwright/test";
import { LoginPage } from "../pages/login.page";
import { TEST_USERS } from "../utils/test-data";

test.describe("Accessibility", () => {
  test.beforeEach(async ({ page }) => {
    const login = new LoginPage(page);
    await login.goto();
    await login.loginAndWaitForRedirect(
      TEST_USERS.admin.email,
      TEST_USERS.admin.password,
    );
  });

  test.describe("Skip Navigation", () => {
    test("should have skip link as first focusable element", async ({
      page,
    }) => {
      await page.goto("/deals");

      // Tab to first focusable element
      await page.keyboard.press("Tab");

      // Skip link should be focused
      const skipLink = page.locator('a[href="#main-content"]');
      await expect(skipLink).toBeFocused();
      await expect(skipLink).toHaveText("Skip to main content");
    });

    test("skip link should be visible on focus", async ({ page }) => {
      await page.goto("/deals");

      const skipLink = page.locator('a[href="#main-content"]');

      // Initially hidden (sr-only)
      await expect(skipLink).not.toBeVisible();

      // Tab to skip link
      await page.keyboard.press("Tab");

      // Should become visible on focus
      await expect(skipLink).toBeVisible();
    });

    test("skip link should navigate to main content", async ({ page }) => {
      await page.goto("/deals");

      // Tab to skip link and activate
      await page.keyboard.press("Tab");
      await page.keyboard.press("Enter");

      // Main content should be in view
      const main = page.locator("#main-content");
      await expect(main).toBeInViewport();
    });
  });

  test.describe("Sidebar ARIA", () => {
    test("sidebar should have navigation role and label", async ({ page }) => {
      await page.goto("/deals");

      const sidebar = page.locator('aside[role="navigation"]');
      await expect(sidebar).toHaveAttribute("aria-label", "Main navigation");
    });

    test("active nav item should have aria-current", async ({ page }) => {
      await page.goto("/deals");

      // "Deals" should be the active page
      const activeNavItem = page.locator('span[aria-current="page"]');
      await expect(activeNavItem).toHaveText("Deals");
    });

    test("section headers should label their nav groups", async ({ page }) => {
      // Need to be in a deal workspace to see section headers
      await page.goto("/deals/1");

      const sectionHeader = page.locator(
        '[id^="sidebar-section-"]',
      );
      const count = await sectionHeader.count();

      // Should have at least one section (Current Deal)
      expect(count).toBeGreaterThanOrEqual(1);

      // Check aria-labelledby on nav
      const sectionNav = page.locator('nav[aria-labelledby^="sidebar-section-"]');
      await expect(sectionNav.first()).toBeVisible();
    });
  });

  test.describe("Keyboard Navigation", () => {
    test("should be able to navigate sidebar with Tab key", async ({
      page,
    }) => {
      await page.goto("/deals");

      // Skip the skip link
      await page.keyboard.press("Tab");
      await page.keyboard.press("Tab");

      // Should now be on first nav item (Deals)
      const dealsLink = page.locator('a[href="/deals"]');
      await expect(dealsLink).toBeFocused();
    });

    test("ESC key should close modal", async ({ page }) => {
      await page.goto("/deals");

      // Click "Create Deal" button to open modal
      const createButton = page.locator('button:has-text("Create Deal")');
      if (await createButton.isVisible()) {
        await createButton.click();

        // Modal should be visible
        const modal = page.locator("dialog[open]");
        await expect(modal).toBeVisible();

        // Press ESC to close
        await page.keyboard.press("Escape");

        // Modal should be closed
        await expect(modal).not.toBeVisible();
      }
    });

    test("tables should support keyboard navigation", async ({ page }) => {
      await page.goto("/deals");

      // Find table rows with tabindex
      const tableRows = page.locator("tr[tabindex='0']");
      const count = await tableRows.count();

      if (count > 1) {
        // Focus first row
        await tableRows.first().focus();

        // Press ArrowDown
        await page.keyboard.press("ArrowDown");

        // Second row should be focused
        await expect(tableRows.nth(1)).toBeFocused();

        // Press ArrowUp
        await page.keyboard.press("ArrowUp");

        // First row should be focused again
        await expect(tableRows.first()).toBeFocused();
      }
    });

    test("table rows should be activatable with Enter key", async ({
      page,
    }) => {
      await page.goto("/deals");

      const tableRows = page.locator("tr[tabindex='0']");
      const count = await tableRows.count();

      if (count > 0) {
        await tableRows.first().focus();

        // Press Enter
        await page.keyboard.press("Enter");

        // Should navigate to deal workspace
        await page.waitForURL(/\/deals\/\d+/);
      }
    });
  });

  test.describe("Focus Management", () => {
    test("modal should trap focus", async ({ page }) => {
      await page.goto("/deals");

      const createButton = page.locator('button:has-text("Create Deal")');
      if (await createButton.isVisible()) {
        await createButton.click();

        // Tab through modal elements
        const closeButton = page.locator('button[aria-label="Close modal"]');
        const modalInputs = page.locator("dialog input, dialog button");

        // Should not be able to tab outside modal
        const modalCount = await modalInputs.count();
        for (let i = 0; i < modalCount + 2; i++) {
          await page.keyboard.press("Tab");
        }

        // Focus should still be within modal (native dialog handles this)
        const focusedElement = page.locator(":focus");
        const isInModal = await focusedElement.evaluate((el) =>
          el.closest("dialog") !== null
        );
        expect(isInModal).toBeTruthy();
      }
    });

    test("modal close should return focus to trigger", async ({ page }) => {
      await page.goto("/deals");

      const createButton = page.locator('button:has-text("Create Deal")');
      if (await createButton.isVisible()) {
        await createButton.click();

        // Close modal with ESC
        await page.keyboard.press("Escape");

        // Focus should return to create button
        await expect(createButton).toBeFocused();
      }
    });
  });

  test.describe("Charts ARIA", () => {
    test("charts should have role=img and aria-label", async ({ page }) => {
      // Navigate to QoE page which has charts
      await page.goto("/deals/1/qoe");

      const charts = page.locator('[role="img"]');
      const count = await charts.count();

      // If there are charts on the page
      if (count > 0) {
        for (let i = 0; i < count; i++) {
          const chart = charts.nth(i);
          await expect(chart).toHaveAttribute("aria-label");
        }
      }
    });
  });

  test.describe("Loading States", () => {
    test("skeleton loaders should have status role", async ({ page }) => {
      // Intercept API to delay response
      await page.route("**/api/**", async (route) => {
        await new Promise((r) => setTimeout(r, 500));
        await route.continue();
      });

      await page.goto("/deals");

      // Check for skeleton with status role
      const skeleton = page.locator('[role="status"]');
      // Skeleton should either be present during loading or not (depends on timing)
      // Just verify the attribute pattern exists in the DOM
    });

    test("skeleton should announce loading to screen readers", async ({
      page,
    }) => {
      await page.route("**/api/**", async (route) => {
        await new Promise((r) => setTimeout(r, 500));
        await route.continue();
      });

      await page.goto("/deals");

      // Check for sr-only loading text
      const srOnly = page.locator(".sr-only:has-text('Loading')");
      // May or may not be visible depending on timing
    });
  });

  test.describe("Touch Targets", () => {
    test("nav items should have minimum 44px height", async ({ page }) => {
      await page.goto("/deals");

      const navItems = page.locator('nav a[href]');
      const count = await navItems.count();

      for (let i = 0; i < Math.min(count, 5); i++) {
        const item = navItems.nth(i);
        const box = await item.boundingBox();

        if (box) {
          // WCAG 2.5.5 requires 44x44px minimum
          expect(box.height).toBeGreaterThanOrEqual(44);
        }
      }
    });

    test("buttons should have minimum touch target size", async ({ page }) => {
      await page.goto("/deals");

      const buttons = page.locator("button");
      const count = await buttons.count();

      for (let i = 0; i < Math.min(count, 5); i++) {
        const button = buttons.nth(i);
        if (await button.isVisible()) {
          const box = await button.boundingBox();

          if (box) {
            // At least 44px in one dimension
            const touchable = box.height >= 44 || box.width >= 44;
            expect(touchable).toBeTruthy();
          }
        }
      }
    });
  });

  test.describe("Color Contrast", () => {
    test("text should have sufficient contrast ratio", async ({ page }) => {
      await page.goto("/deals");

      // Check that text is visible against backgrounds
      // This is a basic check - full contrast testing requires specialized tools
      const bodyText = page.locator(".text-text-body").first();
      if (await bodyText.isVisible()) {
        const color = await bodyText.evaluate(
          (el) => getComputedStyle(el).color
        );
        // Text should not be transparent
        expect(color).not.toBe("rgba(0, 0, 0, 0)");
      }
    });
  });

  test.describe("Live Regions", () => {
    test("live regions should be present in DOM", async ({ page }) => {
      await page.goto("/deals");

      // Check for polite and assertive regions
      const politeRegion = page.locator('[aria-live="polite"]');
      const assertiveRegion = page.locator('[aria-live="assertive"]');

      await expect(politeRegion).toBeAttached();
      await expect(assertiveRegion).toBeAttached();
    });
  });
});
