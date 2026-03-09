import { useMemo } from "react";
import { Users } from "lucide-react";
import { Badge, EmptyState } from "@/components/ui";
import type { BuyerCandidate } from "@/modules/ma/types/buyer";
import type { BuyerStageSummary } from "@/modules/ma/types/marketing_log";
import { buildStageMap, MARKETING_STAGES } from "@/modules/ma/constants";
import BuyerTierBadge from "./BuyerTierBadge";
import InterestIndicator from "./InterestIndicator";
import MarketingStageTracker from "./MarketingStageTracker";

interface ShortListMasterListProps {
  buyers: BuyerCandidate[];
  overviewData: BuyerStageSummary[];
  selectedBuyerId: string | null;
  onSelectBuyer: (buyerId: string) => void;
  totalBuyerCount: number;
}

export default function ShortListMasterList({
  buyers,
  overviewData,
  selectedBuyerId,
  onSelectBuyer,
  totalBuyerCount,
}: ShortListMasterListProps) {
  const stageMap = useMemo(() => buildStageMap(overviewData), [overviewData]);

  const dropCount = buyers.filter((b) => b.status === "BID_DROPPED").length;
  const activeCount = buyers.length - dropCount;
  const conversionRate =
    totalBuyerCount > 0
      ? Math.round((buyers.length / totalBuyerCount) * 100)
      : 0;

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
        <p className="text-xs text-text-muted mt-0.5">
          {buyers.length}개 후보 (Active {activeCount} / Drop {dropCount})
        </p>
        {totalBuyerCount > 0 && (
          <p className="text-xs font-medium text-accent mt-0.5">
            숏리스트 전환율 {conversionRate}%
          </p>
        )}
      </div>

      <div className="space-y-1 overflow-y-auto" aria-label="Short List 후보 목록">
        {buyers.map((buyer) => {
          const isSelected = selectedBuyerId === buyer.id;
          const stages = stageMap.get(buyer.id);
          const summary = stages ? { buyer_id: buyer.id, stages } as BuyerStageSummary : undefined;
          const isDropped = buyer.status === "BID_DROPPED";
          const completedCount = stages
            ? MARKETING_STAGES.filter((s) => stages[s]).length
            : 0;

          return (
            <button
              key={buyer.id}
              type="button"
              onClick={() => onSelectBuyer(buyer.id)}
              className={`w-full text-left rounded-lg px-3 py-2.5 transition-colors ${
                isSelected
                  ? "bg-accent/5 border-l-2 border-accent"
                  : "hover:bg-gray-50"
              }`}
            >
              <div className="flex items-center gap-2">
                {/* 회사명 + 담당자 */}
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-1.5">
                    <p className={`font-medium text-sm truncate ${isDropped ? "text-text-muted" : ""}`}>
                      {buyer.company_name}
                    </p>
                    {isDropped && (
                      <Badge variant="neutral" className="text-[9px] px-1 py-0">
                        Drop
                      </Badge>
                    )}
                  </div>
                  {buyer.contact_name && (
                    <p className="text-xs text-text-muted truncate">
                      {buyer.contact_name}
                    </p>
                  )}
                </div>

                {/* Tier + Interest + N/6 */}
                <div className="flex items-center gap-1.5 shrink-0">
                  <BuyerTierBadge tier={buyer.tier} />
                  <InterestIndicator tier={buyer.tier} />
                  <span className="text-[10px] text-text-muted">
                    {completedCount}/{MARKETING_STAGES.length}
                  </span>
                </div>
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}
