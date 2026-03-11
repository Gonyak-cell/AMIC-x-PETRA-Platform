import { Calendar } from "lucide-react";
import { Badge, EmptyState, Spinner } from "@/components/ui";
import {
  MEETING_STATUS_VARIANT,
  MARKETING_STAGE_LABELS,
} from "@/modules/ma/constants";
import {
  MEETING_STATUS_LABEL,
  CHANNEL_ICON_COMPONENT,
} from "@/modules/ma/constants/meeting";
import { useMeetingLogs } from "@/modules/ma/hooks/useMeetingLogs";

interface BuyerMeetingTimelineProps {
  txnId: string;
  buyerId: string;
}

export default function BuyerMeetingTimeline({
  txnId,
  buyerId,
}: BuyerMeetingTimelineProps) {
  const { data, isLoading } = useMeetingLogs(txnId, { buyerId });

  const logs = data?.items ?? [];

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-8">
        <Spinner />
      </div>
    );
  }

  if (logs.length === 0) {
    return <EmptyState icon={Calendar} title="미팅 기록 없음" />;
  }

  return (
    <div className="space-y-0">
      {logs.map((log, idx) => (
        <div key={log.id} className="relative flex gap-4">
          {/* 왼쪽: 날짜 */}
          <div className="w-20 shrink-0 pt-1 text-right">
            <span className="text-xs text-text-muted">{log.meeting_date}</span>
          </div>

          {/* 중앙: 세로 라인 + 점 */}
          <div className="relative flex flex-col items-center">
            <div className="z-10 mt-1.5 h-2.5 w-2.5 rounded-full border-2 border-accent bg-white" />
            {idx < logs.length - 1 && (
              <div className="w-0 flex-1 border-l-2 border-gray-200" />
            )}
          </div>

          {/* 우측: 카드 */}
          <div className="mb-4 flex-1 rounded-lg border bg-white p-3">
            <div className="flex items-center gap-2">
              {(() => {
                const ChannelIcon = CHANNEL_ICON_COMPONENT[log.channel];
                return (
                  <span className="text-text-muted">
                    <ChannelIcon className="h-4 w-4" />
                  </span>
                );
              })()}
              <span className="font-medium text-sm">{log.title}</span>
              <Badge variant={MEETING_STATUS_VARIANT[log.status]}>
                {MEETING_STATUS_LABEL[log.status]}
              </Badge>
              {log.marketing_stage && (
                <Badge variant="info">
                  {MARKETING_STAGE_LABELS[log.marketing_stage]}
                </Badge>
              )}
            </div>
            {log.summary && (
              <p className="mt-1.5 text-sm text-text-muted line-clamp-2">
                {log.summary}
              </p>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}
