import type { BuyerTier } from "@/modules/ma/types/buyer";

interface InterestIndicatorProps {
  tier: BuyerTier | null;
}

const tierConfig: Record<string, { className: string; title: string }> = {
  TIER_1: { className: "bg-accent", title: "High Interest" },
  TIER_2: { className: "bg-caution", title: "Mid Interest" },
  TIER_3: { className: "bg-gray-300", title: "Low Interest" },
};

export default function InterestIndicator({ tier }: InterestIndicatorProps) {
  const config = tier ? tierConfig[tier] : null;

  return (
    <span
      className={`inline-block h-2.5 w-2.5 rounded-full ${
        config ? config.className : "border border-gray-300"
      }`}
      title={config ? config.title : "Not Targeted"}
    />
  );
}
