import type { BuyerTier } from "@/modules/ma/types/buyer";

interface InterestIndicatorProps {
  tier: BuyerTier | null;
}

/**
 * 3단 세로 막대기 형태의 관심도 표시기.
 * Tier 1 = 3개 활성, Tier 2 = 2개 활성, Tier 3 = 1개 활성.
 */
export default function InterestIndicator({ tier }: InterestIndicatorProps) {
  const level =
    tier === "TIER_1" ? 3 : tier === "TIER_2" ? 2 : tier === "TIER_3" ? 1 : 0;
  const title =
    tier === "TIER_1"
      ? "High Interest"
      : tier === "TIER_2"
        ? "Mid Interest"
        : tier === "TIER_3"
          ? "Low Interest"
          : "Not Targeted";

  return (
    <span className="inline-flex items-end gap-px" role="img" aria-label={title} title={title}>
      <span
        className={`w-[3px] rounded-sm ${level >= 1 ? "bg-accent" : "bg-gray-200"}`}
        style={{ height: 6 }}
      />
      <span
        className={`w-[3px] rounded-sm ${level >= 2 ? "bg-accent" : "bg-gray-200"}`}
        style={{ height: 9 }}
      />
      <span
        className={`w-[3px] rounded-sm ${level >= 3 ? "bg-accent" : "bg-gray-200"}`}
        style={{ height: 12 }}
      />
    </span>
  );
}
