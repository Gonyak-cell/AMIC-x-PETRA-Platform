import { ChevronRight } from "lucide-react";
import { EmptyState } from "@/components/ui";
import BuyerTierBadge from "./BuyerTierBadge";
import InlineLogInput from "./InlineLogInput";
import { MARKETING_STAGES, MARKETING_STAGE_LABELS } from "@/modules/ma/constants";
import type { BuyerCandidate } from "@/modules/ma/types/buyer";
import type {
  BuyerStageSummary,
  MarketingStage,
} from "@/modules/ma/types/marketing_log";

interface MarketingKanbanViewProps {
  buyers: BuyerCandidate[];
  overviewData: BuyerStageSummary[];
  onSelectBuyer: (buyerId: string) => void;
  canWrite: boolean;
  txnId: string;
}

function latestStage(
  stages: Record<MarketingStage, string | null>,
): MarketingStage {
  for (let i = MARKETING_STAGES.length - 1; i >= 0; i--) {
    if (stages[MARKETING_STAGES[i]]) return MARKETING_STAGES[i];
  }
  return "IDENTIFIED";
}

export default function MarketingKanbanView({
  buyers,
  overviewData,
  onSelectBuyer,
  canWrite,
  txnId,
}: MarketingKanbanViewProps) {
  if (buyers.length === 0) {
    return (
      <EmptyState
        title="Short List가 비어 있습니다"
        description="Long List에서 매수자를 Short List로 승격해주세요."
      />
    );
  }

  const stageMap = new Map(overviewData.map((s) => [s.buyer_id, s.stages]));

  // Group buyers by their latest completed stage
  const columns = new Map<MarketingStage, BuyerCandidate[]>();
  for (const stage of MARKETING_STAGES) {
    columns.set(stage, []);
  }
  for (const buyer of buyers) {
    const stages = stageMap.get(buyer.id);
    const current = stages ? latestStage(stages) : "IDENTIFIED";
    columns.get(current)?.push(buyer);
  }

  return (
    <div className="flex gap-3 overflow-x-auto pb-2">
      {MARKETING_STAGES.map((stage) => {
        const stageBuyers = columns.get(stage) ?? [];
        const nextStageIdx = MARKETING_STAGES.indexOf(stage) + 1;
        const nextStage =
          nextStageIdx < MARKETING_STAGES.length ? MARKETING_STAGES[nextStageIdx] : null;

        return (
          <div
            key={stage}
            className="flex-shrink-0 w-56 bg-bg-cool rounded-dr border border-gray-border"
          >
            {/* Column header */}
            <div className="px-3 py-2 border-b border-gray-border bg-white rounded-t-dr">
              <div className="flex items-center justify-between">
                <span className="text-xs font-medium text-text-dark">
                  {MARKETING_STAGE_LABELS[stage]}
                </span>
                <span className="text-[10px] text-text-muted bg-bg-cool px-1.5 py-0.5 rounded-full">
                  {stageBuyers.length}
                </span>
              </div>
            </div>

            {/* Cards */}
            <div className="p-2 space-y-2 min-h-[100px]">
              {stageBuyers.map((buyer) => (
                <div
                  key={buyer.id}
                  className="bg-white rounded border border-gray-border p-2 hover:shadow-sm transition-shadow"
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-xs font-medium text-text-dark truncate max-w-[140px]">
                      {buyer.company_name}
                    </span>
                    <button
                      type="button"
                      onClick={() => onSelectBuyer(buyer.id)}
                      className="p-0.5 text-text-muted hover:text-accent transition-colors"
                      aria-label="상세 보기"
                    >
                      <ChevronRight className="h-3 w-3" />
                    </button>
                  </div>
                  {buyer.tier && <BuyerTierBadge tier={buyer.tier} />}
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
                <p className="text-[10px] text-text-muted text-center py-4">
                  없음
                </p>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}
