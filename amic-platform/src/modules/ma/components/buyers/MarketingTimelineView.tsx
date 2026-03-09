import { Check, ChevronRight } from "lucide-react";
import { EmptyState, Badge } from "@/components/ui";
import BuyerTierBadge from "./BuyerTierBadge";
import InlineLogInput from "./InlineLogInput";
import { MARKETING_STAGES, MARKETING_STAGE_LABELS } from "@/modules/ma/constants";
import type { BuyerCandidate } from "@/modules/ma/types/buyer";
import type {
  BuyerStageSummary,
  MarketingStage,
} from "@/modules/ma/types/marketing_log";

interface MarketingTimelineViewProps {
  buyers: BuyerCandidate[];
  overviewData: BuyerStageSummary[];
  onSelectBuyer: (buyerId: string) => void;
  canWrite: boolean;
  txnId: string;
}

function latestStageIndex(
  stages: Record<MarketingStage, string | null>,
): number {
  for (let i = MARKETING_STAGES.length - 1; i >= 0; i--) {
    if (stages[MARKETING_STAGES[i]]) return i;
  }
  return -1;
}

export default function MarketingTimelineView({
  buyers,
  overviewData,
  onSelectBuyer,
  canWrite,
  txnId,
}: MarketingTimelineViewProps) {
  if (buyers.length === 0) {
    return (
      <EmptyState
        title="Short List가 비어 있습니다"
        description="Long List에서 매수자를 Short List로 승격해주세요."
      />
    );
  }

  const stageMap = new Map(overviewData.map((s) => [s.buyer_id, s.stages]));

  const sorted = [...buyers].sort((a, b) => {
    const aIdx = latestStageIndex(
      stageMap.get(a.id) ?? ({} as Record<MarketingStage, string | null>),
    );
    const bIdx = latestStageIndex(
      stageMap.get(b.id) ?? ({} as Record<MarketingStage, string | null>),
    );
    return bIdx - aIdx;
  });

  return (
    <div>
      <p className="text-xs font-medium text-accent mb-2">Timeline View — 진행률 바 + 카드</p>
      <div className="space-y-3">
      {sorted.map((buyer) => {
        const stages = stageMap.get(buyer.id);
        const currentIdx = stages ? latestStageIndex(stages) : -1;
        const pct = Math.round(
          ((currentIdx + 1) / MARKETING_STAGES.length) * 100,
        );
        const nextStage =
          currentIdx < MARKETING_STAGES.length - 1 ? MARKETING_STAGES[currentIdx + 1] : null;

        return (
          <div
            key={buyer.id}
            className="rounded-dr border border-gray-border bg-white p-3"
          >
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2">
                <span className="font-medium text-sm text-text-dark">
                  {buyer.company_name}
                </span>
                {buyer.tier && <BuyerTierBadge tier={buyer.tier} />}
                {currentIdx >= 0 && (
                  <Badge variant="info" className="text-[10px]">
                    {MARKETING_STAGE_LABELS[MARKETING_STAGES[currentIdx]]}
                  </Badge>
                )}
                {currentIdx >= 0 && (
                  <span className="text-[10px] font-semibold text-accent">
                    {pct}%
                  </span>
                )}
              </div>
              <button
                type="button"
                onClick={() => onSelectBuyer(buyer.id)}
                className="p-1 text-text-muted hover:text-accent transition-colors"
                aria-label={`${buyer.company_name} 상세 보기`}
              >
                <ChevronRight className="h-4 w-4" />
              </button>
            </div>

            {/* Timeline bar */}
            <div className="flex items-center gap-0.5">
              {MARKETING_STAGES.map((stage, idx) => {
                const date = stages?.[stage] ?? null;
                const completed = !!date;
                return (
                  <div key={stage} className="flex-1 flex flex-col items-center">
                    <div
                      className={`h-1.5 w-full rounded-full ${
                        completed
                          ? "bg-accent"
                          : idx <= currentIdx
                            ? "bg-accent/30"
                            : "bg-gray-200"
                      }`}
                    />
                    <span
                      className={`text-[9px] mt-1 ${
                        completed ? "text-accent font-medium" : "text-text-muted"
                      }`}
                    >
                      {date ? date.slice(5) : MARKETING_STAGE_LABELS[stage].slice(0, 2)}
                    </span>
                  </div>
                );
              })}
            </div>

            {/* Inline input for next stage OR completion indicator */}
            {!nextStage && currentIdx >= 0 ? (
              <div className="mt-2 pt-2 border-t border-gray-border flex items-center gap-1 text-accent">
                <Check className="h-3.5 w-3.5" />
                <span className="text-xs font-semibold">모든 단계 완료</span>
              </div>
            ) : (
              canWrite && nextStage && (
                <div className="mt-2 pt-2 border-t border-gray-border">
                  <InlineLogInput
                    txnId={txnId}
                    buyerId={buyer.id}
                    defaultStage={nextStage}
                    compact
                  />
                </div>
              )
            )}
          </div>
        );
      })}
      </div>
    </div>
  );
}
