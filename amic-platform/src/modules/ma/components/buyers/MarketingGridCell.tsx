import { useRef, useState } from "react";
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
  const shortDate = dateValue ? dateValue.slice(5) : null; // "MM/DD"

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
      onClick={handleClick}
      className={cn(
        "px-2 py-1.5 text-center text-xs cursor-pointer transition-colors border-r border-gray-border",
        isEmpty
          ? "text-text-muted hover:bg-accent/5"
          : "text-text-dark font-medium hover:bg-accent/10",
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
      ) : (
        <span>{shortDate ?? "-"}</span>
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
