/** Test data constants for E2E tests */

export const TEST_DEAL = {
  name: `E2E Test Deal ${Date.now()}`,
  type: "COMPLETION_ACCOUNTS" as const,
  currency: "KRW",
};

export const TEST_COMPANY = {
  corpCode: "00126380", // Samsung Electronics
  name: "삼성전자",
};

export const TEST_DOCUMENT = {
  projectName: `E2E Test IM ${Date.now()}`,
  style: "TITAN" as const,
};

/** Generate a unique test name with timestamp */
export function uniqueName(prefix: string): string {
  return `${prefix}-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`;
}
