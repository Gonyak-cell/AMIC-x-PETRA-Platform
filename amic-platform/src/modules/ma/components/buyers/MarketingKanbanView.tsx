import { useMemo } from "react";
import { ChevronRight } from "lucide-react";
import { EmptyState } from "@/components/ui";
import BuyerTierBadge from "./BuyerTierBadge";
import InterestIndicator from "./InterestIndicator";
import InlineLogInput from "./InlineLogInput";
import {
  MARKETING_STAGES,
  MARKETING_STAGE_LABELS,
  latestCompletedStageIndex,
} from "@/modules/ma/constants";
import type { BuyerCandidate } from "@/modules/ma/types/buyer";
import type { MarketingStage } from "@/modules/ma/types/marketing_log";

interface MarketingKanbanViewProps {
  buyers: BuyerCandidate[];
  stageMap: Map<string, Partial<Record<MarketingStage, string | null>>>;
  onSelectBuyer: (buyerId: string) => void;
  canWrite: boolean;
  txnId: string;
}

export default function MarketingKanbanView({
  buyers,
  stageMap,
  onSelectBuyer,
  canWrite,
  txnId,
}: MarketingKanbanViewProps) {
  const columns = useMemo(() => {
    const cols = new Map<MarketingStage, BuyerCandidate[]>();
    for (const stage of MARKETING_STAGES) {
      cols.set(stage, []);
    }
    for (const buyer of buyers) {
      const stages = stageMap.get(buyer.id);
      const idx = stages ? latestCompletedStageIndex(stages) : -1;
      const current = idx >= 0 ? MARKETING_STAGES[idx] : "IDENTIFIED";
      cols.get(current)?.push(buyer);
    }
    return cols;
  }, [buyers, stageMap]);

  if (buyers.length === 0) {
    return (
      <EmptyState
        title="Short List가 비어 있습니다"
        description="Long List에서 매수자를 Short List로 승격해주세요."
      />
    );
  }

  return (
    <div aria-label="단계별 바이어 현황">
      <p className="text-xs font-medium text-accent mb-2">
        Kanban View — 단계별 칸반 보드
      </p>
      <div
        className="flex gap-3 overflow-x-auto pb-2"
        tabIndex={0}
        role="region"
        aria-label="단계별 바이어 현황 스크롤"
        data-testid="marketing-kanban"
      >
        {MARKETING_STAGES.map((stage) => {
          const stageBuyers = columns.get(stage) ?? [];
          const nextStageIdx = MARKETING_STAGES.indexOf(stage) + 1;
          const nextStage =
            nextStageIdx < MARKETING_STAGES.length
              ? MARKETING_STAGES[nextStageIdx]
              : null;

          return (
            <div
              key={stage}
              role="group"
              aria-label={MARKETING_STAGE_LABELS[stage]}
              className="min-w-52 flex-1 max-w-72 bg-bg-cool rounded-dr border border-gray-border"
            >
              {/* Column header */}
              <div className="px-3 py-2 border-b border-gray-border bg-white rounded-t-dr">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-medium text-text-dark">
                    {MARKETING_STAGE_LABELS[stage]}
                  </span>
                  <span className="text-[10px] text-gray-500 bg-bg-cool px-1.5 py-0.5 rounded-full">
                    {stageBuyers.length}
                  </span>
                </div>
              </div>

              {/* Cards */}
              <div className="p-2 space-y-2 min-h-[100px]">
                {stageBuyers.map((buyer) => (
                  <div
                    key={buyer.id}
                    className="bg-white rounded border border-gray-border p-2 hover:border-accent/30 hover:shadow-sm transition-all"
                  >
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-xs font-medium text-text-dark truncate max-w-[140px]">
                        {buyer.company_name}
                      </span>
                      <button
                        type="button"
                        onClick={() => onSelectBuyer(buyer.id)}
                        className="p-2 min-w-[44px] min-h-[44px] flex items-center justify-center text-gray-500 hover:text-accent transition-colors"
                        aria-label={`${buyer.company_name} 상세 보기`}
                      >
                        <ChevronRight className="h-4 w-4" />
                      </button>
                    </div>
                    {buyer.contact_name && (
                      <p className="text-[10px] text-gray-500 mb-1 truncate">
                        {buyer.contact_name}
                      </p>
                    )}
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-1.5">
                        {buyer.tier && <BuyerTierBadge tier={buyer.tier} />}
                        {buyer.tier && <InterestIndicator tier={buyer.tier} />}
                      </div>
                      {stageMap.get(buyer.id)?.[stage] && (
                        <span className="text-[10px] text-gray-500">
                          {stageMap.get(buyer.id)?.[stage]}
                        </span>
                      )}
                    </div>
                    {canWrite && nextStage && (
                      <div className="mt-1.5 pt-1.5 border-t border-gray-border">
                        <InlineLogInput
                          txnId={txnId}
                          buyerId={buyer.id}
                          defaultStage={nextStage}
                          compact
                        />
                      </div>
                    )}
                  </div>
                ))}
                {stageBuyers.length === 0 && (
                  <p className="text-[10px] text-gray-500 text-center py-4">
                    없음
                  </p>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
