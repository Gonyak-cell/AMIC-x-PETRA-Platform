import { useState } from "react";
import { Pencil, Trash2, ChevronDown, ChevronUp, Users } from "lucide-react";
import { Badge } from "@/components/ui";
import {
  MEETING_STATUS_VARIANT,
  MARKETING_STAGE_LABELS,
} from "@/modules/ma/constants";
import {
  MEETING_STATUS_LABEL,
  MEETING_TYPE_LABEL,
  CHANNEL_ICON_COMPONENT,
} from "@/modules/ma/constants/meeting";
import type { MeetingLog } from "@/modules/ma/types/meeting_log";

interface TimelineMeetingCardProps {
  log: MeetingLog;
  onDelete?: (logId: string) => void;
  onEdit?: (log: MeetingLog) => void;
  canWrite?: boolean;
}

export default function TimelineMeetingCard({
  log,
  onDelete,
  onEdit,
  canWrite,
}: TimelineMeetingCardProps) {
  const [expanded, setExpanded] = useState(false);
  const ChannelIcon = CHANNEL_ICON_COMPONENT[log.channel];

  return (
    <div
      className="ml-2 rounded border border-gray-200 bg-gray-50 px-3 py-2 transition-colors hover:bg-gray-100/80 cursor-pointer focus:outline-none focus:ring-2 focus:ring-primary-500/40"
      role="button"
      tabIndex={0}
      aria-expanded={expanded}
      aria-label={`${log.title} 미팅 상세 ${expanded ? "접기" : "펼치기"}`}
      onClick={() => setExpanded((v) => !v)}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          setExpanded((v) => !v);
        }
      }}
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
        {log.meeting_type && (
          <Badge variant="neutral" className="text-[10px] shrink-0">
            {MEETING_TYPE_LABEL[log.meeting_type]}
          </Badge>
        )}
        <Badge
          variant={MEETING_STATUS_VARIANT[log.status]}
          className="text-[10px] shrink-0"
        >
          {MEETING_STATUS_LABEL[log.status]}
        </Badge>
        {log.attendee_count > 0 && (
          <span className="flex items-center gap-0.5 text-[10px] text-gray-400 shrink-0">
            <Users className="h-3 w-3" />
            {log.attendee_count}
          </span>
        )}
        <span className="text-[10px] text-gray-400 shrink-0 ml-auto">
          {log.meeting_date}
        </span>
        {expanded ? (
          <ChevronUp className="h-3 w-3 text-gray-400 shrink-0" />
        ) : (
          <ChevronDown className="h-3 w-3 text-gray-400 shrink-0" />
        )}
        {canWrite && onEdit && (
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              onEdit(log);
            }}
            className="p-1 text-gray-500 hover:text-primary-600 transition-colors shrink-0"
            aria-label="미팅 로그 수정"
          >
            <Pencil className="h-3.5 w-3.5" />
          </button>
        )}
        {canWrite && onDelete && (
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              if (window.confirm("이 미팅 로그를 삭제하시겠습니까?")) {
                onDelete(log.id);
              }
            }}
            className="p-1.5 text-gray-400 hover:text-red-500 transition-colors shrink-0"
            aria-label="미팅 로그 삭제"
          >
            <Trash2 className="h-3 w-3" />
          </button>
        )}
      </div>
      {!expanded && log.summary && (
        <p className="mt-1 text-[11px] text-gray-500 line-clamp-1">
          {log.summary}
        </p>
      )}
      {expanded && (
        <div className="mt-2 space-y-1.5 border-t border-gray-200 pt-2">
          {log.summary && (
            <div>
              <span className="text-[10px] font-medium text-gray-500">
                요약
              </span>
              <p className="text-[11px] text-gray-700">{log.summary}</p>
            </div>
          )}
          {log.minutes && (
            <div>
              <span className="text-[10px] font-medium text-gray-500">
                회의록
              </span>
              <p className="text-[11px] text-gray-700 whitespace-pre-line line-clamp-5">
                {log.minutes}
              </p>
            </div>
          )}
          {log.attendee_count > 0 && (
            <p className="text-[10px] text-gray-500">
              참석자 {log.attendee_count}명
            </p>
          )}
        </div>
      )}
    </div>
  );
}
