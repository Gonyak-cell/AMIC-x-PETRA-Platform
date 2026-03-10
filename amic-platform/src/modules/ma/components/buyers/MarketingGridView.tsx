import { useMemo } from "react";
import { ChevronRight } from "lucide-react";
import { cn } from "@/lib/cn";
import { EmptyState } from "@/components/ui";
import BuyerTierBadge from "./BuyerTierBadge";
import MarketingGridCell from "./MarketingGridCell";
import {
  MARKETING_STAGES,
  MARKETING_STAGE_LABELS,
  countCompletedStages,
} from "@/modules/ma/constants";
import type { BuyerCandidate } from "@/modules/ma/types/buyer";
import type { MarketingStage } from "@/modules/ma/types/marketing_log";

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
        className="overflow-x-auto border border-gray-border rounded-dr"
        tabIndex={0}
        role="region"
        aria-label="바이어 그리드 스크롤"
      >
        <table
          className="w-full text-sm"
          aria-label="매수자별 마케팅 단계 현황"
          data-testid="marketing-grid"
        >
          <thead>
            <tr className="bg-bg-cool border-b-2 border-gray-300">
              <th className="text-left px-3 py-2 font-medium text-text-dark whitespace-nowrap min-w-[160px] sticky left-0 z-10 bg-bg-cool">
                매수자
              </th>
              {MARKETING_STAGES.map((s) => (
                <th
                  key={s}
                  className="px-2 py-2 font-medium text-gray-600 text-center text-xs whitespace-nowrap border-l border-gray-border"
                >
                  {MARKETING_STAGE_LABELS[s]}
                </th>
              ))}
              <th className="px-2 py-2 font-medium text-gray-600 text-center text-xs whitespace-nowrap border-l border-gray-border min-w-[60px]">
                진행률
              </th>
              <th className="w-10 border-l border-gray-border">
                <span className="sr-only">상세</span>
              </th>
            </tr>
          </thead>
          <tbody>
            {sorted.map((buyer) => {
              const stages = stageMap.get(buyer.id);
              const isDropped = buyer.status === "BID_DROPPED";
              const completedCount = countCompletedStages(stages);
              const progressPct = Math.round(
                (completedCount / MARKETING_STAGES.length) * 100,
              );
              return (
                <tr
                  key={buyer.id}
                  className={cn(
                    "border-b border-gray-300 last:border-b-0 group",
                    isDropped
                      ? "bg-gray-50 grayscale opacity-[0.55] hover:opacity-70"
                      : "hover:bg-accent/5",
                  )}
                >
                  <td
                    className="px-3 py-1.5 border-r border-gray-border sticky left-0 z-[1] bg-white group-hover:bg-accent/5 cursor-pointer"
                    tabIndex={0}
                    role="button"
                    onClick={() => onSelectBuyer(buyer.id)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' || e.key === ' ') {
                        e.preventDefault();
                        onSelectBuyer(buyer.id);
                      }
                    }}
                  >
                    <div className="flex items-center gap-1.5">
                      <div className="min-w-0">
                        <span
                          className={cn(
                            "font-medium text-xs truncate block max-w-[120px]",
                            isDropped
                              ? "text-gray-500 line-through"
                              : "text-text-dark",
                          )}
                        >
                          {buyer.company_name}
                        </span>
                        {buyer.contact_name && (
                          <span className="text-[10px] text-gray-500 truncate block max-w-[120px]">
                            {buyer.contact_name}
                          </span>
                        )}
                      </div>
                      {buyer.tier && <BuyerTierBadge tier={buyer.tier} />}
                    </div>
                  </td>
                  {MARKETING_STAGES.map((stage) => (
                    <MarketingGridCell
                      key={stage}
                      txnId={txnId}
                      buyerId={buyer.id}
                      stage={stage}
                      dateValue={stages?.[stage] ?? null}
                      canWrite={canWrite}
                      buyerName={buyer.company_name}
                    />
                  ))}
                  <td className="px-2 py-1.5 border-l border-gray-border">
                    <div className="flex items-center gap-1">
                      <div className="h-1.5 flex-1 max-w-[40px] rounded-full bg-gray-200">
                        <div
                          className="h-full rounded-full bg-accent transition-all"
                          style={{ width: `${progressPct}%` }}
                        />
                      </div>
                      <span className="text-[10px] text-gray-500 whitespace-nowrap">
                        {completedCount}/{MARKETING_STAGES.length}
                      </span>
                    </div>
                  </td>
                  <td className="text-center border-l border-gray-border">
                    <button
                      type="button"
                      onClick={() => onSelectBuyer(buyer.id)}
                      className="p-1 min-w-[44px] min-h-[44px] flex items-center justify-center text-gray-500 hover:text-accent transition-colors"
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
