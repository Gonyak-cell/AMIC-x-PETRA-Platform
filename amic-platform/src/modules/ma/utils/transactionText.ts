export const GARBLED_TRANSACTION_TEXT_ERROR =
  "한글 입력이 깨진 것으로 보입니다. 입력기 상태를 확인한 뒤 다시 입력해 주세요.";

const QUESTION_RUN_PATTERN = /\?{3,}/;

export function hasGarbledTransactionText(
  value: string | null | undefined,
): boolean {
  if (typeof value !== "string") {
    return false;
  }

  const normalized = value.trim();
  if (!normalized) {
    return false;
  }

  return (
    normalized.includes("\uFFFD") || QUESTION_RUN_PATTERN.test(normalized)
  );
}

export function getTransactionTextError(
  value: string | null | undefined,
): string | undefined {
  return hasGarbledTransactionText(value)
    ? GARBLED_TRANSACTION_TEXT_ERROR
    : undefined;
}
