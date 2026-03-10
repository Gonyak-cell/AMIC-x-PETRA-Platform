import { CheckCircle, Circle } from "lucide-react";
import { Spinner } from "@/components/ui";
import type { BuyerStageSummary } from "@/modules/ma/types/marketing_log";
import { MARKETING_STAGE_LABELS } from "@/modules/ma/constants";
import { useMarketingLogs } from "@/modules/ma/hooks/useMarketingLogs";

interface MaterialTrackerProps {
  txnId: string;
  buyerId: string;
  stageSummary: BuyerStageSummary | undefined;
}

interface CheckItem {
  label: string;
  done: boolean;
  date: string | null;
}

export default function MaterialTracker({
  txnId,
  buyerId,
  stageSummary,
}: MaterialTrackerProps) {
  const { data: logs, isLoading: logsLoading } = useMarketingLogs(
    txnId,
    buyerId,
  );

  const stages = stageSummary?.stages;

  const items: CheckItem[] = [
    {
      label: "Teaser 발송",
      done: stages?.TEASER_SENT != null,
      date: stages?.TEASER_SENT ?? null,
    },
    {
      label: "NDA 체결",
      done: stages?.NDA_SIGNED != null,
      date: stages?.NDA_SIGNED ?? null,
    },
    {
      label: "IM 배포",
      done: stages?.IM_DISTRIBUTED != null,
      date: stages?.IM_DISTRIBUTED ?? null,
    },
    {
      label: "LOI 접수",
      done: stages?.LOI_RECEIVED != null,
      date: stages?.LOI_RECEIVED ?? null,
    },
    {
      label: "VDR 접근",
      done: false,
      date: null,
    },
  ];

  const recentLogs = (logs ?? []).slice(0, 3);

  return (
    <div className="space-y-4">
      {/* 체크리스트 */}
      <div className="space-y-3">
        {items.map((item) => (
          <div key={item.label} className="flex items-center gap-2">
            {item.done ? (
              <CheckCircle className="h-5 w-5 shrink-0 text-green-500" />
            ) : (
              <Circle className="h-5 w-5 shrink-0 text-gray-300" />
            )}
            <span
              className={`text-sm ${item.done ? "text-text-primary" : "text-text-muted"}`}
            >
              {item.label}
            </span>
            {item.date && (
              <span className="ml-auto text-xs text-text-muted">
                {item.date}
              </span>
            )}
          </div>
        ))}
      </div>

      {/* 마케팅 로그 최근 3건 */}
      {logsLoading ? (
        <div className="flex justify-center py-2">
          <Spinner />
        </div>
      ) : (
        recentLogs.length > 0 && (
          <div className="mt-3 border-t pt-3">
            <h4 className="text-xs font-semibold text-text-muted mb-2">
              최근 마케팅 로그
            </h4>
            <div className="space-y-1.5">
              {recentLogs.map((log) => (
                <div key={log.id} className="flex items-baseline gap-2 text-xs">
                  <span className="shrink-0 text-text-muted">
                    {log.log_date}
                  </span>
                  <span className="shrink-0 font-medium text-accent">
                    {MARKETING_STAGE_LABELS[log.stage] ?? log.stage}
                  </span>
                  <span className="truncate text-text-secondary">
                    {log.content || "-"}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )
      )}
    </div>
  );
}
