import { Badge } from "@/components/ui";
import type { BadgeVariant } from "@/components/ui/Badge";
import type { BuyerTier } from "@/modules/ma/types/buyer";
import { BUYER_TIER_LABELS } from "@/modules/ma/constants";

const TIER_VARIANTS: Record<string, BadgeVariant> = {
  TIER_1: "success",
  TIER_2: "info",
  TIER_3: "warning",
  NOT_TARGET: "neutral",
};

interface BuyerTierBadgeProps {
  tier: BuyerTier | null;
}

export default function BuyerTierBadge({ tier }: BuyerTierBadgeProps) {
  if (!tier) {
    return <span className="text-xs text-text-muted italic">미분류</span>;
  }

  return (
    <Badge variant={TIER_VARIANTS[tier] ?? "neutral"} pill>
      {BUYER_TIER_LABELS[tier] ?? tier}
    </Badge>
  );
}
