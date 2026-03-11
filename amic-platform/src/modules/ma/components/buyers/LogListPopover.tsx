import { useState, useRef, useCallback } from "react";
import { Trash2 } from "lucide-react";
import { Popover } from "@/components/ui/Popover";
import { Badge } from "@/components/ui";
import {
  useMarketingLogs,
  useDeleteMarketingLog,
} from "@/modules/ma/hooks/useMarketingLogs";
import { MARKETING_STAGE_LABELS } from "@/modules/ma/constants";
import type { MarketingStage } from "@/modules/ma/types/marketing_log";
import InlineLogInput from "./InlineLogInput";

interface LogListPopoverProps {
  open: boolean;
  onClose: () => void;
  anchorRef: React.RefObject<HTMLElement | null>;
  txnId: string;
  buyerId: string;
  stage: MarketingStage;
  canWrite: boolean;
}

function DeleteLogButton({
  logId,
  onConfirm,
}: {
  logId: string;
  onConfirm: (id: string) => void;
}) {
  const [confirming, setConfirming] = useState(false);

  if (confirming) {
    return (
      <span className="flex items-center gap-1 text-[10px]">
        <button
          type="button"
          onClick={() => { onConfirm(logId); setConfirming(false); }}
          className="text-danger font-medium hover:underline"
        >
          삭제
        </button>
        <button
          type="button"
          onClick={() => setConfirming(false)}
          className="text-text-muted hover:underline"
        >
          취소
        </button>
      </span>
    );
  }

  return (
    <button
      type="button"
      onClick={() => setConfirming(true)}
      className="shrink-0 p-0.5 text-text-muted hover:text-danger transition-colors"
      aria-label="로그 삭제"
    >
      <Trash2 className="h-3 w-3" />
    </button>
  );
}

export default function LogListPopover({
  open,
  onClose,
  anchorRef,
  txnId,
  buyerId,
  stage,
  canWrite,
}: LogListPopoverProps) {
  const { data: logs } = useMarketingLogs(txnId, buyerId, { stage });
  const deleteLog = useDeleteMarketingLog(txnId, buyerId);
  const listRef = useRef<HTMLUListElement>(null);

  const handleListKeyDown = useCallback((e: React.KeyboardEvent<HTMLUListElement>) => {
    if (e.key !== "ArrowDown" && e.key !== "ArrowUp") return;
    e.preventDefault();
    const items = listRef.current?.querySelectorAll<HTMLLIElement>("[role=option]");
    if (!items || items.length === 0) return;
    const current = document.activeElement as HTMLElement;
    const idx = current?.dataset?.index ? Number(current.dataset.index) : -1;
    const next = e.key === "ArrowDown"
      ? Math.min(idx + 1, items.length - 1)
      : Math.max(idx - 1, 0);
    items[next]?.focus();
  }, []);

  return (
    <Popover
      open={open}
      onClose={onClose}
      anchorRef={anchorRef}
      className="w-80"
    >
      <div className="p-3 space-y-2">
        <div className="flex items-center justify-between">
          <h4 className="text-sm font-medium text-text-dark">
            {MARKETING_STAGE_LABELS[stage]} 로그
          </h4>
          <Badge variant="neutral" className="text-[10px]">
            {logs?.length ?? 0}건
          </Badge>
        </div>

        {logs && logs.length > 0 ? (
          <ul
            ref={listRef}
            role="listbox"
            aria-label={`${MARKETING_STAGE_LABELS[stage]} 로그 목록`}
            tabIndex={0}
            onKeyDown={handleListKeyDown}
            className="space-y-1.5 max-h-48 overflow-y-auto focus:outline-none"
          >
            {logs.map((log, idx) => (
              <li
                key={log.id}
                role="option"
                tabIndex={-1}
                data-index={idx}
                className="flex items-start gap-2 text-xs p-1.5 rounded bg-bg-cool focus:ring-2 focus:ring-accent/40 focus:outline-none"
              >
                <span className="shrink-0 text-text-muted w-16">
                  {log.log_date}
                </span>
                <span className="flex-1 text-text-dark min-w-0 break-words">
                  {log.content || "-"}
                </span>
                {canWrite && (
                  <DeleteLogButton
                    logId={log.id}
                    onConfirm={(id) => deleteLog.mutate(id)}
                  />
                )}
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-xs text-text-muted py-2">기록이 없습니다.</p>
        )}

        {canWrite && (
          <div className="pt-1 border-t border-gray-border">
            <InlineLogInput
              txnId={txnId}
              buyerId={buyerId}
              defaultStage={stage}
              compact
            />
          </div>
        )}
      </div>
    </Popover>
  );
}
