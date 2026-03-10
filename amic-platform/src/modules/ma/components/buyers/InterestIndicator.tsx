import type { BuyerTier } from "@/modules/ma/types/buyer";

interface InterestIndicatorProps {
  tier: BuyerTier | null;
}

const TIER_LABEL: Record<string, string> = {
  TIER_1: "관심도: 높음 (Tier 1)",
  TIER_2: "관심도: 중간 (Tier 2)",
  TIER_3: "관심도: 낮음 (Tier 3)",
};

/**
 * 3단 세로 막대기 형태의 관심도 표시기.
 * Tier 1 = 3개 활성, Tier 2 = 2개 활성, Tier 3 = 1개 활성.
 */
export default function InterestIndicator({ tier }: InterestIndicatorProps) {
  const level =
    tier === "TIER_1" ? 3 : tier === "TIER_2" ? 2 : tier === "TIER_3" ? 1 : 0;
  const label = tier ? (TIER_LABEL[tier] ?? "대상 아님") : "대상 아님";

  return (
    <span
      className="inline-flex items-end gap-px"
      role="img"
      aria-label={label}
      title={label}
    >
      <span
        className={`w-[3px] h-[6px] rounded-sm ${level >= 1 ? "bg-accent" : "bg-gray-200"}`}
      />
      <span
        className={`w-[3px] h-[9px] rounded-sm ${level >= 2 ? "bg-accent" : "bg-gray-200"}`}
      />
      <span
        className={`w-[3px] h-[12px] rounded-sm ${level >= 3 ? "bg-accent" : "bg-gray-200"}`}
      />
    </span>
  );
}
