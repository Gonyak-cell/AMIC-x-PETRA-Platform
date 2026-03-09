import { useMemo } from "react";
import { MARKETING_STAGES, buildStageMap } from "@/modules/ma/constants";
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
  const stageMap = useMemo(() => buildStageMap(overviewData), [overviewData]);

  const dropCount = buyers.filter((b) => b.status === "BID_DROPPED").length;
  const activeCount = buyers.length - dropCount;
  const ndaCount = overviewData.filter((s) => s.stages.NDA_SIGNED).length;
  const targetMeetingCount = overviewData.filter(
    (s) => s.stages.TARGET_MEETING,
  ).length;
  const tier1Count = buyers.filter((b) => b.tier === "TIER_1").length;

  const avgPct = useMemo(() => {
    if (buyers.length === 0) return 0;
    let total = 0;
    for (const b of buyers) {
      const stages = stageMap.get(b.id);
      if (!stages) continue;
      const done = MARKETING_STAGES.filter(
        (s: MarketingStage) => stages[s],
      ).length;
      total += (done / MARKETING_STAGES.length) * 100;
    }
    return Math.round(total / buyers.length);
  }, [buyers, stageMap]);

  const cards = [
    { label: "ACTIVE 후보", value: activeCount, color: "text-text-dark" },
    { label: "DROP", value: dropCount, color: "text-orange-500" },
    { label: "NDA 체결", value: ndaCount, color: "text-amic-400" },
    {
      label: "대상미팅 완료",
      value: targetMeetingCount,
      color: "text-solid-green",
    },
    { label: "TIER 1", value: tier1Count, color: "text-amic-500" },
    { label: "평균 진행률", value: "${avgPct}%", color: "text-amic-300" },
  ];

  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2">
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
