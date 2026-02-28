import type { BuyerTier } from "@/modules/ma/types/buyer";
import { BUYER_TIER_LABELS } from "@/modules/ma/constants";

const TIER_STYLES: Record<string, string> = {
  TIER_1: "bg-emerald-50 text-emerald-700",
  TIER_2: "bg-blue-50 text-blue-700",
  TIER_3: "bg-amber-50 text-amber-700",
  NOT_TARGET: "bg-gray-100 text-gray-500",
};

interface BuyerTierBadgeProps {
  tier: BuyerTier | null;
}

export default function BuyerTierBadge({ tier }: BuyerTierBadgeProps) {
  if (!tier) {
    return <span className="text-xs text-text-muted italic">미분류</span>;
  }

  return (
    <span
      className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${TIER_STYLES[tier] ?? "bg-gray-100 text-gray-500"}`}
    >
      {BUYER_TIER_LABELS[tier] ?? tier}
    </span>
  );
}
