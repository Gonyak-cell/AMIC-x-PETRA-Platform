import { memo } from "react";
import { Check, Plus } from "lucide-react";
import { cn } from "@/lib/cn";
import { SKIPPABLE_STAGES } from "@/modules/ma/constants";
import type { MarketingStage } from "@/modules/ma/types/marketing_log";

interface MarketingGridCellProps {
  stage: MarketingStage;
  dateValue: string | null;
  buyerName?: string;
  isNext?: boolean;
}

const MarketingGridCell = memo(function MarketingGridCell({
  stage,
  dateValue,
  buyerName,
  isNext = false,
}: MarketingGridCellProps) {
  const isEmpty = !dateValue;
  const shortDate = dateValue ? dateValue.slice(5) : null; // "MM-DD"

  return (
    <td
      data-testid={`grid-cell-${stage}`}
      aria-label={buyerName ? `${buyerName} ${stage} 활동 기록` : undefined}
      className={cn(
        "px-3 py-2 text-center text-xs transition-colors",
        isEmpty ? "text-text-muted" : "text-text-dark",
      )}
    >
      {isEmpty && isNext ? (
        <span className="inline-flex flex-col items-center gap-0.5 group/next">
          <span className="inline-flex items-center justify-center w-6 h-6 rounded-full border-2 border-dashed border-green-400 text-green-500 motion-safe:animate-pulse">
            <Plus className="h-3 w-3" />
          </span>
          <span className="text-[9px] text-green-600 font-medium">다음</span>
        </span>
      ) : isEmpty ? (
        <span
          className={`inline-block ${
            SKIPPABLE_STAGES.has(stage)
              ? "text-[10px] text-gray-400"
              : "w-4 h-4 rounded-full border border-gray-300"
          }`}
        >
          {SKIPPABLE_STAGES.has(stage) ? (
            <>
              <span className="text-gray-400" aria-hidden="true">
                &mdash;
              </span>
              <span className="sr-only">생략 가능</span>
            </>
          ) : (
            <span className="sr-only">미완료</span>
          )}
        </span>
      ) : (
        <span className="inline-flex flex-col items-center gap-0.5">
          <span className="inline-flex items-center justify-center w-5 h-5 rounded-full bg-gradient-to-br from-green-400 to-green-600 text-white shadow-sm">
            <Check className="h-3 w-3" />
          </span>
          <span className="text-[10px] text-green-600 font-semibold">
            {shortDate}
          </span>
        </span>
      )}
    </td>
  );
});

export default MarketingGridCell;
