import type { BadgeVariant } from "@/components/ui";

/** IB 매체 소스명 → 한글 표시 라벨 */
export const IB_SOURCE_LABELS: Record<string, string> = {
  investchosun: "인베스트조선",
  dealsite: "딜사이트",
  ibtomato: "IB토마토",
  bloter: "블로터",
};

/** Opinion 카테고리별 Badge variant */
export const IB_OPINION_BADGE_VARIANT: Record<string, BadgeVariant> = {
  investment_style: "neutral",
  reputation: "warning",
  personnel_evaluation: "info",
};
