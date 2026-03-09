import { useRef, useState } from "react";
import { Check } from "lucide-react";
import { cn } from "@/lib/cn";
import type { MarketingStage } from "@/modules/ma/types/marketing_log";
import InlineLogInput from "./InlineLogInput";
import LogListPopover from "./LogListPopover";

interface MarketingGridCellProps {
  txnId: string;
  buyerId: string;
  stage: MarketingStage;
  dateValue: string | null;
  canWrite: boolean;
}

export default function MarketingGridCell({
  txnId,
  buyerId,
  stage,
  dateValue,
  canWrite,
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
      tabIndex={0}
      role="button"
      onClick={handleClick}
      onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); handleClick(); } }}
      className={cn(
        "px-2 py-1.5 text-center text-xs cursor-pointer transition-colors border-r border-gray-border",
        isEmpty
          ? "text-text-muted hover:bg-accent/5"
          : "text-text-dark hover:bg-accent/10",
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
      ) : isEmpty ? (
        <span className="inline-flex items-center justify-center w-5 h-5 rounded-full border border-dashed border-gray-300 hover:border-accent">
          <span className="sr-only">미완료</span>
        </span>
      ) : (
        <span className="inline-flex flex-col items-center gap-0.5">
          <span className="inline-flex items-center justify-center w-5 h-5 rounded-full bg-accent text-white">
            <Check className="h-3 w-3" />
          </span>
          <span className="text-[9px] text-accent font-medium">{shortDate}</span>
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
}
