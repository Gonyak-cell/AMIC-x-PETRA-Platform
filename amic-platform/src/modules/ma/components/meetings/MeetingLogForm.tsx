import { useState, useEffect } from "react";
import { Button, Input, Select, Modal } from "@/components/ui";
import {
  MEETING_CHANNEL_OPTIONS,
  MEETING_STATUS_OPTIONS,
  MARKETING_STAGE_OPTIONS,
} from "@/modules/ma/constants";
import type {
  MeetingPhase,
  MeetingLogCreate,
  MeetingLogUpdate,
  MeetingLog,
} from "@/modules/ma/types/meeting_log";
import type { MarketingStage } from "@/modules/ma/types/marketing_log";

interface MeetingLogFormProps {
  open: boolean;
  onClose: () => void;
  meetingPhase: MeetingPhase;
  existing?: MeetingLog | null;
  onSubmit: (body: MeetingLogCreate | MeetingLogUpdate) => void;
  isLoading?: boolean;
}

export default function MeetingLogForm({
  open,
  onClose,
  meetingPhase,
  existing,
  onSubmit,
  isLoading,
}: MeetingLogFormProps) {
  const [title, setTitle] = useState(existing?.title ?? "");
  const [meetingDate, setMeetingDate] = useState(existing?.meeting_date ?? "");
  const [meetingTime, setMeetingTime] = useState(existing?.meeting_time ?? "");
  const [location, setLocation] = useState(existing?.location ?? "");
  const [channel, setChannel] = useState<string>(
    existing?.channel ?? "IN_PERSON",
  );
  const [status, setStatus] = useState<string>(existing?.status ?? "SCHEDULED");
  const [minutes, setMinutes] = useState(existing?.minutes ?? "");
  const [summary, setSummary] = useState(existing?.summary ?? "");
  const [marketingStage, setMarketingStage] = useState<MarketingStage | "">(
    existing?.marketing_stage ?? "",
  );

  const isMarketing = meetingPhase === "MARKETING";

  // existing prop 변경 시 폼 상태 동기화
  useEffect(() => {
    setTitle(existing?.title ?? "");
    setMeetingDate(existing?.meeting_date ?? "");
    setMeetingTime(existing?.meeting_time ?? "");
    setLocation(existing?.location ?? "");
    setChannel(existing?.channel ?? "IN_PERSON");
    setStatus(existing?.status ?? "SCHEDULED");
    setMinutes(existing?.minutes ?? "");
    setSummary(existing?.summary ?? "");
    setMarketingStage(existing?.marketing_stage ?? "");
  }, [existing]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim() || !meetingDate) return;

    if (existing) {
      const body: MeetingLogUpdate = {
        title: title.trim(),
        meeting_date: meetingDate,
        meeting_time: meetingTime || undefined,
        location: location.trim() || undefined,
        channel: channel as MeetingLogUpdate["channel"],
        status: status as MeetingLogUpdate["status"],
        minutes: minutes.trim() || undefined,
        summary: summary.trim() || undefined,
        marketing_stage: marketingStage ? (marketingStage as MarketingStage) : undefined,
      };
      onSubmit(body);
    } else {
      const body: MeetingLogCreate = {
        meeting_phase: meetingPhase,
        title: title.trim(),
        meeting_date: meetingDate,
        meeting_time: meetingTime || undefined,
        location: location.trim() || undefined,
        channel: channel as MeetingLogCreate["channel"],
        status: status as MeetingLogCreate["status"],
        minutes: minutes.trim() || undefined,
        summary: summary.trim() || undefined,
        marketing_stage: marketingStage ? (marketingStage as MarketingStage) : undefined,
      };
      onSubmit(body);
    }
  };

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={existing ? "미팅 로그 수정" : "새 미팅 로그"}
      size="lg"
    >
      <form onSubmit={handleSubmit} className="space-y-4">
        <Input
          label="제목"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="미팅 제목"
          required
        />
        <div className="grid grid-cols-2 gap-4">
          <Input
            label="미팅 일자"
            type="date"
            value={meetingDate}
            onChange={(e) => setMeetingDate(e.target.value)}
            required
          />
          <Input
            label="시간"
            type="time"
            value={meetingTime}
            onChange={(e) => setMeetingTime(e.target.value)}
          />
        </div>
        <Input
          label="장소"
          value={location}
          onChange={(e) => setLocation(e.target.value)}
          placeholder="미팅 장소"
        />
        <div className="grid grid-cols-2 gap-4">
          <Select
            label="채널"
            value={channel}
            onChange={(e) => setChannel(e.target.value)}
            options={MEETING_CHANNEL_OPTIONS}
          />
          <Select
            label="상태"
            value={status}
            onChange={(e) => setStatus(e.target.value)}
            options={MEETING_STATUS_OPTIONS}
          />
        </div>
        {isMarketing && (
          <Select
            label="마케팅 단계"
            value={marketingStage}
            onChange={(e) =>
              setMarketingStage(e.target.value as MarketingStage)
            }
            options={[
              { value: "", label: "선택 안 함" },
              ...MARKETING_STAGE_OPTIONS,
            ]}
          />
        )}
        <div>
          <label className="block text-sm font-medium text-text-dark mb-1">
            요약
          </label>
          <textarea
            className="w-full rounded-lg border border-gray-border bg-white px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
            rows={2}
            value={summary}
            onChange={(e) => setSummary(e.target.value)}
            placeholder="미팅 요약"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-text-dark mb-1">
            회의록
          </label>
          <textarea
            className="w-full rounded-lg border border-gray-border bg-white px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
            rows={5}
            value={minutes}
            onChange={(e) => setMinutes(e.target.value)}
            placeholder="회의록 내용"
          />
        </div>
        <div className="flex justify-end gap-2 pt-2">
          <Button type="button" variant="ghost" onClick={onClose}>
            취소
          </Button>
          <Button
            type="submit"
            disabled={isLoading || !title.trim() || !meetingDate}
          >
            {existing ? "수정" : "생성"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}
