/**
 * Test data constants and generators for E2E tests.
 */

export const TEST_USERS = {
  admin: {
    email: "admin@autofdd.dev",
    password: "Admin1234!",
    role: "ADMIN",
  },
  analyst: {
    email: "analyst@autofdd.dev",
    password: "Analyst1234!",
    role: "ANALYST",
  },
  viewer: {
    email: "viewer@autofdd.dev",
    password: "Viewer1234!",
    role: "VIEWER",
  },
} as const;

export const DEFAULT_DEAL = {
  name: "E2E Test Deal",
  deal_type: "COMPLETION_ACCOUNTS" as const,
  base_currency: "KRW",
  reference_date: "2025-12-31",
  period_start: "2025-01-01",
  period_end: "2025-12-31",
};

export function uniqueDealName(prefix = "E2E"): string {
  return `${prefix} ${Date.now().toString(36).toUpperCase()}`;
}

/** Generate a date string YYYY-MM-DD offset from today. */
export function offsetDate(days: number): string {
  const d = new Date();
  d.setDate(d.getDate() + days);
  return d.toISOString().slice(0, 10);
}
