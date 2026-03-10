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
  const loiCount = overviewData.filter((s) => s.stages.LOI_RECEIVED).length;
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
      label: "LOI 접수",
      value: loiCount,
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
      label: "진행률",
      value: `${avgPct}%`,
      color: "text-accent",
      filter: "all",
    },
  ];

  return (
    <div className="flex items-center gap-2 flex-wrap">
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
              "inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs transition-all cursor-pointer",
              isActive
                ? "bg-accent/10 text-accent border border-accent/30 font-medium"
                : "bg-gray-100 text-text-body border border-transparent hover:bg-gray-200",
            )}
          >
            {card.icon === "drop" && dropCount > 0 && (
              <AlertTriangle className="w-3 h-3 text-negative flex-shrink-0" />
            )}
            <span className="font-medium">{card.label}</span>
            <span className="font-bold tabular-nums">{card.value}</span>
          </button>
        );
      })}
    </div>
  );
}
