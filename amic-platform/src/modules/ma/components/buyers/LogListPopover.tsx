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
          <ul className="space-y-1.5 max-h-48 overflow-y-auto">
            {logs.map((log) => (
              <li
                key={log.id}
                className="flex items-start gap-2 text-xs p-1.5 rounded bg-bg-cool"
              >
                <span className="shrink-0 text-text-muted w-16">
                  {log.log_date}
                </span>
                <span className="flex-1 text-text-dark min-w-0 break-words">
                  {log.content || "-"}
                </span>
                {canWrite && (
                  <button
                    type="button"
                    onClick={() => deleteLog.mutate(log.id)}
                    className="shrink-0 p-0.5 text-text-muted hover:text-danger transition-colors"
                    aria-label="로그 삭제"
                  >
                    <Trash2 className="h-3 w-3" />
                  </button>
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
