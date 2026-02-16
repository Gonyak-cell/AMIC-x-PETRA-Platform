import type { Page } from "@playwright/test";

export interface ConsoleMonitor {
  errors: string[];
  warnings: string[];
  unhandledExceptions: string[];
  assertNoErrors: () => void;
  assertNoUnhandledExceptions: () => void;
}

/** Benign console error patterns to ignore */
const BENIGN_PATTERNS = [
  "favicon.ico",
  "DevTools",
  "ResizeObserver loop",
  "Download the React DevTools",
  "[HMR]",
  "Vite",
];

function isBenign(message: string): boolean {
  return BENIGN_PATTERNS.some((p) => message.includes(p));
}

/**
 * Attach console and pageerror listeners to capture JS errors during test.
 * Call `assertNoErrors()` after page interactions to verify no real errors occurred.
 */
export function attachConsoleMonitor(page: Page): ConsoleMonitor {
  const monitor: ConsoleMonitor = {
    errors: [],
    warnings: [],
    unhandledExceptions: [],

    assertNoErrors() {
      const real = this.errors.filter((e) => !isBenign(e));
      if (real.length > 0) {
        throw new Error(
          `Unexpected console errors (${real.length}):\n${real.map((e) => `  - ${e}`).join("\n")}`,
        );
      }
    },

    assertNoUnhandledExceptions() {
      if (this.unhandledExceptions.length > 0) {
        throw new Error(
          `Unhandled exceptions (${this.unhandledExceptions.length}):\n${this.unhandledExceptions.map((e) => `  - ${e}`).join("\n")}`,
        );
      }
    },
  };

  page.on("console", (msg) => {
    if (msg.type() === "error") monitor.errors.push(msg.text());
    if (msg.type() === "warning") monitor.warnings.push(msg.text());
  });

  page.on("pageerror", (err) => {
    monitor.unhandledExceptions.push(err.message);
  });

  return monitor;
}
