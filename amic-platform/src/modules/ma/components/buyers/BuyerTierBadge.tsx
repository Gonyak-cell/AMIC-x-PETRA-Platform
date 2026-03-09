import { Badge } from "@/components/ui";

import type { BuyerTier } from "@/modules/ma/types/buyer";
import { BUYER_TIER_LABELS } from "@/modules/ma/constants";

const TIER_STYLES: Record<BuyerTier, string> = {
  TIER_1: "bg-accent-light text-amic-400",
  TIER_2: "bg-amic-50 text-amic-400",
  TIER_3: "bg-amic-100 text-amic-500",
  NOT_TARGET: "bg-bg-cool text-text-secondary",
};

interface BuyerTierBadgeProps {
  tier: BuyerTier | null;
}

export default function BuyerTierBadge({ tier }: BuyerTierBadgeProps) {
  if (!tier) {
    return <span className="text-xs text-text-muted italic">미분류</span>;
  }

  return (
    <Badge className={TIER_STYLES[tier] ?? "bg-bg-cool text-text-secondary"} pill>
      {BUYER_TIER_LABELS[tier] ?? tier}
    </Badge>
  );
}
