import type { BadgeVariant } from "@/components/ui/Badge";

/**
 * 상태값에 따른 배지 variant 자동 결정
 */
export function getStatusVariant(status: string): BadgeVariant {
  const upper = status.toUpperCase();

  if (["ACTIVE", "APPROVED", "COMPLETED", "SUCCESS", "MAPPED"].includes(upper)) {
    return "success";
  }
  if (["DRAFT", "PENDING", "CANDIDATE", "PROCESSING", "IN_PROGRESS"].includes(upper)) {
    return "warning";
  }
  if (["FAILED", "REJECTED", "CRITICAL", "ERROR", "UNMAPPED"].includes(upper)) {
    return "error";
  }
  if (["INFO", "NEW"].includes(upper)) {
    return "info";
  }
  return "neutral";
}
