import { useState, useEffect, useCallback, useRef } from "react";
import { Upload, Mic, Check, AlertTriangle, Loader2, Trash2, Plus } from "lucide-react";
import { Button, Modal, Input, Select, Badge } from "@/components/ui";
import { useBuyers } from "@/modules/ma/hooks/useTransactions";
import {
  useStartTranscription,
  useTranscriptionStatus,
  useApproveTranscription,
} from "@/modules/ma/hooks/useTranscription";
import type { MeetingPhase, AttendeeRole } from "@/modules/ma/types/meeting_log";
import type {
  TranscriptionJob,
  ActionItemDraft,
  TranscriptionApprovalPayload,
} from "@/modules/ma/types/transcription";

const ACCEPTED_AUDIO = ".mp3,.wav,.m4a,.webm,.ogg,.flac";
const MAX_SIZE_MB = 100;

const ATTENDEE_ROLE_OPTIONS = [
  { value: "SELLER_ADVISOR", label: "매도측 어드바이저" },
  { value: "BUYER_ADVISOR", label: "매수측 어드바이저" },
  { value: "LEGAL_COUNSEL", label: "법률 자문" },
  { value: "CLIENT_REPRESENTATIVE", label: "고객 담당자" },
  { value: "COUNTERPARTY", label: "상대방" },
  { value: "OBSERVER", label: "옵저버" },
  { value: "OTHER", label: "기타" },
];

const REACTION_OPTIONS = [
  { value: "", label: "선택" },
  { value: "VERY_POSITIVE", label: "매우 긍정" },
  { value: "POSITIVE", label: "긍정" },
  { value: "NEUTRAL", label: "중립" },
  { value: "NEGATIVE", label: "부정" },
  { value: "VERY_NEGATIVE", label: "매우 부정" },
];

const CONDITION_OPTIONS = [
  { value: "", label: "선택" },
  { value: "FULL_MATCH", label: "완전 부합" },
  { value: "PARTIAL_MATCH", label: "부분 부합" },
  { value: "MISMATCH", label: "불일치" },
];

type Step = "info" | "upload" | "processing" | "review";

interface AttendeeInput {
  name: string;
  email: string;
  organization: string;
  role: AttendeeRole;
}

interface Props {
  open: boolean;
  onClose: () => void;
  txnId: string;
  meetingPhase: MeetingPhase;
  buyerId?: string;
}

export default function AudioTranscriptionModal({ open, onClose, txnId, meetingPhase, buyerId }: Props) {
  const [step, setStep] = useState<Step>("info");

  // Step 1: 미팅 정보
  const [title, setTitle] = useState("");
  const [meetingDate, setMeetingDate] = useState(new Date().toISOString().slice(0, 10));
  const [selectedBuyerId, setSelectedBuyerId] = useState(buyerId ?? "");
  const [attendees, setAttendees] = useState<AttendeeInput[]>([
    { name: "", email: "", organization: "", role: "SELLER_ADVISOR" },
  ]);

  // Step 2: 파일
  const [audioFile, setAudioFile] = useState<File | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Step 3: 처리 중
  const [jobId, setJobId] = useState<string | null>(null);

  // Step 4: 리뷰
  const [editMinutes, setEditMinutes] = useState("");
  const [editSummary, setEditSummary] = useState("");
  const [editActions, setEditActions] = useState<ActionItemDraft[]>([]);
  const [conditionMatch, setConditionMatch] = useState("");
  const [conditionNotes, setConditionNotes] = useState("");
  const [buyerReaction, setBuyerReaction] = useState("");

  const { data: buyers } = useBuyers(txnId);
  const startMutation = useStartTranscription(txnId);
  const approveMutation = useApproveTranscription(txnId);

  // 폴링: 처리 중일 때만
  const shouldPoll = step === "processing" && !!jobId;
  const { data: jobStatus } = useTranscriptionStatus(txnId, jobId, {
    enabled: shouldPoll,
    refetchInterval: shouldPoll ? 3000 : false,
  });

  // 처리 완료 시 리뷰 단계로 전환
  useEffect(() => {
    if (!jobStatus) return;
    if (jobStatus.status === "COMPLETED") {
      const mj = jobStatus.minutes_json;
      setEditMinutes(mj?.minutes ?? "");
      setEditSummary(mj?.summary ?? "");
      setEditActions(mj?.action_items ?? []);
      setConditionMatch(mj?.condition_assessment?.match_level ?? "");
      setConditionNotes(mj?.condition_assessment?.notes ?? "");
      setBuyerReaction(mj?.buyer_reaction ?? "");
      setStep("review");
    } else if (jobStatus.status === "FAILED") {
      // 에러 상태 유지 — processing 단계에서 에러 메시지 표시
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [jobStatus?.status]);

  // 모달 닫힐 때 리셋
  useEffect(() => {
    if (!open) {
      setStep("info");
      setTitle("");
      setMeetingDate(new Date().toISOString().slice(0, 10));
      setSelectedBuyerId(buyerId ?? "");
      setAttendees([{ name: "", email: "", organization: "", role: "SELLER_ADVISOR" }]);
      setAudioFile(null);
      setJobId(null);
      setEditMinutes("");
      setEditSummary("");
      setEditActions([]);
      setConditionMatch("");
      setConditionNotes("");
      setBuyerReaction("");
    }
  }, [open, buyerId]);

  // ── 핸들러 ──

  const addAttendee = () => {
    setAttendees([...attendees, { name: "", email: "", organization: "", role: "OTHER" }]);
  };

  const removeAttendee = (idx: number) => {
    setAttendees(attendees.filter((_, i) => i !== idx));
  };

  const updateAttendee = (idx: number, field: keyof AttendeeInput, value: string) => {
    const next = [...attendees];
    next[idx] = { ...next[idx], [field]: value };
    setAttendees(next);
  };

  const handleFileDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    const file = e.dataTransfer.files[0];
    if (file && file.size <= MAX_SIZE_MB * 1024 * 1024) {
      setAudioFile(file);
    }
  }, []);

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file && file.size <= MAX_SIZE_MB * 1024 * 1024) {
      setAudioFile(file);
    }
  };

  const handleStartTranscription = () => {
    if (!audioFile) return;
    const validAttendees = attendees.filter((a) => a.name.trim());
    startMutation.mutate(
      {
        audio: audioFile,
        title,
        meeting_date: meetingDate,
        meeting_phase: meetingPhase,
        buyer_id: selectedBuyerId || undefined,
        attendees_json: JSON.stringify(validAttendees),
      },
      {
        onSuccess: (job: TranscriptionJob) => {
          setJobId(job.id);
          setStep("processing");
        },
      },
    );
  };

  const handleApprove = () => {
    if (!jobId) return;
    const body: TranscriptionApprovalPayload = {
      minutes: editMinutes,
      summary: editSummary || undefined,
      action_items: editActions.length > 0 ? editActions : undefined,
      condition_match: conditionMatch || undefined,
      condition_notes: conditionNotes || undefined,
      buyer_reaction: buyerReaction || undefined,
    };
    approveMutation.mutate({ jobId, body }, { onSuccess: () => onClose() });
  };

  const updateAction = (idx: number, field: keyof ActionItemDraft, value: string | null) => {
    const next = [...editActions];
    next[idx] = { ...next[idx], [field]: value };
    setEditActions(next);
  };

  const addAction = () => {
    setEditActions([
      ...editActions,
      { title: "", description: null, assignee_name: null, assignee_email: null, due_date: null, priority: "MEDIUM" },
    ]);
  };

  const removeAction = (idx: number) => {
    setEditActions(editActions.filter((_, i) => i !== idx));
  };

  // ── 유효성 ──
  const canProceedToUpload = title.trim().length > 0 && meetingDate.length === 10;
  const canStartProcessing = !!audioFile;

  // ── 스텝 인디케이터 ──
  const steps: { id: Step; label: string }[] = [
    { id: "info", label: "미팅 정보" },
    { id: "upload", label: "파일 업로드" },
    { id: "processing", label: "처리 중" },
    { id: "review", label: "결과 검토" },
  ];
  const stepIdx = steps.findIndex((s) => s.id === step);

  const buyerOptions = [
    { value: "", label: "선택 안 함" },
    ...(buyers?.map((b) => ({ value: b.id, label: b.company_name })) ?? []),
  ];

  return (
    <Modal open={open} onClose={onClose} title="녹음 변환 — 자동 회의록" size="lg">
      {/* 스텝 인디케이터 */}
      <div className="flex items-center gap-1 mb-6">
        {steps.map((s, i) => (
          <div key={s.id} className="flex items-center gap-1">
            <div
              className={`flex items-center justify-center w-7 h-7 rounded-full text-xs font-semibold ${
                i < stepIdx
                  ? "bg-accent text-white"
                  : i === stepIdx
                    ? "bg-primary-600 text-white"
                    : "bg-gray-200 text-text-secondary"
              }`}
            >
              {i < stepIdx ? <Check className="w-3.5 h-3.5" /> : i + 1}
            </div>
            <span className={`text-xs ${i === stepIdx ? "text-primary-600 font-semibold" : "text-text-secondary"}`}>
              {s.label}
            </span>
            {i < steps.length - 1 && <div className="w-6 h-px bg-gray-300 mx-1" />}
          </div>
        ))}
      </div>

      {/* ── Step 1: 미팅 정보 ── */}
      {step === "info" && (
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-medium text-text-dark mb-1">미팅 제목 *</label>
              <Input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="예: OO사 1차 미팅" />
            </div>
            <div>
              <label className="block text-xs font-medium text-text-dark mb-1">미팅 일자 *</label>
              <Input type="date" value={meetingDate} onChange={(e) => setMeetingDate(e.target.value)} />
            </div>
          </div>

          <div>
            <label className="block text-xs font-medium text-text-dark mb-1">매수자</label>
            <Select value={selectedBuyerId} onChange={(e) => setSelectedBuyerId(e.target.value)} options={buyerOptions} />
          </div>

          {/* 참석자 */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="text-xs font-medium text-text-dark">참석자</label>
              <button onClick={addAttendee} className="text-xs text-primary-600 hover:underline flex items-center gap-0.5">
                <Plus className="w-3 h-3" /> 추가
              </button>
            </div>
            <div className="space-y-2 max-h-48 overflow-y-auto">
              {attendees.map((att, i) => (
                <div key={i} className="flex items-center gap-2">
                  <Input
                    className="flex-1"
                    placeholder="이름"
                    value={att.name}
                    onChange={(e) => updateAttendee(i, "name", e.target.value)}
                  />
                  <Input
                    className="flex-1"
                    placeholder="소속"
                    value={att.organization}
                    onChange={(e) => updateAttendee(i, "organization", e.target.value)}
                  />
                  <select
                    className="border border-gray-border rounded-dr px-2 py-1.5 text-xs bg-white"
                    value={att.role}
                    onChange={(e) => updateAttendee(i, "role", e.target.value)}
                  >
                    {ATTENDEE_ROLE_OPTIONS.map((o) => (
                      <option key={o.value} value={o.value}>{o.label}</option>
                    ))}
                  </select>
                  {attendees.length > 1 && (
                    <button onClick={() => removeAttendee(i)} className="text-red-400 hover:text-red-600 p-1">
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  )}
                </div>
              ))}
            </div>
          </div>

          <div className="flex justify-end pt-2">
            <Button onClick={() => setStep("upload")} disabled={!canProceedToUpload}>
              다음
            </Button>
          </div>
        </div>
      )}

      {/* ── Step 2: 파일 업로드 ── */}
      {step === "upload" && (
        <div className="space-y-4">
          <div
            className="border-2 border-dashed border-gray-300 rounded-dr p-8 text-center cursor-pointer hover:border-primary-400 transition-colors"
            onDragOver={(e) => e.preventDefault()}
            onDrop={handleFileDrop}
            onClick={() => fileInputRef.current?.click()}
          >
            {audioFile ? (
              <div className="flex flex-col items-center gap-2">
                <Mic className="w-10 h-10 text-accent" />
                <p className="text-sm font-medium text-text-dark">{audioFile.name}</p>
                <p className="text-xs text-text-secondary">
                  {(audioFile.size / (1024 * 1024)).toFixed(1)} MB
                </p>
                <button
                  onClick={(e) => { e.stopPropagation(); setAudioFile(null); }}
                  className="text-xs text-red-500 hover:underline"
                >
                  파일 제거
                </button>
              </div>
            ) : (
              <div className="flex flex-col items-center gap-2">
                <Upload className="w-10 h-10 text-gray-400" />
                <p className="text-sm text-text-secondary">
                  오디오 파일을 드래그하거나 클릭하여 선택하세요
                </p>
                <p className="text-xs text-text-secondary">
                  MP3, WAV, M4A, WebM, OGG, FLAC — 최대 {MAX_SIZE_MB}MB
                </p>
              </div>
            )}
            <input
              ref={fileInputRef}
              type="file"
              accept={ACCEPTED_AUDIO}
              className="hidden"
              onChange={handleFileSelect}
            />
          </div>

          <div className="flex justify-between pt-2">
            <Button variant="ghost" onClick={() => setStep("info")}>
              이전
            </Button>
            <Button
              onClick={handleStartTranscription}
              disabled={!canStartProcessing || startMutation.isPending}
              loading={startMutation.isPending}
            >
              변환 시작
            </Button>
          </div>
        </div>
      )}

      {/* ── Step 3: 처리 중 ── */}
      {step === "processing" && (
        <div className="flex flex-col items-center justify-center py-12 space-y-4">
          {jobStatus?.status === "FAILED" ? (
            <>
              <AlertTriangle className="w-12 h-12 text-red-500" />
              <p className="text-sm font-semibold text-red-600">변환에 실패했습니다</p>
              <p className="text-xs text-text-secondary text-center max-w-sm">
                {jobStatus.error_message || "알 수 없는 오류가 발생했습니다."}
              </p>
              <Button variant="ghost" onClick={onClose}>
                닫기
              </Button>
            </>
          ) : (
            <>
              <Loader2 className="w-12 h-12 text-primary-600 animate-spin" />
              <p className="text-sm font-semibold text-text-dark">
                {jobStatus?.status === "TRANSCRIBING" && "음성을 텍스트로 변환하고 있습니다..."}
                {jobStatus?.status === "ANALYZING" && "LLM이 회의록을 작성하고 있습니다..."}
                {(!jobStatus || jobStatus.status === "PENDING") && "변환 준비 중..."}
              </p>
              <div className="flex gap-2">
                {["TRANSCRIBING", "ANALYZING"].map((s) => (
                  <Badge
                    key={s}
                    variant={
                      jobStatus?.status === s
                        ? "info"
                        : steps.findIndex((st) => st.id === "processing") > 0
                          ? "success"
                          : "neutral"
                    }
                    className="text-xs"
                  >
                    {s === "TRANSCRIBING" ? "STT 변환" : "LLM 분석"}
                  </Badge>
                ))}
              </div>
              <p className="text-xs text-text-secondary">
                파일 크기에 따라 1~5분 정도 소요됩니다
              </p>
            </>
          )}
        </div>
      )}

      {/* ── Step 4: 결과 검토 ── */}
      {step === "review" && (
        <div className="space-y-4 max-h-[60vh] overflow-y-auto pr-1">
          {/* 회의록 */}
          <div>
            <label className="block text-xs font-semibold text-text-dark mb-1">회의록</label>
            <textarea
              className="w-full border border-gray-border rounded-dr p-3 text-sm min-h-[160px] resize-y"
              value={editMinutes}
              onChange={(e) => setEditMinutes(e.target.value)}
            />
          </div>

          {/* 요약 */}
          <div>
            <label className="block text-xs font-semibold text-text-dark mb-1">요약</label>
            <textarea
              className="w-full border border-gray-border rounded-dr p-2 text-sm min-h-[60px] resize-y"
              value={editSummary}
              onChange={(e) => setEditSummary(e.target.value)}
            />
          </div>

          {/* 조건 평가 + 매수자 반응 */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-text-dark mb-1">조건 부합도</label>
              <Select
                value={conditionMatch}
                onChange={(e) => setConditionMatch(e.target.value)}
                options={CONDITION_OPTIONS}
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-text-dark mb-1">매수자 반응</label>
              <Select
                value={buyerReaction}
                onChange={(e) => setBuyerReaction(e.target.value)}
                options={REACTION_OPTIONS}
              />
            </div>
          </div>

          {conditionMatch && (
            <div>
              <label className="block text-xs font-semibold text-text-dark mb-1">조건 상세</label>
              <Input
                value={conditionNotes}
                onChange={(e) => setConditionNotes(e.target.value)}
                placeholder="조건 관련 메모"
              />
            </div>
          )}

          {/* 액션아이템 */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="text-xs font-semibold text-text-dark">액션아이템</label>
              <button onClick={addAction} className="text-xs text-primary-600 hover:underline flex items-center gap-0.5">
                <Plus className="w-3 h-3" /> 추가
              </button>
            </div>
            <div className="space-y-2">
              {editActions.map((action, i) => (
                <div key={i} className="border border-gray-200 rounded-dr p-2 space-y-1">
                  <div className="flex items-center gap-2">
                    <Input
                      className="flex-1"
                      placeholder="제목"
                      value={action.title}
                      onChange={(e) => updateAction(i, "title", e.target.value)}
                    />
                    <Input
                      className="w-28"
                      placeholder="담당자"
                      value={action.assignee_name ?? ""}
                      onChange={(e) => updateAction(i, "assignee_name", e.target.value)}
                    />
                    <Input
                      type="date"
                      className="w-32"
                      value={action.due_date ?? ""}
                      onChange={(e) => updateAction(i, "due_date", e.target.value || null)}
                    />
                    <button onClick={() => removeAction(i)} className="text-red-400 hover:text-red-600 p-1">
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                  {action.description && (
                    <p className="text-xs text-text-secondary pl-1">{action.description}</p>
                  )}
                </div>
              ))}
              {editActions.length === 0 && (
                <p className="text-xs text-text-secondary">액션아이템이 없습니다</p>
              )}
            </div>
          </div>

          {/* 비용 정보 */}
          {jobStatus && (
            <div className="flex gap-4 text-xs text-text-secondary pt-1">
              <span>STT 비용: ₩{jobStatus.stt_cost_krw.toLocaleString()}</span>
              <span>LLM 비용: ${jobStatus.llm_cost_usd.toFixed(4)}</span>
            </div>
          )}

          <div className="flex justify-between pt-2">
            <Button variant="ghost" onClick={onClose}>
              취소
            </Button>
            <Button
              onClick={handleApprove}
              disabled={!editMinutes.trim() || approveMutation.isPending}
              loading={approveMutation.isPending}
            >
              회의록 확정
            </Button>
          </div>
        </div>
      )}
    </Modal>
  );
}
