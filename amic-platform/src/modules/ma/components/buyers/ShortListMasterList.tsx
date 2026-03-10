import { useMemo } from "react";
import { Users } from "lucide-react";
import { cn } from "@/lib/cn";
import { Badge, EmptyState } from "@/components/ui";
import type { BuyerCandidate } from "@/modules/ma/types/buyer";
import type { MarketingStage } from "@/modules/ma/types/marketing_log";
import {
  MARKETING_STAGES,
  MARKETING_STAGE_LABELS,
  countCompletedStages,
} from "@/modules/ma/constants";
import BuyerTierBadge from "./BuyerTierBadge";
import InterestIndicator from "./InterestIndicator";

interface ShortListMasterListProps {
  buyers: BuyerCandidate[];
  stageMap: Map<string, Partial<Record<MarketingStage, string | null>>>;
  selectedBuyerId: string | null;
  onSelectBuyer: (buyerId: string) => void;
  totalBuyerCount: number;
}

const TIER_ORDER = ["TIER_1", "TIER_2", "TIER_3", null] as const;
const TIER_GROUP_LABELS: Record<string, string> = {
  TIER_1: "Tier 1",
  TIER_2: "Tier 2",
  TIER_3: "Tier 3",
  none: "미분류",
};

export default function ShortListMasterList({
  buyers,
  stageMap,
  selectedBuyerId,
  onSelectBuyer,
  totalBuyerCount,
}: ShortListMasterListProps) {
  const dropCount = buyers.filter((b) => b.status === "BID_DROPPED").length;
  const activeCount = buyers.length - dropCount;
  const conversionRate =
    totalBuyerCount > 0
      ? Math.round((buyers.length / totalBuyerCount) * 100)
      : 0;

  const tierGroups = useMemo(() => {
    const groups: { tier: string; label: string; items: BuyerCandidate[] }[] =
      [];
    for (const t of TIER_ORDER) {
      const filtered = buyers.filter((b) => (b.tier ?? null) === t);
      if (filtered.length > 0) {
        groups.push({
          tier: t ?? "none",
          label: TIER_GROUP_LABELS[t ?? "none"],
          items: filtered,
        });
      }
    }
    return groups;
  }, [buyers]);

  if (buyers.length === 0) {
    return (
      <EmptyState
        icon={Users}
        title="Short List 후보 없음"
        description="Long List에서 후보를 승격하세요."
      />
    );
  }

  return (
    <div className="space-y-1">
      {/* Header */}
      <div className="mb-3">
        <h3 className="text-base font-semibold text-text-dark">Short List</h3>
        <p className="text-xs text-gray-500 mt-0.5">
          {buyers.length}개 후보 (Active {activeCount} / Drop {dropCount})
        </p>
        {totalBuyerCount > 0 && (
          <p className="text-xs font-medium text-accent mt-0.5">
            숏리스트 전환율 {conversionRate}%
          </p>
        )}
      </div>

      <div
        className="space-y-3 overflow-y-auto"
        role="region"
        aria-label="Short List 후보 목록"
      >
        {tierGroups.map((group) => (
          <div key={group.tier}>
            {/* Tier 구분선 */}
            <div className="flex items-center gap-2 px-2 mb-1">
              <div className="h-px flex-1 bg-gray-200" />
              <span className="text-[10px] font-semibold text-gray-500 uppercase tracking-wider">
                {group.label}
              </span>
              <div className="h-px flex-1 bg-gray-200" />
            </div>

            <div className="space-y-1">
              {group.items.map((buyer) => {
                const isSelected = selectedBuyerId === buyer.id;
                const stages = stageMap.get(buyer.id);
                const isDropped = buyer.status === "BID_DROPPED";
                const completedCount = countCompletedStages(stages);

                // 최근 완료 단계 (툴팁용)
                const latestStageLabel = stages
                  ? (MARKETING_STAGES.filter((s: MarketingStage) => stages[s])
                      .map((s) => MARKETING_STAGE_LABELS[s])
                      .pop() ?? null)
                  : null;

                const tooltipText = latestStageLabel
                  ? `최근 단계: ${latestStageLabel}`
                  : "아직 진행된 단계 없음";

                const ariaLabel = `${buyer.company_name}${buyer.tier ? `, ${TIER_GROUP_LABELS[buyer.tier]}` : ""}, 진행 ${completedCount}/${MARKETING_STAGES.length}${isDropped ? ", Drop" : ""}`;

                return (
                  <button
                    key={buyer.id}
                    type="button"
                    data-testid={`buyer-${buyer.id}`}
                    onClick={() => !isDropped && onSelectBuyer(buyer.id)}
                    title={tooltipText}
                    aria-label={ariaLabel}
                    aria-disabled={isDropped || undefined}
                    tabIndex={isDropped ? -1 : undefined}
                    className={cn(
                      "w-full text-left rounded-dr px-3 py-2.5 transition-colors",
                      isSelected
                        ? "bg-accent/10 border-l-[3px] border-accent shadow-sm"
                        : "hover:bg-gray-50",
                      isDropped && "opacity-[0.55] grayscale cursor-default hover:opacity-70",
                    )}
                  >
                    <div className="flex items-center gap-2">
                      {/* 회사명 + 담당자 */}
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center gap-1.5">
                          <p
                            className={`font-medium text-sm truncate ${
                              isDropped ? "text-gray-500 line-through" : ""
                            }`}
                          >
                            {buyer.company_name}
                          </p>
                          {isDropped && (
                            <Badge
                              variant="neutral"
                              className="text-[9px] px-1 py-0"
                            >
                              Drop
                            </Badge>
                          )}
                        </div>
                        {buyer.contact_name && (
                          <p className="text-xs text-gray-500 truncate">
                            {buyer.contact_name}
                          </p>
                        )}
                      </div>

                      {/* Tier + Interest + N/6 */}
                      <div className="flex items-center gap-1.5 shrink-0">
                        <BuyerTierBadge tier={buyer.tier} />
                        <InterestIndicator tier={buyer.tier} />
                        <span className="text-[10px] text-gray-500">
                          {completedCount}/{MARKETING_STAGES.length}
                        </span>
                      </div>
                    </div>
                  </button>
                );
              })}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
