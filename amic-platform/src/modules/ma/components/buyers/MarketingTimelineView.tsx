import { useMemo } from "react";
import { ChevronRight } from "lucide-react";
import { EmptyState, Badge } from "@/components/ui";
import BuyerTierBadge from "./BuyerTierBadge";
import InlineLogInput from "./InlineLogInput";
import { MARKETING_STAGES, MARKETING_STAGE_LABELS, buildStageMap } from "@/modules/ma/constants";
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
  stages: Partial<Record<MarketingStage, string | null>>,
): number {
  for (let i = MARKETING_STAGES.length - 1; i >= 0; i--) {
    if (stages[MARKETING_STAGES[i]]) return i;
  }
  return -1;
}

/** IOI_RECEIVED 단계 특수 컬러 */
const IOI_STAGE: MarketingStage = "IOI_RECEIVED";

export default function MarketingTimelineView({
  buyers,
  overviewData,
  onSelectBuyer,
  canWrite,
  txnId,
}: MarketingTimelineViewProps) {
  const stageMap = useMemo(() => buildStageMap(overviewData), [overviewData]);

  const sorted = useMemo(
    () =>
      [...buyers].sort((a, b) => {
        const aIdx = latestStageIndex(
          stageMap.get(a.id) ?? ({} as Partial<Record<MarketingStage, string | null>>),
        );
        const bIdx = latestStageIndex(
          stageMap.get(b.id) ?? ({} as Partial<Record<MarketingStage, string | null>>),
        );
        return bIdx - aIdx;
      }),
    [buyers, stageMap],
  );

  if (buyers.length === 0) {
    return (
      <EmptyState
        title="Short List가 비어 있습니다"
        description="Long List에서 매수자를 Short List로 승격해주세요."
      />
    );
  }

  return (
    <div>
      <p className="text-xs font-medium text-accent mb-2">
        TIMELINE VIEW — 수직 연대기
      </p>
      <div className="space-y-4">
        {sorted.map((buyer) => {
          const stages = stageMap.get(buyer.id);
          const currentIdx = stages ? latestStageIndex(stages) : -1;
          const pct =
            currentIdx >= 0
              ? Math.round(((currentIdx + 1) / MARKETING_STAGES.length) * 100)
              : 0;

          // 완료된 단계만 수집
          const completedStages: { stage: MarketingStage; date: string }[] = [];
          if (stages) {
            for (const s of MARKETING_STAGES) {
              const date = stages[s];
              if (date) completedStages.push({ stage: s, date });
            }
          }

          // 다음 단계 결정
          const nextStage =
            currentIdx < MARKETING_STAGES.length - 1
              ? MARKETING_STAGES[currentIdx + 1]
              : null;

          return (
            <div
              key={buyer.id}
              className="rounded-dr border border-gray-border bg-white"
            >
              {/* Card header */}
              <div className="flex items-center justify-between px-4 py-3 border-b border-gray-border">
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
                    <span className="text-xs font-semibold text-accent">
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

              {/* Vertical timeline */}
              <div className="px-4 py-3">
                {completedStages.length === 0 ? (
                  <p className="text-xs text-text-muted py-2">
                    아직 진행된 단계가 없습니다.
                  </p>
                ) : (
                  <div className="relative ml-1.5">
                    {completedStages.map((item, idx) => {
                      const isIOI = item.stage === IOI_STAGE;
                      const isLast = idx === completedStages.length - 1;
                      const ioiAmount = isIOI ? buyer.ioi_value : null;

                      return (
                        <div key={item.stage} className="flex items-start gap-3 relative">
                          {/* Vertical line + dot */}
                          <div className="flex flex-col items-center">
                            <div
                              className={`w-2.5 h-2.5 rounded-full flex-shrink-0 mt-1 ${
                                isIOI ? "bg-orange-400" : "bg-accent"
                              }`}
                            />
                            {!isLast && (
                              <div className="w-px flex-1 min-h-[20px] bg-gray-200" />
                            )}
                          </div>
                          {/* Date + stage label */}
                          <div className="pb-3">
                            <span className="text-sm text-text-muted">
                              {item.date}
                            </span>
                            <span
                              className={`text-sm font-semibold ml-2 ${
                                isIOI ? "text-orange-500" : "text-text-dark"
                              }`}
                            >
                              {MARKETING_STAGE_LABELS[item.stage]}
                              {ioiAmount && ` (${ioiAmount})`}
                            </span>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>

              {/* Inline log input */}
              {canWrite && nextStage && (
                <div className="px-4 pb-3">
                  <InlineLogInput
                    txnId={txnId}
                    buyerId={buyer.id}
                    defaultStage={nextStage}
                  />
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
