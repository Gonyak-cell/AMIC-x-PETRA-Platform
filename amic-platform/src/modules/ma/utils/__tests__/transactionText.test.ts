import { describe, expect, it } from "vitest";

import {
  GARBLED_TRANSACTION_TEXT_ERROR,
  getTransactionTextError,
  hasGarbledTransactionText,
} from "../transactionText";

describe("transactionText", () => {
  it("accepts normal Korean text", () => {
    expect(hasGarbledTransactionText("NX게임즈")).toBe(false);
    expect(getTransactionTextError("최일곤")).toBeUndefined();
  });

  it("flags question-mark runs as garbled text", () => {
    expect(hasGarbledTransactionText("NX3???")).toBe(true);
    expect(getTransactionTextError("???")).toBe(
      GARBLED_TRANSACTION_TEXT_ERROR,
    );
  });

  it("flags replacement characters as garbled text", () => {
    expect(hasGarbledTransactionText("테스트\uFFFD")).toBe(true);
  });
});
