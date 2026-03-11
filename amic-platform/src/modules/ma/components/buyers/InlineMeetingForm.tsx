import { useState } from "react";
import { Plus, Check, X } from "lucide-react";
import { Button } from "@/components/ui";
import { useCreateMeetingLog } from "@/modules/ma/hooks/useMeetingLogs";
import {
  MEETING_CHANNEL_OPTIONS,
  MEETING_TYPE_OPTIONS,
} from "@/modules/ma/constants/meeting";
import type {
  MeetingChannel,
  MeetingType,
} from "@/modules/ma/types/meeting_log";

interface InlineMeetingFormProps {
  txnId: string;
  buyerId: string;
}

function todayStr(): string {
  const d = new Date();
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

export default function InlineMeetingForm({
  txnId,
  buyerId,
}: InlineMeetingFormProps) {
  const [open, setOpen] = useState(false);
  const [title, setTitle] = useState("");
  const [meetingDate, setMeetingDate] = useState(todayStr());
  const [channel, setChannel] = useState<MeetingChannel>("IN_PERSON");
  const [meetingType, setMeetingType] = useState<MeetingType>("MEETING");
  const [summary, setSummary] = useState("");
  const [attendeesInput, setAttendeesInput] = useState("");

  const createLog = useCreateMeetingLog(txnId);

  const reset = () => {
    setTitle("");
    setMeetingDate(todayStr());
    setChannel("IN_PERSON");
    setMeetingType("MEETING");
    setSummary("");
    setAttendeesInput("");
    setOpen(false);
  };

  const handleSubmit = () => {
    if (!title.trim() || !meetingDate || createLog.isPending) return;
    createLog.mutate(
      {
        meeting_phase: "MARKETING",
        title: title.trim(),
        meeting_date: meetingDate,
        channel,
        meeting_type: meetingType,
        status: "COMPLETED",
        summary: summary.trim() || undefined,
        buyer_id: buyerId,
        attendees: attendeesInput.trim()
          ? attendeesInput
              .split(",")
              .map((n) => n.trim())
              .filter(Boolean)
              .map((name) => ({ name }))
          : undefined,
      },
      { onSuccess: reset },
    );
  };

  if (!open) {
    return (
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="flex items-center gap-1 text-[11px] text-gray-400 hover:text-accent transition-colors py-1.5"
      >
        <Plus className="h-3 w-3" />
        미팅 추가
      </button>
    );
  }

  return (
    <div
      className={`rounded border bg-accent/5 p-2 space-y-2 ${createLog.isError ? "border-red-300" : "border-accent/30"}`}
      onKeyDown={(e) => {
        if (e.key === "Escape") reset();
      }}
    >
      <div className="flex items-center gap-2">
        <input
          type="text"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="미팅 제목"
          aria-label="미팅 제목"
          maxLength={200}
          className="h-7 flex-1 min-w-0 px-2 text-xs border border-gray-border rounded bg-white focus:ring-1 focus:ring-accent"
          onKeyDown={(e) => {
            if (e.key === "Enter") handleSubmit();
          }}
          autoFocus
        />
        <input
          type="date"
          value={meetingDate}
          onChange={(e) => setMeetingDate(e.target.value)}
          className="h-7 px-1.5 text-xs border border-gray-border rounded bg-white focus:ring-1 focus:ring-accent"
          aria-label="미팅 날짜"
        />
      </div>
      <div className="flex items-center gap-2">
        <select
          value={channel}
          onChange={(e) => setChannel(e.target.value as MeetingChannel)}
          className="h-7 px-1.5 text-xs border border-gray-border rounded bg-white focus:ring-1 focus:ring-accent"
          aria-label="채널"
        >
          {MEETING_CHANNEL_OPTIONS.map((o) => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
        </select>
        <select
          value={meetingType}
          onChange={(e) => setMeetingType(e.target.value as MeetingType)}
          className="h-7 px-1.5 text-xs border border-gray-border rounded bg-white focus:ring-1 focus:ring-accent"
          aria-label="유형"
        >
          {MEETING_TYPE_OPTIONS.map((o) => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
        </select>
        <input
          type="text"
          value={summary}
          onChange={(e) => setSummary(e.target.value)}
          placeholder="요약 (선택)"
          aria-label="미팅 요약"
          maxLength={500}
          className="h-7 flex-1 min-w-0 px-2 text-xs border border-gray-border rounded bg-white focus:ring-1 focus:ring-accent"
          onKeyDown={(e) => {
            if (e.key === "Enter") handleSubmit();
          }}
        />
      </div>
      <div className="flex items-center gap-2">
        <input
          type="text"
          value={attendeesInput}
          onChange={(e) => setAttendeesInput(e.target.value)}
          placeholder="참석자 (쉼표 구분, 예: 홍길동, 김철수)"
          aria-label="참석자"
          maxLength={500}
          className="h-7 flex-1 min-w-0 px-2 text-xs border border-gray-border rounded bg-white focus:ring-1 focus:ring-accent"
          onKeyDown={(e) => {
            if (e.key === "Enter") handleSubmit();
          }}
        />
        <Button
          size="sm"
          onClick={handleSubmit}
          loading={createLog.isPending}
          className="h-7 px-2 text-xs"
          disabled={!title.trim() || !meetingDate}
        >
          <Check className="h-3 w-3 mr-1" />
          저장
        </Button>
        <Button
          size="sm"
          variant="ghost"
          onClick={reset}
          className="h-7 w-7 p-0"
          aria-label="취소"
        >
          <X className="h-3 w-3" />
        </Button>
      </div>
      {createLog.isError && (
        <p className="text-xs text-red-500">
          저장에 실패했습니다. 다시 시도해 주세요.
        </p>
      )}
    </div>
  );
}
