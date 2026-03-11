import { Badge } from "@/components/ui";
import {
  MEETING_STATUS_VARIANT,
  MARKETING_STAGE_LABELS,
} from "@/modules/ma/constants";
import {
  MEETING_STATUS_LABEL,
  CHANNEL_ICON_COMPONENT,
} from "@/modules/ma/constants/meeting";
import type { MeetingLog } from "@/modules/ma/types/meeting_log";

interface TimelineMeetingCardProps {
  log: MeetingLog;
}

export default function TimelineMeetingCard({ log }: TimelineMeetingCardProps) {
  const ChannelIcon = CHANNEL_ICON_COMPONENT[log.channel];

  return (
    <div
      className="ml-2 rounded border border-gray-200 bg-gray-50 px-3 py-2"
      role="listitem"
    >
      <div className="flex items-center gap-2">
        <span className="text-gray-400">
          <ChannelIcon className="h-3.5 w-3.5" />
        </span>
        <span className="text-xs font-medium text-text-dark truncate">
          {log.marketing_stage
            ? MARKETING_STAGE_LABELS[log.marketing_stage]
            : log.title}
        </span>
        <Badge
          variant={MEETING_STATUS_VARIANT[log.status]}
          className="text-[10px] shrink-0"
        >
          {MEETING_STATUS_LABEL[log.status]}
        </Badge>
        <span className="text-[10px] text-gray-400 shrink-0 ml-auto">
          {log.meeting_date}
        </span>
      </div>
      {log.summary && (
        <p className="mt-1 text-[11px] text-gray-500 line-clamp-1">
          {log.summary}
        </p>
      )}
    </div>
  );
}
