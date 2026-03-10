import { memo, useRef, useState } from "react";
import { Check, Plus } from "lucide-react";
import { cn } from "@/lib/cn";
import { SKIPPABLE_STAGES } from "@/modules/ma/constants";
import type { MarketingStage } from "@/modules/ma/types/marketing_log";
import InlineLogInput from "./InlineLogInput";
import LogListPopover from "./LogListPopover";

interface MarketingGridCellProps {
  txnId: string;
  buyerId: string;
  stage: MarketingStage;
  dateValue: string | null;
  canWrite: boolean;
  buyerName?: string;
  isNext?: boolean;
}

const MarketingGridCell = memo(function MarketingGridCell({
  txnId,
  buyerId,
  stage,
  dateValue,
  canWrite,
  buyerName,
  isNext = false,
}: MarketingGridCellProps) {
  const cellRef = useRef<HTMLTableCellElement>(null);
  const [showInput, setShowInput] = useState(false);
  const [showPopover, setShowPopover] = useState(false);

  const isEmpty = !dateValue;
  const shortDate = dateValue ? dateValue.slice(5) : null; // "MM-DD"

  const handleClick = () => {
    if (isEmpty && canWrite) {
      setShowInput(true);
    } else if (!isEmpty) {
      setShowPopover(true);
    }
  };

  return (
    <td
      ref={cellRef}
      data-testid={`grid-cell-${stage}`}
      tabIndex={0}
      role="button"
      aria-label={buyerName ? `${buyerName} ${stage} 활동 기록` : undefined}
      onClick={handleClick}
      onKeyDown={(e) => {
        if (e.key === "Escape" && showInput) {
          setShowInput(false);
        } else if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          handleClick();
        }
      }}
      className={cn(
        "px-3 py-2 text-center text-xs cursor-pointer transition-colors",
        isEmpty
          ? "text-text-muted hover:bg-accent/10"
          : "text-text-dark hover:bg-accent/15",
      )}
    >
      {showInput && isEmpty ? (
        <InlineLogInput
          txnId={txnId}
          buyerId={buyerId}
          defaultStage={stage}
          compact
          onComplete={() => setShowInput(false)}
        />
      ) : isEmpty && isNext ? (
        <span
          className="inline-flex flex-col items-center gap-0.5 group/next"
          title={canWrite ? "클릭하여 다음 단계 기록" : undefined}
        >
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
          title={canWrite ? "클릭하여 로그 추가" : undefined}
        >
          {SKIPPABLE_STAGES.has(stage) ? (
            <><span className="text-gray-400" aria-hidden="true">&mdash;</span><span className="sr-only">생략 가능</span></>
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

      {showPopover && (
        <LogListPopover
          open={showPopover}
          onClose={() => setShowPopover(false)}
          anchorRef={cellRef}
          txnId={txnId}
          buyerId={buyerId}
          stage={stage}
          canWrite={canWrite}
        />
      )}
    </td>
  );
});

export default MarketingGridCell;
