import { useMemo } from "react";
import { ChevronRight } from "lucide-react";
import { EmptyState, Badge } from "@/components/ui";
import BuyerTierBadge from "./BuyerTierBadge";
import InlineLogInput from "./InlineLogInput";
import {
  MARKETING_STAGES,
  MARKETING_STAGE_LABELS,
  latestCompletedStageIndex,
} from "@/modules/ma/constants";
import type { BuyerCandidate } from "@/modules/ma/types/buyer";
import type { MarketingStage } from "@/modules/ma/types/marketing_log";

interface MarketingTimelineViewProps {
  buyers: BuyerCandidate[];
  stageMap: Map<string, Partial<Record<MarketingStage, string | null>>>;
  onSelectBuyer: (buyerId: string) => void;
  canWrite: boolean;
  txnId: string;
}

/** 두 날짜(YYYY-MM-DD) 사이 일수 차이 */
function daysBetween(a: string, b: string): number | null {
  const da = new Date(a);
  const db = new Date(b);
  if (isNaN(da.getTime()) || isNaN(db.getTime())) return null;
  return Math.round((db.getTime() - da.getTime()) / (1000 * 60 * 60 * 24));
}

const MILESTONE_STAGES = new Set<MarketingStage>([
  "NDA_SIGNED",
  "TARGET_MEETING",
]);

export default function MarketingTimelineView({
  buyers,
  stageMap,
  onSelectBuyer,
  canWrite,
  txnId,
}: MarketingTimelineViewProps) {
  const sorted = useMemo(
    () =>
      [...buyers].sort((a, b) => {
        const aIdx = latestCompletedStageIndex(
          stageMap.get(a.id) ??
            ({} as Partial<Record<MarketingStage, string | null>>),
        );
        const bIdx = latestCompletedStageIndex(
          stageMap.get(b.id) ??
            ({} as Partial<Record<MarketingStage, string | null>>),
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
      <p className="sr-only">
        각 매수 후보자별 마케팅 단계 진행 현황을 시간순으로 표시합니다. 단계:
        후보 발굴, 이메일 발송, 전화 접촉, 자문사 미팅, NDA 체결, 대상 미팅.
      </p>
      <div className="space-y-4" data-testid="marketing-timeline">
        {sorted.map((buyer) => {
          const stages = stageMap.get(buyer.id);
          const currentIdx = stages ? latestCompletedStageIndex(stages) : -1;
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
                  className="p-2 min-w-[44px] min-h-[44px] flex items-center justify-center text-gray-500 hover:text-accent transition-colors"
                  aria-label={`${buyer.company_name} 상세 보기`}
                >
                  <ChevronRight className="h-4 w-4" />
                </button>
              </div>

              {/* Vertical timeline */}
              <div className="px-4 py-3">
                {completedStages.length === 0 ? (
                  <p className="text-xs text-gray-500 py-2">
                    아직 진행된 단계가 없습니다.
                  </p>
                ) : (
                  <div className="relative ml-1.5">
                    {completedStages.map((item, idx) => {
                      const isMilestone = MILESTONE_STAGES.has(item.stage);
                      const isLast = idx === completedStages.length - 1;
                      const prevDate =
                        idx > 0 ? completedStages[idx - 1].date : null;
                      const elapsed = prevDate
                        ? daysBetween(prevDate, item.date)
                        : null;

                      return (
                        <div
                          key={item.stage}
                          className="flex items-start gap-3 relative"
                        >
                          {/* Vertical line + dot */}
                          <div className="flex flex-col items-center">
                            <div
                              className={`rounded-full flex-shrink-0 mt-1 ${
                                isMilestone
                                  ? "w-3.5 h-3.5 bg-accent ring-2 ring-accent/30"
                                  : "w-2.5 h-2.5 bg-accent"
                              }`}
                            />
                            {!isLast && (
                              <div className="w-px flex-1 min-h-[20px] bg-gray-200 relative">
                                {elapsed != null && elapsed > 0 && (
                                  <span className="absolute left-3 top-1/2 -translate-y-1/2 text-[9px] text-gray-500 whitespace-nowrap">
                                    {elapsed}일
                                  </span>
                                )}
                              </div>
                            )}
                          </div>
                          {/* Date + stage label */}
                          <div className="pb-3">
                            <span className="text-sm text-gray-500">
                              {item.date}
                            </span>
                            <span className="text-sm font-semibold ml-2 text-text-dark">
                              {MARKETING_STAGE_LABELS[item.stage]}
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
