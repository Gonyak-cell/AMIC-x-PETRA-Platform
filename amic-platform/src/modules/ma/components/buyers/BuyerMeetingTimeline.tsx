import {
  Calendar,
  Video,
  Phone,
  Mail,
  Users,
  MessageCircle,
} from "lucide-react";
import { Badge, EmptyState, Spinner } from "@/components/ui";
import { useMeetingLogs } from "@/modules/ma/hooks/useMeetingLogs";
import type {
  MeetingChannel,
  MeetingStatus,
} from "@/modules/ma/types/meeting_log";

interface BuyerMeetingTimelineProps {
  txnId: string;
  buyerId: string;
}

const CHANNEL_ICON: Record<MeetingChannel, React.ReactNode> = {
  VIDEO: <Video className="h-4 w-4" />,
  PHONE: <Phone className="h-4 w-4" />,
  EMAIL: <Mail className="h-4 w-4" />,
  IN_PERSON: <Users className="h-4 w-4" />,
  HYBRID: <MessageCircle className="h-4 w-4" />,
};

const STATUS_VARIANT: Record<
  MeetingStatus,
  "success" | "info" | "error" | "warning"
> = {
  COMPLETED: "success",
  SCHEDULED: "info",
  CANCELLED: "error",
  POSTPONED: "warning",
};

const STATUS_LABEL: Record<MeetingStatus, string> = {
  COMPLETED: "완료",
  SCHEDULED: "예정",
  CANCELLED: "취소",
  POSTPONED: "연기",
};

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
              <span className="text-text-muted">
                {CHANNEL_ICON[log.channel]}
              </span>
              <span className="font-medium text-sm">{log.title}</span>
              <Badge variant={STATUS_VARIANT[log.status]}>
                {STATUS_LABEL[log.status]}
              </Badge>
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
