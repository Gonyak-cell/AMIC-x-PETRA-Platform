import { useMemo } from "react";
import { AlertTriangle } from "lucide-react";
import { cn } from "@/lib/cn";
import { MARKETING_STAGES, countCompletedStages } from "@/modules/ma/constants";
import type { BuyerCandidate } from "@/modules/ma/types/buyer";
import type {
  BuyerStageSummary,
  MarketingStage,
} from "@/modules/ma/types/marketing_log";
import type { KpiFilter } from "./ShortListOverview";

interface ShortListSummaryBarProps {
  buyers: BuyerCandidate[];
  overviewData: BuyerStageSummary[];
  stageMap: Map<string, Partial<Record<MarketingStage, string | null>>>;
  activeFilter: KpiFilter;
  onFilterChange: (filter: KpiFilter) => void;
}

export default function ShortListSummaryBar({
  buyers,
  overviewData,
  stageMap,
  activeFilter,
  onFilterChange,
}: ShortListSummaryBarProps) {
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
    let counted = 0;
    for (const b of buyers) {
      const stages = stageMap.get(b.id);
      if (!stages) continue;
      counted++;
      const done = countCompletedStages(stages);
      total += (done / MARKETING_STAGES.length) * 100;
    }
    return counted > 0 ? Math.round(total / counted) : 0;
  }, [buyers, stageMap]);

  const cards: {
    label: string;
    value: number | string;
    color: string;
    filter: KpiFilter;
    icon?: "drop";
    progressPct?: number;
  }[] = [
    {
      label: "Active 후보",
      value: activeCount,
      color: "text-text-dark",
      filter: "active",
    },
    {
      label: "Drop",
      value: dropCount,
      color: "text-negative",
      filter: "drop",
      icon: "drop",
    },
    {
      label: "NDA 체결",
      value: ndaCount,
      color: "text-amic-400",
      filter: "nda",
    },
    {
      label: "대상미팅 완료",
      value: targetMeetingCount,
      color: "text-solid-green",
      filter: "target_meeting",
    },
    {
      label: "Tier 1",
      value: tier1Count,
      color: "text-amic-500",
      filter: "tier1",
    },
    {
      label: "평균 진행률",
      value: `${avgPct}%`,
      color: "text-accent",
      filter: "all",
      progressPct: avgPct,
    },
  ];

  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2">
      {cards.map((card) => {
        const isActive = activeFilter === card.filter && card.filter !== "all";
        return (
          <button
            key={card.filter}
            type="button"
            data-testid={`kpi-${card.filter}`}
            aria-label={`${card.label}: ${card.value}`}
            onClick={() => onFilterChange(isActive ? "all" : card.filter)}
            className={cn(
              "rounded-dr border px-3 py-2.5 text-center transition-all cursor-pointer",
              isActive
                ? "border-accent bg-accent/5 ring-1 ring-accent/30"
                : "border-gray-300 bg-white hover:border-gray-400 hover:shadow-sm",
            )}
          >
            <p className={`text-2xl font-bold leading-tight ${card.color}`}>
              {card.icon === "drop" && dropCount > 0 && (
                <AlertTriangle className="inline-block w-4 h-4 mr-1 -mt-0.5" />
              )}
              {card.value}
            </p>
            {card.progressPct != null && (
              <div className="mt-1.5 h-1.5 w-full rounded-full bg-gray-200" role="progressbar" aria-valuenow={card.progressPct} aria-valuemin={0} aria-valuemax={100}>
                <div
                  className="h-full rounded-full bg-accent transition-all duration-500"
                  style={{ width: `${Math.min(card.progressPct, 100)}%` }}
                />
              </div>
            )}
            <p className="mt-1 text-xs text-gray-500">{card.label}</p>
          </button>
        );
      })}
    </div>
  );
}
