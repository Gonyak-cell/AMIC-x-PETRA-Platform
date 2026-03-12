import { useState } from "react";
import { Plus, X, Mic } from "lucide-react";
import {
  Button,
  Card,
  EmptyState,
  Spinner,
  KpiCard,
  Select,
  Badge,
} from "@/components/ui";
import { useAuth } from "@/hooks/useAuth";
import {
  useMeetingLogs,
  useMeetingLog,
  useMeetingLogSummary,
  useCreateMeetingLog,
  useUpdateMeetingLog,
  useDeleteMeetingLog,
  useCreateActionItem,
  useUpdateActionItem,
  useDeleteActionItem,
} from "@/modules/ma/hooks/useMeetingLogs";
import {
  useNegotiationIssues,
  useCreateNegotiationIssue,
  useUpdateNegotiationIssue,
  useDeleteNegotiationIssue,
  useAIClauseSuggestion,
} from "@/modules/ma/hooks/useNegotiationIssues";
import { MEETING_STATUS_OPTIONS } from "@/modules/ma/constants";
import type {
  MeetingPhase,
  MeetingLogCreate,
  MeetingLogUpdate,
  MeetingStatus,
} from "@/modules/ma/types/meeting_log";
import MeetingLogCard from "./MeetingLogCard";
import MeetingLogForm from "./MeetingLogForm";
import AttendeeList from "./AttendeeList";
import ActionItemList from "./ActionItemList";
import ConditionAssessment from "./ConditionAssessment";
import NegotiationIssuePanel from "./NegotiationIssuePanel";
import AudioTranscriptionModal from "./AudioTranscriptionModal";

interface MeetingLogsTabProps {
  txnId: string;
  meetingPhase: MeetingPhase;
  buyerId?: string;
  buyerName?: string;
  onClearBuyerFilter?: () => void;
}

export default function MeetingLogsTab({
  txnId,
  meetingPhase,
  buyerId,
  buyerName,
  onClearBuyerFilter,
}: MeetingLogsTabProps) {
  const { canWrite } = useAuth();
  const [statusFilter, setStatusFilter] = useState<MeetingStatus | "">("");
  const [showForm, setShowForm] = useState(false);
  const [showTranscription, setShowTranscription] = useState(false);
  const [selectedLogId, setSelectedLogId] = useState<string | null>(null);

  // 미팅 로그 데이터
  const {
    data: logs,
    isLoading,
    isError,
  } = useMeetingLogs(txnId, {
    meetingPhase,
    status: statusFilter || undefined,
    buyerId,
  });
  const { data: summary } = useMeetingLogSummary(txnId, meetingPhase);
  const { data: selectedLog, isLoading: isDetailLoading } = useMeetingLog(
    txnId,
    selectedLogId ?? "",
  );

  // 미팅 CRUD
  const createLog = useCreateMeetingLog(txnId);
  const updateLog = useUpdateMeetingLog(txnId);
  const deleteLog = useDeleteMeetingLog(txnId);

  // 액션아이템 CRUD
  const createAction = useCreateActionItem(txnId, selectedLogId ?? "");
  const updateAction = useUpdateActionItem(txnId, selectedLogId ?? "");
  const deleteAction = useDeleteActionItem(txnId, selectedLogId ?? "");

  // 협상 이견 (NEGOTIATION phase only)
  const { data: issuesData } = useNegotiationIssues(
    meetingPhase === "NEGOTIATION" ? txnId : "",
  );
  const createIssue = useCreateNegotiationIssue(txnId);
  const updateIssue = useUpdateNegotiationIssue(txnId);
  const deleteIssue = useDeleteNegotiationIssue(txnId);
  const aiSuggest = useAIClauseSuggestion(txnId);

  const handleCreate = (body: MeetingLogCreate | MeetingLogUpdate) => {
    createLog.mutate(body as MeetingLogCreate, {
      onSuccess: () => setShowForm(false),
    });
  };

  const handleUpdate = (body: MeetingLogCreate | MeetingLogUpdate) => {
    if (!selectedLogId) return;
    updateLog.mutate(
      { logId: selectedLogId, body: body as MeetingLogUpdate },
      {
        onSuccess: () => setShowForm(false),
      },
    );
  };

  if (isLoading) return <Spinner size="lg" />;
  if (isError)
    return (
      <EmptyState
        title="데이터를 불러올 수 없습니다"
        description="네트워크 오류가 발생했습니다. 잠시 후 다시 시도해 주세요."
      />
    );

  const statusOptions = [
    { value: "", label: "전체" },
    ...MEETING_STATUS_OPTIONS,
  ];
  const phaseLabel = meetingPhase === "MARKETING" ? "마케팅" : "협상";

  return (
    <div className="space-y-6">
      {/* KPI 요약 */}
      {summary && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          <KpiCard label="전체 미팅" value={String(summary.total)} />
          <KpiCard
            label="완료"
            value={String(summary.by_status?.COMPLETED ?? 0)}
            variant="good"
          />
          <KpiCard
            label="예정"
            value={String(summary.by_status?.SCHEDULED ?? 0)}
            variant="warning"
          />
          <KpiCard
            label="취소/연기"
            value={String(
              (summary.by_status?.CANCELLED ?? 0) +
                (summary.by_status?.POSTPONED ?? 0),
            )}
            variant="bad"
          />
        </div>
      )}

      {/* 필터 + 생성 버튼 */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Select
            value={statusFilter}
            onChange={(e) =>
              setStatusFilter(e.target.value as MeetingStatus | "")
            }
            options={statusOptions}
            className="w-36"
          />
          {buyerId && (
            <Badge
              variant="info"
              className="flex items-center gap-1 pl-2 pr-1 py-1"
            >
              <span className="text-xs">
                {buyerName || "매수자"} 필터 적용 중
              </span>
              {onClearBuyerFilter && (
                <button
                  onClick={onClearBuyerFilter}
                  className="ml-1 rounded-full p-0.5 hover:bg-primary-200 transition-colors"
                  aria-label="필터 해제"
                >
                  <X className="w-3 h-3" />
                </button>
              )}
            </Badge>
          )}
        </div>
        {canWrite() && (
          <div className="flex gap-2">
            <Button
              variant="ghost"
              icon={Mic}
              onClick={() => setShowTranscription(true)}
            >
              녹음 변환
            </Button>
            <Button
              icon={Plus}
              onClick={() => {
                setSelectedLogId(null);
                setShowForm(true);
              }}
            >
              로그 추가
            </Button>
          </div>
        )}
      </div>

      {/* 상세 뷰 — 선택된 미팅 */}
      {selectedLogId && selectedLog && !isDetailLoading && (
        <Card className="p-5 space-y-5 border-primary-200">
          <div className="flex items-center justify-between">
            <h3 className="text-base font-heading font-semibold">
              {selectedLog.title}
            </h3>
            <div className="flex gap-2">
              {canWrite() && (
                <>
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => setShowForm(true)}
                  >
                    수정
                  </Button>
                  <Button
                    size="sm"
                    variant="ghost"
                    className="text-red-500"
                    onClick={() => {
                      deleteLog.mutate(selectedLogId);
                      setSelectedLogId(null);
                    }}
                  >
                    삭제
                  </Button>
                </>
              )}
              <Button
                size="sm"
                variant="ghost"
                onClick={() => setSelectedLogId(null)}
              >
                닫기
              </Button>
            </div>
          </div>

          {/* 회의록 */}
          {selectedLog.minutes && (
            <div>
              <h4 className="text-sm font-semibold text-text-dark mb-1">
                회의록
              </h4>
              <div className="rounded-lg bg-gray-50 border border-gray-border p-3 text-sm whitespace-pre-wrap">
                {selectedLog.minutes}
              </div>
            </div>
          )}

          {/* 마케팅: 조건 평가 */}
          {meetingPhase === "MARKETING" && (
            <ConditionAssessment
              conditionMatch={selectedLog.condition_match}
              conditionNotes={selectedLog.condition_notes}
            />
          )}

          {/* 참석자 */}
          <AttendeeList
            attendees={selectedLog.attendees}
            meetingPhase={meetingPhase}
            canWrite={false}
            onAdd={() => {}}
            onDelete={() => {}}
          />

          {/* 액션아이템 */}
          <ActionItemList
            items={selectedLog.action_items}
            canWrite={canWrite()}
            onAdd={(body) => createAction.mutate(body)}
            onUpdate={(itemId, body) => updateAction.mutate({ itemId, body })}
            onDelete={(itemId) => deleteAction.mutate(itemId)}
          />

          {/* 제공 자료 */}
          {selectedLog.provided_materials &&
            selectedLog.provided_materials.length > 0 && (
              <div>
                <h4 className="text-sm font-semibold text-text-dark mb-1">
                  제공 자료
                </h4>
                <ul className="space-y-1">
                  {selectedLog.provided_materials.map((m, i) => (
                    <li
                      key={i}
                      className="text-xs text-text-secondary flex items-center gap-1"
                    >
                      <span className="font-medium">{m.name}</span>
                      {m.description && <span>— {m.description}</span>}
                    </li>
                  ))}
                </ul>
              </div>
            )}
        </Card>
      )}

      {/* 미팅 목록 */}
      {!selectedLogId && (
        <>
          {!logs?.items || logs.items.length === 0 ? (
            <EmptyState
              title={`${phaseLabel} 미팅 로그가 없습니다`}
              description="미팅을 추가하여 기록을 시작하세요."
            />
          ) : (
            <div className="space-y-2">
              {logs.items.map((meeting) => (
                <MeetingLogCard
                  key={meeting.id}
                  meeting={meeting}
                  onClick={() => setSelectedLogId(meeting.id)}
                />
              ))}
            </div>
          )}
        </>
      )}

      {/* 협상 이견 패널 (NEGOTIATION only) */}
      {meetingPhase === "NEGOTIATION" && issuesData && (
        <NegotiationIssuePanel
          issues={issuesData.items}
          canWrite={canWrite()}
          onCreate={(body) => createIssue.mutate(body)}
          onUpdate={(id, body) => updateIssue.mutate({ issueId: id, body })}
          onDelete={(id) => deleteIssue.mutate(id)}
          onAISuggest={(id) => aiSuggest.mutate(id)}
          isAISuggestPending={aiSuggest.isPending}
        />
      )}

      {/* 녹음 변환 모달 */}
      <AudioTranscriptionModal
        open={showTranscription}
        onClose={() => setShowTranscription(false)}
        txnId={txnId}
        meetingPhase={meetingPhase}
        buyerId={buyerId}
      />

      {/* 생성/수정 모달 */}
      <MeetingLogForm
        open={showForm}
        onClose={() => setShowForm(false)}
        meetingPhase={meetingPhase}
        existing={selectedLogId ? (selectedLog ?? null) : null}
        onSubmit={selectedLogId ? handleUpdate : handleCreate}
        isLoading={createLog.isPending || updateLog.isPending}
        txnId={txnId}
      />
    </div>
  );
}
