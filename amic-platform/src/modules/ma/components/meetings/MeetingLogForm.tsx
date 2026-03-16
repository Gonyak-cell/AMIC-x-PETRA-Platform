import { useState, useEffect } from "react";
import { Plus, Trash2 } from "lucide-react";
import { Button, Input, Select, Modal } from "@/components/ui";
import {
  MEETING_CHANNEL_OPTIONS,
  MEETING_STATUS_OPTIONS,
  MARKETING_STAGE_OPTIONS,
} from "@/modules/ma/constants";
import { MEETING_TYPE_OPTIONS } from "@/modules/ma/constants/meeting";
import {
  useMeetingLog,
  useAddAttendee,
  useUpdateAttendee,
  useDeleteAttendee,
} from "@/modules/ma/hooks/useMeetingLogs";
import type {
  MeetingPhase,
  MeetingType,
  MeetingLogCreate,
  MeetingLogUpdate,
  MeetingLog,
  MeetingAttendeeCreate,
} from "@/modules/ma/types/meeting_log";
import type { MarketingStage } from "@/modules/ma/types/marketing_log";
import AttendeeList from "./AttendeeList";

interface MeetingLogFormProps {
  open: boolean;
  onClose: () => void;
  meetingPhase: MeetingPhase;
  existing?: MeetingLog | null;
  onSubmit: (body: MeetingLogCreate | MeetingLogUpdate) => void;
  isLoading?: boolean;
  txnId?: string;
  /** buyer 컨텍스트 — BuyersTab에서 빠른 활동 추가 시 pre-fill */
  buyerId?: string;
  buyerName?: string;
  /** true면 buyer 선택 필드를 disabled로 표시 */
  lockBuyer?: boolean;
}

export default function MeetingLogForm({
  open,
  onClose,
  meetingPhase,
  existing,
  onSubmit,
  isLoading,
  txnId,
  buyerId,
  buyerName,
  lockBuyer,
}: MeetingLogFormProps) {
  const [title, setTitle] = useState(existing?.title ?? "");
  const [meetingDate, setMeetingDate] = useState(existing?.meeting_date ?? "");
  const [meetingTime, setMeetingTime] = useState(existing?.meeting_time ?? "");
  const [location, setLocation] = useState(existing?.location ?? "");
  const [channel, setChannel] = useState<string>(
    existing?.channel ?? "IN_PERSON",
  );
  const [meetingType, setMeetingType] = useState<string>(
    existing?.meeting_type ?? "MEETING",
  );
  const [status, setStatus] = useState<string>(existing?.status ?? "SCHEDULED");
  const [minutes, setMinutes] = useState(existing?.minutes ?? "");
  const [summary, setSummary] = useState(existing?.summary ?? "");
  const [marketingStage, setMarketingStage] = useState<MarketingStage | "">(
    existing?.marketing_stage ?? "",
  );
  const [attendees, setAttendees] = useState<
    { name: string; organization: string; role: string }[]
  >([]);

  const isMarketing = meetingPhase === "MARKETING";
  const isEditMode = !!existing;
  const logId = existing?.id ?? "";

  // 수정 모드: 기존 참석자 로딩
  const { data: logDetail } = useMeetingLog(txnId ?? "", logId);
  const addAttendee = useAddAttendee(txnId ?? "", logId);
  const updateAttendee = useUpdateAttendee(txnId ?? "", logId);
  const deleteAttendee = useDeleteAttendee(txnId ?? "", logId);

  // existing prop 변경 시 폼 상태 동기화
  useEffect(() => {
    setTitle(existing?.title ?? "");
    setMeetingDate(existing?.meeting_date ?? "");
    setMeetingTime(existing?.meeting_time ?? "");
    setLocation(existing?.location ?? "");
    setChannel(existing?.channel ?? "IN_PERSON");
    setMeetingType(existing?.meeting_type ?? "MEETING");
    setStatus(existing?.status ?? "SCHEDULED");
    setMinutes(existing?.minutes ?? "");
    setSummary(existing?.summary ?? "");
    setMarketingStage(existing?.marketing_stage ?? "");
    setAttendees([]);
  }, [existing]);

  const addLocalAttendee = () => {
    setAttendees((prev) => [...prev, { name: "", organization: "", role: "" }]);
  };

  const removeLocalAttendee = (idx: number) => {
    setAttendees((prev) => prev.filter((_, i) => i !== idx));
  };

  const updateLocalAttendee = (
    idx: number,
    field: "name" | "organization" | "role",
    value: string,
  ) => {
    setAttendees((prev) =>
      prev.map((a, i) => (i === idx ? { ...a, [field]: value } : a)),
    );
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim() || !meetingDate) return;

    const validAttendees: MeetingAttendeeCreate[] = attendees
      .filter((a) => a.name.trim())
      .map((a) => ({
        name: a.name.trim(),
        organization: a.organization.trim() || undefined,
        role: undefined,
      }));

    if (existing) {
      const body: MeetingLogUpdate = {
        title: title.trim(),
        meeting_date: meetingDate,
        meeting_time: meetingTime || undefined,
        location: location.trim() || undefined,
        channel: channel as MeetingLogUpdate["channel"],
        meeting_type: meetingType as MeetingType,
        status: status as MeetingLogUpdate["status"],
        minutes: minutes.trim() || undefined,
        summary: summary.trim() || undefined,
        marketing_stage: marketingStage
          ? (marketingStage as MarketingStage)
          : undefined,
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
        meeting_type: meetingType as MeetingType,
        status: status as MeetingLogCreate["status"],
        minutes: minutes.trim() || undefined,
        summary: summary.trim() || undefined,
        marketing_stage: marketingStage
          ? (marketingStage as MarketingStage)
          : undefined,
        buyer_id: buyerId || undefined,
        attendees: validAttendees.length > 0 ? validAttendees : undefined,
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
        {/* buyer 컨텍스트 표시 (lockBuyer 모드) */}
        {lockBuyer && buyerName && (
          <div className="rounded-lg bg-bg-cool px-3 py-2 text-xs text-text-secondary">
            매수자:{" "}
            <span className="font-medium text-text-dark">{buyerName}</span>
          </div>
        )}
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
        <div className="grid grid-cols-3 gap-4">
          <Select
            label="채널"
            value={channel}
            onChange={(e) => setChannel(e.target.value)}
            options={MEETING_CHANNEL_OPTIONS}
          />
          <Select
            label="유형"
            value={meetingType}
            onChange={(e) => setMeetingType(e.target.value)}
            options={MEETING_TYPE_OPTIONS}
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
          <label
            htmlFor="meeting-summary"
            className="block text-sm font-medium text-text-dark mb-1"
          >
            요약
          </label>
          <textarea
            id="meeting-summary"
            className="w-full rounded-lg border border-gray-border bg-white px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
            rows={2}
            value={summary}
            onChange={(e) => setSummary(e.target.value)}
            placeholder="미팅 요약"
          />
        </div>
        <div>
          <label
            htmlFor="meeting-minutes"
            className="block text-sm font-medium text-text-dark mb-1"
          >
            회의록
          </label>
          <textarea
            id="meeting-minutes"
            className="w-full rounded-lg border border-gray-border bg-white px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
            rows={5}
            value={minutes}
            onChange={(e) => setMinutes(e.target.value)}
            placeholder="회의록 내용"
          />
        </div>

        {/* 참석자 섹션 */}
        {isEditMode && txnId && logDetail ? (
          /* 수정 모드: API 연동 AttendeeList */
          <AttendeeList
            attendees={logDetail.attendees ?? []}
            meetingPhase={meetingPhase}
            canWrite
            onAdd={(body) => addAttendee.mutate(body)}
            onUpdate={(attId, body) =>
              updateAttendee.mutate({ attendeeId: attId, body })
            }
            onDelete={(attId) => deleteAttendee.mutate(attId)}
          />
        ) : (
          /* 생성 모드: 인라인 참석자 폼 */
          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="block text-sm font-medium text-text-dark">
                참석자
              </label>
              <Button
                type="button"
                size="sm"
                variant="ghost"
                onClick={addLocalAttendee}
                className="text-xs"
              >
                <Plus className="h-3 w-3 mr-1" />
                참석자 추가
              </Button>
            </div>
            {attendees.length === 0 && (
              <p className="text-xs text-gray-400">
                참석자가 없습니다. 위 버튼으로 추가하세요.
              </p>
            )}
            <div className="space-y-2">
              {attendees.map((att, idx) => (
                <div key={idx} className="flex items-center gap-2">
                  <input
                    type="text"
                    value={att.name}
                    onChange={(e) =>
                      updateLocalAttendee(idx, "name", e.target.value)
                    }
                    placeholder="이름"
                    aria-label={`참석자 ${idx + 1} 이름`}
                    className="h-8 flex-1 min-w-0 px-2 text-sm border border-gray-border rounded bg-white focus:ring-1 focus:ring-primary-500"
                  />
                  <input
                    type="text"
                    value={att.organization}
                    onChange={(e) =>
                      updateLocalAttendee(idx, "organization", e.target.value)
                    }
                    placeholder="소속"
                    aria-label={`참석자 ${idx + 1} 소속`}
                    className="h-8 flex-1 min-w-0 px-2 text-sm border border-gray-border rounded bg-white focus:ring-1 focus:ring-primary-500"
                  />
                  <button
                    type="button"
                    onClick={() => removeLocalAttendee(idx)}
                    className="p-1 text-gray-400 hover:text-red-500 transition-colors"
                    aria-label={`참석자 ${idx + 1}${att.name ? ` ${att.name}` : ""} 삭제`}
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </button>
                </div>
              ))}
            </div>
          </div>
        )}

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
