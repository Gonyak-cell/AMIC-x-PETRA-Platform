import { test as base, expect } from "@playwright/test";
import { attachConsoleMonitor, type ConsoleMonitor } from "./console-monitor";

type DeepTestFixtures = {
  consoleMonitor: ConsoleMonitor;
};

/**
 * Extended test fixture with console monitoring.
 * Use in deep verification tests for JS error detection.
 */
export const test = base.extend<DeepTestFixtures>({
  consoleMonitor: async ({ page }, use) => {
    const monitor = attachConsoleMonitor(page);
    await use(monitor);
  },
});

export { expect };
