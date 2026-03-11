import { useState } from "react";
import { Plus, Check } from "lucide-react";
import { Button } from "@/components/ui";
import { useCreateMeetingLog } from "@/modules/ma/hooks/useMeetingLogs";
import {
  MARKETING_STAGE_OPTIONS,
  MARKETING_STAGE_TITLE_LABELS,
} from "@/modules/ma/constants";
import type { MarketingStage } from "@/modules/ma/types/marketing_log";

interface InlineLogInputProps {
  txnId: string;
  buyerId: string;
  /** 그리드 셀에서 단계가 이미 결정된 경우 */
  defaultStage?: MarketingStage;
  /** 저장 완료 후 콜백 */
  onComplete?: () => void;
  /** Escape 키 등으로 입력 취소 시 콜백 */
  onCancel?: () => void;
  /** true: 날짜+저장만 (그리드 셀용), false: 전체 폼 */
  compact?: boolean;
}

function todayStr(): string {
  const d = new Date();
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

export default function InlineLogInput({
  txnId,
  buyerId,
  defaultStage,
  onComplete,
  onCancel,
  compact = false,
}: InlineLogInputProps) {
  const [stage, setStage] = useState<MarketingStage>(
    defaultStage ?? "IDENTIFIED",
  );
  const [logDate, setLogDate] = useState(todayStr());
  const [content, setContent] = useState("");

  const createLog = useCreateMeetingLog(txnId);

  const handleSubmit = () => {
    if (!logDate) return;
    const resolvedStage = defaultStage ?? stage;
    const stageLabel = MARKETING_STAGE_TITLE_LABELS[resolvedStage];
    const autoTitle = content
      ? `${stageLabel} — ${content.slice(0, 50)}`
      : stageLabel;

    createLog.mutate(
      {
        meeting_phase: "MARKETING",
        title: autoTitle,
        meeting_date: logDate,
        channel: "EMAIL",
        status: "COMPLETED",
        summary: content || undefined,
        buyer_id: buyerId,
        marketing_stage: resolvedStage,
      },
      {
        onSuccess: () => {
          setContent("");
          setLogDate(todayStr());
          onComplete?.();
        },
      },
    );
  };

  if (compact) {
    return (
      <div
        className="flex items-center gap-1"
        onKeyDown={(e) => {
          if (e.key === "Escape") onCancel?.();
        }}
      >
        <input
          type="date"
          value={logDate}
          onChange={(e) => setLogDate(e.target.value)}
          className="h-7 px-1.5 text-xs border border-gray-border rounded bg-white focus:ring-1 focus:ring-accent"
          aria-label="접촉 날짜"
        />
        <Button
          size="sm"
          variant="ghost"
          onClick={handleSubmit}
          loading={createLog.isPending}
          className="h-7 w-7 p-0"
          aria-label="로그 저장"
        >
          <Check className="h-3.5 w-3.5" />
        </Button>
      </div>
    );
  }

  return (
    <div
      className="flex items-center gap-2 p-2 bg-bg-cool rounded border border-gray-border"
      onKeyDown={(e) => {
        if (e.key === "Escape") onCancel?.();
      }}
    >
      {!defaultStage && (
        <select
          value={stage}
          onChange={(e) => setStage(e.target.value as MarketingStage)}
          className="h-7 px-1.5 text-xs border border-gray-border rounded bg-white focus:ring-1 focus:ring-accent"
          aria-label="접촉 유형"
        >
          {MARKETING_STAGE_OPTIONS.map((o) => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
        </select>
      )}
      <input
        type="date"
        value={logDate}
        onChange={(e) => setLogDate(e.target.value)}
        className="h-7 px-1.5 text-xs border border-gray-border rounded bg-white focus:ring-1 focus:ring-accent"
        aria-label="접촉 날짜"
      />
      <input
        type="text"
        value={content}
        onChange={(e) => setContent(e.target.value)}
        placeholder="활동 내용 (선택)"
        aria-label="활동 내용"
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
      >
        <Plus className="h-3 w-3 mr-1" />
        추가
      </Button>
    </div>
  );
}
