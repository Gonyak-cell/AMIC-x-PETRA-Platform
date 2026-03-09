import { useMemo } from "react";
import { Users } from "lucide-react";
import { EmptyState } from "@/components/ui";
import type { BuyerCandidate } from "@/modules/ma/types/buyer";
import type { BuyerStageSummary } from "@/modules/ma/types/marketing_log";
import { buildStageMap } from "@/modules/ma/constants";
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
      <p className="text-xs text-text-muted mb-2">
        {buyers.length}개 후보
        {totalBuyerCount > 0 && (
          <span className="ml-2 text-text-secondary">
            숏리스트 전환율 {Math.round((buyers.length / totalBuyerCount) * 100)}%
          </span>
        )}
      </p>

      <div className="space-y-1 overflow-y-auto" aria-label="Short List 후보 목록">
        {buyers.map((buyer) => {
          const isSelected = selectedBuyerId === buyer.id;
          const stages = stageMap.get(buyer.id);
          const summary = stages ? { buyer_id: buyer.id, stages } as BuyerStageSummary : undefined;

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
              <div className="flex items-center justify-between gap-3">
                {/* 좌: 회사명 + 담당자 */}
                <div className="min-w-0 flex-1">
                  <p className="font-medium text-sm truncate">
                    {buyer.company_name}
                  </p>
                  {buyer.contact_name && (
                    <p className="text-xs text-text-muted truncate">
                      {buyer.contact_name}
                    </p>
                  )}
                </div>

                {/* 중: Tier 배지 + 관심도 */}
                <div className="flex items-center gap-2 shrink-0">
                  <BuyerTierBadge tier={buyer.tier} />
                  <InterestIndicator tier={buyer.tier} />
                </div>

                {/* 우: Stage Tracker */}
                {summary && (
                  <div className="shrink-0">
                    <MarketingStageTracker compact summary={summary} />
                  </div>
                )}
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}
