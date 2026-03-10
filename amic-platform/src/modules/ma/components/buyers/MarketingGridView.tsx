import { useMemo } from "react";
import { ChevronRight } from "lucide-react";
import { cn } from "@/lib/cn";
import { EmptyState } from "@/components/ui";
import MarketingGridCell from "./MarketingGridCell";
import {
  MARKETING_STAGES,
  MARKETING_STAGE_LABELS,
  SKIPPABLE_STAGES,
  countCompletedStages,
  effectiveStageCount,
  latestCompletedStageIndex,
} from "@/modules/ma/constants";
import type { BuyerCandidate, BuyerTier } from "@/modules/ma/types/buyer";
import type { MarketingStage } from "@/modules/ma/types/marketing_log";

/* ── Compact Tier Badge (Grid 전용) ─────────────── */
const TIER_SHORT: Partial<Record<BuyerTier, string>> = {
  TIER_1: "T1",
  TIER_2: "T2",
  TIER_3: "T3",
  // NOT_TARGET: Grid에서는 Tier 뱃지를 표시하지 않음 (의도적 생략)
};
const TIER_COLOR: Partial<Record<BuyerTier, string>> = {
  TIER_1: "bg-accent-light text-amic-400",
  TIER_2: "bg-amic-50 text-amic-400",
  TIER_3: "bg-amic-100 text-amic-500",
};

/* ── Circular SVG Progress ──────────────────────── */
const CIRCLE_R = 11;
const CIRCLE_C = 2 * Math.PI * CIRCLE_R;

function CircularProgress({ pct, label }: { pct: number; label: string }) {
  const offset = CIRCLE_C - (pct / 100) * CIRCLE_C;
  return (
    <div className="flex flex-col items-center gap-0.5">
      <svg width="28" height="28" viewBox="0 0 28 28" className="block" role="img" aria-label={label}>
        <circle
          cx="14"
          cy="14"
          r={CIRCLE_R}
          fill="none"
          className="stroke-gray-200"
          strokeWidth="3"
        />
        <circle
          cx="14"
          cy="14"
          r={CIRCLE_R}
          fill="none"
          className="stroke-green-500 transition-all duration-500"
          strokeWidth="3"
          strokeLinecap="round"
          strokeDasharray={CIRCLE_C}
          strokeDashoffset={offset}
          transform="rotate(-90 14 14)"
        />
      </svg>
      <span className="text-[10px] text-gray-500 whitespace-nowrap">
        {label}
      </span>
    </div>
  );
}

interface MarketingGridViewProps {
  buyers: BuyerCandidate[];
  stageMap: Map<string, Partial<Record<MarketingStage, string | null>>>;
  onSelectBuyer: (buyerId: string) => void;
  canWrite: boolean;
  txnId: string;
}

export default function MarketingGridView({
  buyers,
  stageMap,
  onSelectBuyer,
  canWrite,
  txnId,
}: MarketingGridViewProps) {
  // 완료 단계 수 기준 내림차순 정렬
  const sorted = useMemo(
    () =>
      [...buyers].sort((a, b) => {
        const aStages = stageMap.get(a.id);
        const bStages = stageMap.get(b.id);
        const aCount = countCompletedStages(aStages);
        const bCount = countCompletedStages(bStages);
        return bCount - aCount;
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
        Grid View — 매수자 × 마케팅 단계
      </p>
      <div
        className="overflow-x-auto rounded-lg"
        tabIndex={0}
        role="region"
        aria-label="바이어 그리드 스크롤"
      >
        <table
          className="w-full text-sm border-separate"
          style={{ borderSpacing: "0 6px" }}
          aria-label="매수자별 마케팅 단계 현황"
          data-testid="marketing-grid"
        >
          <thead>
            <tr className="bg-accent">
              <th className="text-left px-3 py-2.5 font-medium text-white whitespace-nowrap w-[200px] max-w-[200px] sticky left-0 z-10 bg-accent rounded-l-lg">
                매수자
              </th>
              {MARKETING_STAGES.map((s) => (
                <th
                  key={s}
                  className="px-2 py-2.5 font-medium text-white/90 text-center text-xs whitespace-nowrap"
                >
                  {MARKETING_STAGE_LABELS[s]}
                  {SKIPPABLE_STAGES.has(s) && (
                    <span className="block text-[9px] font-normal text-white/60">
                      선택
                    </span>
                  )}
                </th>
              ))}
              <th className="px-2 py-2.5 font-medium text-white/90 text-center text-xs whitespace-nowrap min-w-[60px]">
                진행률
              </th>
              <th className="w-10 rounded-r-lg">
                <span className="sr-only">상세</span>
              </th>
            </tr>
          </thead>
          <tbody>
            {sorted.map((buyer) => {
              const stages = stageMap.get(buyer.id);
              const isDropped = buyer.status === "BID_DROPPED";
              const completedCount = countCompletedStages(stages);
              const effectiveTotal = effectiveStageCount(stages);
              const progressPct =
                effectiveTotal > 0
                  ? Math.round((completedCount / effectiveTotal) * 100)
                  : 0;
              const hasProgress = completedCount > 0;
              // 마지막 완료 단계 다음 = "다음 단계" CTA 표시 위치
              // 중간 단계가 비어 있어도 마지막 완료 이후만 표시 (의도적)
              const nextIdx = stages
                ? latestCompletedStageIndex(stages) + 1
                : 0; // stages 없으면 첫 단계(IDENTIFIED)가 다음
              return (
                <tr
                  key={buyer.id}
                  className={cn(
                    "group transition-shadow",
                    isDropped
                      ? "grayscale opacity-[0.55] hover:opacity-70"
                      : hasProgress
                        ? "bg-white shadow-sm hover:shadow-md"
                        : "bg-white/60 hover:bg-white",
                  )}
                >
                  <td
                    className={cn(
                      "px-3 py-2 sticky left-0 z-[1] cursor-pointer rounded-l-lg",
                      isDropped ? "bg-gray-50" : "bg-white",
                    )}
                    tabIndex={0}
                    role="button"
                    aria-label={`${buyer.company_name} 상세 보기`}
                    onClick={() => onSelectBuyer(buyer.id)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter" || e.key === " ") {
                        e.preventDefault();
                        onSelectBuyer(buyer.id);
                      }
                    }}
                  >
                    <div className="flex items-center gap-2">
                      {/* Compact Tier Badge */}
                      {buyer.tier && TIER_SHORT[buyer.tier] && (
                        <span
                          className={cn(
                            "inline-flex items-center justify-center w-7 h-7 rounded-md text-[11px] font-bold flex-shrink-0",
                            TIER_COLOR[buyer.tier] ??
                              "bg-gray-200 text-gray-600",
                          )}
                        >
                          {TIER_SHORT[buyer.tier]}
                        </span>
                      )}
                      <div className="min-w-0">
                        <span
                          className={cn(
                            "font-medium text-xs truncate block max-w-[140px]",
                            isDropped
                              ? "text-gray-500 line-through"
                              : "text-text-dark",
                          )}
                        >
                          {buyer.company_name}
                        </span>
                        {buyer.contact_name && (
                          <span className="text-[10px] text-gray-500 truncate block max-w-[140px]">
                            {buyer.contact_name}
                          </span>
                        )}
                      </div>
                    </div>
                  </td>
                  {MARKETING_STAGES.map((stage, idx) => (
                    <MarketingGridCell
                      key={stage}
                      txnId={txnId}
                      buyerId={buyer.id}
                      stage={stage}
                      dateValue={stages?.[stage] ?? null}
                      canWrite={canWrite}
                      buyerName={buyer.company_name}
                      isNext={
                        !isDropped &&
                        idx === nextIdx &&
                        nextIdx < MARKETING_STAGES.length
                      }
                    />
                  ))}
                  <td className="px-2 py-2">
                    <CircularProgress
                      pct={progressPct}
                      label={`${completedCount}/${effectiveTotal}`}
                    />
                  </td>
                  <td className="text-center rounded-r-lg">
                    <button
                      type="button"
                      onClick={() => onSelectBuyer(buyer.id)}
                      className="p-1 min-w-[44px] min-h-[44px] flex items-center justify-center text-gray-400 hover:text-accent transition-colors"
                      aria-label={`${buyer.company_name} 상세`}
                    >
                      <ChevronRight className="h-4 w-4" />
                    </button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
