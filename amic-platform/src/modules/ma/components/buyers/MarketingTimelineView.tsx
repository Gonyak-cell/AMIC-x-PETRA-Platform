import { useMemo } from "react";
import { ChevronRight } from "lucide-react";
import { EmptyState, Badge } from "@/components/ui";
import BuyerTierBadge from "./BuyerTierBadge";
import InlineLogInput from "./InlineLogInput";
import TimelineMeetingCard from "./TimelineMeetingCard";
import InlineMeetingForm from "./InlineMeetingForm";
import {
  MARKETING_STAGES,
  MARKETING_STAGE_LABELS,
  latestCompletedStageIndex,
} from "@/modules/ma/constants";
import { useMeetingLogs } from "@/modules/ma/hooks/useMeetingLogs";
import { buildTimelineItems } from "@/modules/ma/utils/timelineItems";
import type { BuyerCandidate } from "@/modules/ma/types/buyer";
import type { MarketingStage } from "@/modules/ma/types/marketing_log";
import type { MeetingLog } from "@/modules/ma/types/meeting_log";

interface MarketingTimelineViewProps {
  buyers: BuyerCandidate[];
  stageMap: Map<string, Partial<Record<MarketingStage, string | null>>>;
  onSelectBuyer: (buyerId: string) => void;
  canWrite: boolean;
  txnId: string;
}

const MILESTONE_STAGES = new Set<MarketingStage>([
  "NDA_SIGNED",
  "TARGET_MEETING",
  "CIM_SENT",
  "DD_STARTED",
]);

export default function MarketingTimelineView({
  buyers,
  stageMap,
  onSelectBuyer,
  canWrite,
  txnId,
}: MarketingTimelineViewProps) {
  /* 트랜잭션 전체 MARKETING 미팅을 1회 fetch (N+1 방지) */
  const { data: meetingData, isError: meetingError } = useMeetingLogs(txnId, {
    meetingPhase: "MARKETING",
  });

  /* buyer_id별 미팅 로그 그룹핑 */
  const meetingsByBuyer = useMemo(() => {
    const map = new Map<string, MeetingLog[]>();
    if (!meetingData?.items) return map;
    for (const log of meetingData.items) {
      if (!log.buyer_id) continue;
      const list = map.get(log.buyer_id);
      if (list) {
        list.push(log);
      } else {
        map.set(log.buyer_id, [log]);
      }
    }
    return map;
  }, [meetingData?.items]);

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
      {meetingError && (
        <p className="text-xs text-amber-600 bg-amber-50 border border-amber-200 rounded px-3 py-1.5 mb-2">
          미팅 데이터를 불러오지 못했습니다.
        </p>
      )}
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

          // 미완료 단계 수집
          const completedSet = new Set(completedStages.map((c) => c.stage));
          const pendingStages = MARKETING_STAGES.filter(
            (s) => !completedSet.has(s),
          );

          // 다음 단계 결정
          const nextStage =
            currentIdx < MARKETING_STAGES.length - 1
              ? MARKETING_STAGES[currentIdx + 1]
              : null;

          // 이 매수자의 미팅 로그
          const buyerMeetings = meetingsByBuyer.get(buyer.id) ?? [];

          // 단계 + 미팅을 날짜순 병합
          const timelineItems = buildTimelineItems(
            completedStages,
            buyerMeetings,
          );

          return (
            <div
              key={buyer.id}
              className="rounded-lg border border-gray-border bg-white"
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
                    <span
                      className="text-xs font-semibold text-accent"
                      role="progressbar"
                      aria-valuenow={pct}
                      aria-valuemin={0}
                      aria-valuemax={100}
                      aria-label={`${buyer.company_name} 마케팅 진행률 ${pct}%`}
                    >
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
                {completedStages.length === 0 &&
                buyerMeetings.length === 0 ? (
                  <p className="text-xs text-gray-500 py-2">
                    아직 진행된 단계가 없습니다.
                  </p>
                ) : (
                  <div className="relative ml-1.5" aria-label="마케팅 진행 타임라인" role="list">
                    {/* 완료 단계 + 미팅 통합 렌더링 */}
                    {timelineItems.map((item, idx) => {
                      const isLastItem =
                        idx === timelineItems.length - 1 &&
                        pendingStages.length === 0;

                      if (item.type === "stage") {
                        const isMilestone = MILESTONE_STAGES.has(item.stage);

                        return (
                          <div
                            key={`stage-${item.stage}`}
                            className="flex items-start gap-3 relative"
                          >
                            <div className="flex flex-col items-center">
                              <div
                                className={`rounded-full flex-shrink-0 mt-1 ${
                                  isMilestone
                                    ? "w-3.5 h-3.5 bg-accent ring-2 ring-accent/30"
                                    : "w-2.5 h-2.5 bg-accent"
                                }`}
                              />
                              {!isLastItem && (
                                <div className="w-px flex-1 min-h-[20px] bg-gray-200 relative">
                                  {item.elapsed != null && item.elapsed > 0 && (
                                    <span className="absolute left-3 top-1/2 -translate-y-1/2 text-[9px] text-gray-500 whitespace-nowrap">
                                      {item.elapsed}일
                                    </span>
                                  )}
                                </div>
                              )}
                            </div>
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
                      }

                      // meeting item
                      return (
                        <div
                          key={`meeting-${item.log.id}`}
                          className="flex items-start gap-3 relative"
                        >
                          <div className="flex flex-col items-center">
                            <div className="w-2 h-2 rounded-sm flex-shrink-0 mt-1.5 border border-accent/50 bg-accent/10" />
                            {!isLastItem && (
                              <div className="w-px flex-1 min-h-[20px] bg-gray-200" />
                            )}
                          </div>
                          <div className="pb-2 flex-1 min-w-0">
                            <TimelineMeetingCard log={item.log} />
                          </div>
                        </div>
                      );
                    })}

                    {/* 미팅 추가 버튼 (완료 단계가 있을 때만) */}
                    {canWrite && completedStages.length > 0 && (
                      <div className="flex items-start gap-3 relative">
                        <div className="flex flex-col items-center">
                          <div className="w-px min-h-[8px]" />
                        </div>
                        <div className="pb-2 flex-1 min-w-0">
                          <InlineMeetingForm
                            txnId={txnId}
                            buyerId={buyer.id}
                          />
                        </div>
                      </div>
                    )}

                    {/* 미완료(pending) 단계 */}
                    {pendingStages.map((stage, idx) => {
                      const isLast = idx === pendingStages.length - 1;
                      return (
                        <div
                          key={stage}
                          className="flex items-start gap-3 relative opacity-50"
                        >
                          <div className="flex flex-col items-center">
                            <div className="w-2.5 h-2.5 rounded-full flex-shrink-0 mt-1 border border-gray-300 bg-white" />
                            {!isLast && (
                              <div className="w-px flex-1 min-h-[20px] bg-gray-200" />
                            )}
                          </div>
                          <div className="pb-3">
                            <span className="text-sm italic text-gray-400">
                              {MARKETING_STAGE_LABELS[stage]}
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
