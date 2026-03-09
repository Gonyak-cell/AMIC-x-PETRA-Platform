import { MARKETING_STAGES } from "@/modules/ma/constants";
import type { BuyerCandidate } from "@/modules/ma/types/buyer";
import type {
  BuyerStageSummary,
  MarketingStage,
} from "@/modules/ma/types/marketing_log";

interface ShortListSummaryBarProps {
  buyers: BuyerCandidate[];
  overviewData: BuyerStageSummary[];
}

export default function ShortListSummaryBar({
  buyers,
  overviewData,
}: ShortListSummaryBarProps) {
  const stageMap = new Map(overviewData.map((s) => [s.buyer_id, s.stages]));

  const ndaCount = overviewData.filter((s) => s.stages.NDA_SIGNED).length;
  const targetMeetingCount = overviewData.filter(
    (s) => s.stages.TARGET_MEETING,
  ).length;
  const tier1Count = buyers.filter((b) => b.tier === "TIER_1").length;

  const avgPct =
    buyers.length > 0
      ? Math.round(
          buyers.reduce((sum, b) => {
            const stages = stageMap.get(b.id);
            if (!stages) return sum;
            const done = MARKETING_STAGES.filter(
              (s: MarketingStage) => stages[s],
            ).length;
            return sum + (done / MARKETING_STAGES.length) * 100;
          }, 0) / buyers.length,
        )
      : 0;

  const cards = [
    { label: "전체 후보", value: buyers.length, color: "text-accent" },
    { label: "NDA 체결", value: ndaCount, color: "text-blue-600" },
    { label: "대상미팅 완료", value: targetMeetingCount, color: "text-emerald-600" },
    { label: "Tier 1", value: tier1Count, color: "text-amber-600" },
    { label: "평균 진행률", value: `${avgPct}%`, color: "text-violet-600" },
  ];

  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-2">
      {cards.map((card) => (
        <div
          key={card.label}
          className="rounded-dr border border-gray-border bg-white px-3 py-2 text-center"
        >
          <p className={`text-lg font-bold ${card.color}`}>{card.value}</p>
          <p className="text-[10px] text-text-muted">{card.label}</p>
        </div>
      ))}
    </div>
  );
}
