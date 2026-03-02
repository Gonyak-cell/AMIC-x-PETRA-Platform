import { Calendar, MapPin, Users, ChevronRight } from "lucide-react";
import { Badge } from "@/components/ui";
import {
  MEETING_CHANNEL_OPTIONS,
  MEETING_STATUS_OPTIONS,
  MEETING_STATUS_VARIANT,
} from "@/modules/ma/constants";
import type { MeetingLog } from "@/modules/ma/types/meeting_log";

interface MeetingLogCardProps {
  meeting: MeetingLog;
  onClick: () => void;
}

export default function MeetingLogCard({
  meeting,
  onClick,
}: MeetingLogCardProps) {
  const channelLabel =
    MEETING_CHANNEL_OPTIONS.find((o) => o.value === meeting.channel)?.label ??
    meeting.channel;
  const statusLabel =
    MEETING_STATUS_OPTIONS.find((o) => o.value === meeting.status)?.label ??
    meeting.status;

  return (
    <button
      type="button"
      onClick={onClick}
      className="w-full text-left rounded-xl border border-gray-border bg-white p-4 hover:border-primary-300 hover:shadow-sm transition-all"
    >
      <div className="flex items-start justify-between">
        <div className="flex-1 min-w-0">
          <h4 className="text-sm font-heading font-semibold text-text-dark truncate">
            {meeting.title}
          </h4>
          <div className="flex flex-wrap items-center gap-3 mt-1.5 text-xs text-text-secondary">
            <span className="flex items-center gap-1">
              <Calendar className="h-3.5 w-3.5" />
              {new Date(meeting.meeting_date).toLocaleDateString("ko-KR")}
              {meeting.meeting_time && ` ${meeting.meeting_time}`}
            </span>
            {meeting.location && (
              <span className="flex items-center gap-1">
                <MapPin className="h-3.5 w-3.5" />
                {meeting.location}
              </span>
            )}
            <span className="flex items-center gap-1">
              <Users className="h-3.5 w-3.5" />
              {meeting.attendee_count}명
            </span>
          </div>
          {meeting.summary && (
            <p className="text-xs text-text-muted mt-1.5 line-clamp-2">
              {meeting.summary}
            </p>
          )}
        </div>
        <div className="flex items-center gap-2 shrink-0 ml-3">
          <Badge variant="neutral">{channelLabel}</Badge>
          <Badge variant={MEETING_STATUS_VARIANT[meeting.status]}>
            {statusLabel}
          </Badge>
          <ChevronRight className="h-4 w-4 text-gray-400" />
        </div>
      </div>
    </button>
  );
}
