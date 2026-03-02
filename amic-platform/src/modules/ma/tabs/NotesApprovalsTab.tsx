import { useState } from "react";
import {
  Plus,
  Trash2,
  Shield,
  MessageSquare,
  Pin,
  Check,
  X,
  Send,
} from "lucide-react";
import {
  useNotes,
  useCreateNote,
  useDeleteNote,
} from "@/modules/ma/hooks/useNotes";
import {
  useApprovals,
  useApprovalSummary,
  useCreateApproval,
  useDecideApproval,
  useCancelApproval,
} from "@/modules/ma/hooks/useApprovals";
import type { NoteCreate, NoteType } from "@/modules/ma/types/note";
import type {
  ApprovalCreate,
  ApprovalType as AppType,
} from "@/modules/ma/types/approval";
import {
  NOTE_TYPE_OPTIONS,
  APPROVAL_TYPE_OPTIONS,
  APPROVAL_STATUS_OPTIONS,
} from "@/modules/ma/constants";

import {
  Badge,
  Button,
  Card,
  EmptyState,
  Input,
  KpiCard,
  Modal,
  Select,
} from "@/components/ui";

import { formatISODate as formatDate } from "@/modules/ma/utils/format";

interface NotesApprovalsTabProps {
  txnId: string;
  canWrite: boolean;
}

export default function NotesApprovalsTab({
  txnId,
  canWrite,
}: NotesApprovalsTabProps) {
  const { data: notesData } = useNotes(txnId);
  const { data: approvalsData } = useApprovals(txnId);
  const { data: approvalSummary } = useApprovalSummary(txnId);
  const createNote = useCreateNote(txnId);
  const deleteNote = useDeleteNote(txnId);
  const createApproval = useCreateApproval(txnId);
  const decideApproval = useDecideApproval();
  const cancelApproval = useCancelApproval();

  const [showNoteModal, setShowNoteModal] = useState(false);
  const [showApprovalModal, setShowApprovalModal] = useState(false);
  const [noteTypeFilter, setNoteTypeFilter] = useState<string>("ALL");

  const [noteForm, setNoteForm] = useState<NoteCreate>({
    content: "",
    note_type: "COMMENT",
  });
  const [approvalForm, setApprovalForm] = useState<ApprovalCreate>({
    approval_type: "PHASE_ADVANCE",
    title: "",
    approvers: [{ email: "", role: "승인자" }],
  });

  const filteredNotes =
    noteTypeFilter === "ALL"
      ? notesData?.items
      : notesData?.items.filter((n) => n.note_type === noteTypeFilter);

  return (
    <div className="space-y-6">
      {/* 승인 요약 KPI */}
      {approvalSummary && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <KpiCard label="전체 승인" value={String(approvalSummary.total)} />
          <KpiCard
            label="대기 중"
            value={String(approvalSummary.pending)}
            variant={approvalSummary.pending > 0 ? "warning" : undefined}
          />
          <KpiCard
            label="승인됨"
            value={String(approvalSummary.approved)}
            variant="good"
          />
          <KpiCard
            label="거절됨"
            value={String(approvalSummary.rejected)}
            variant={approvalSummary.rejected > 0 ? "bad" : undefined}
          />
        </div>
      )}

      {/* 승인 요청 목록 */}
      <Card
        title="승인 요청"
        headerBar
        actions={
          canWrite ? (
            <Button
              size="sm"
              icon={Plus}
              onClick={() => setShowApprovalModal(true)}
            >
              승인 요청
            </Button>
          ) : undefined
        }
      >
        {!approvalsData?.items.length ? (
          <EmptyState
            icon={Shield}
            title="승인 요청 없음"
            description="단계 전환이나 계약 체결 시 승인 요청을 생성하세요."
          />
        ) : (
          <div className="space-y-3 p-1">
            {approvalsData.items.map((approval) => (
              <div
                key={approval.id}
                className="border rounded-lg p-4 space-y-2 hover:border-accent/30 transition-colors"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="font-medium text-sm">
                      {approval.title}
                    </span>
                    <Badge
                      variant={
                        approval.status === "APPROVED"
                          ? "success"
                          : approval.status === "REJECTED"
                            ? "error"
                            : approval.status === "CANCELLED"
                              ? "neutral"
                              : "warning"
                      }
                      pill
                    >
                      {APPROVAL_STATUS_OPTIONS.find(
                        (o) => o.value === approval.status,
                      )?.label ?? approval.status}
                    </Badge>
                    <Badge variant="info" pill>
                      {APPROVAL_TYPE_OPTIONS.find(
                        (o) => o.value === approval.approval_type,
                      )?.label ?? approval.approval_type}
                    </Badge>
                  </div>
                  <div className="flex items-center gap-1">
                    {canWrite && approval.status === "PENDING" && (
                      <>
                        <Button
                          size="sm"
                          variant="ghost"
                          icon={Check}
                          onClick={() =>
                            decideApproval.mutate({
                              approvalId: approval.id,
                              body: {
                                email: approval.approvers[0]?.email ?? "",
                                decision: "APPROVED",
                              },
                            })
                          }
                        >
                          승인
                        </Button>
                        <Button
                          size="sm"
                          variant="ghost"
                          icon={X}
                          onClick={() =>
                            decideApproval.mutate({
                              approvalId: approval.id,
                              body: {
                                email: approval.approvers[0]?.email ?? "",
                                decision: "REJECTED",
                              },
                            })
                          }
                        >
                          거절
                        </Button>
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={() => cancelApproval.mutate(approval.id)}
                        >
                          취소
                        </Button>
                      </>
                    )}
                  </div>
                </div>
                {approval.description && (
                  <p className="text-xs text-text-muted">
                    {approval.description}
                  </p>
                )}
                <div className="flex items-center gap-4 text-xs text-text-muted">
                  <span>요청자: {approval.requester_email}</span>
                  {approval.deadline && <span>기한: {approval.deadline}</span>}
                  <span>{formatDate(approval.created_at)}</span>
                </div>
                {approval.approvers.length > 0 && (
                  <div className="flex flex-wrap gap-2 pt-1">
                    {approval.approvers.map((a) => (
                      <Badge
                        key={a.email}
                        variant={
                          a.status === "APPROVED"
                            ? "success"
                            : a.status === "REJECTED"
                              ? "error"
                              : "neutral"
                        }
                        pill
                      >
                        {a.email} ({a.role})
                      </Badge>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </Card>

      {/* 노트 타입 필터 */}
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-xs font-medium text-text-muted">타입:</span>
        {[{ value: "ALL", label: "전체" }, ...NOTE_TYPE_OPTIONS].map((opt) => (
          <button
            key={opt.value}
            type="button"
            className={`px-3 py-1 text-xs font-medium rounded-dr-sm transition-colors ${
              noteTypeFilter === opt.value
                ? "bg-accent text-white"
                : "bg-bg-cool text-text-muted hover:bg-gray-border"
            }`}
            onClick={() => setNoteTypeFilter(opt.value)}
          >
            {opt.label}
          </button>
        ))}
      </div>

      {/* 노트/코멘트 */}
      <Card
        title="내부 노트"
        headerBar
        actions={
          canWrite ? (
            <Button
              size="sm"
              icon={Plus}
              onClick={() => setShowNoteModal(true)}
            >
              노트 추가
            </Button>
          ) : undefined
        }
      >
        {!filteredNotes?.length ? (
          <EmptyState
            icon={MessageSquare}
            title="노트 없음"
            description={
              canWrite
                ? "내부 의사결정, 질문, 메모를 기록하세요."
                : "등록된 노트가 없습니다."
            }
          />
        ) : (
          <div className="space-y-3 p-1">
            {filteredNotes.map((note) => (
              <div
                key={note.id}
                className={`border rounded-lg p-4 space-y-2 ${note.is_pinned ? "border-accent/40 bg-accent/5" : ""}`}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    {note.is_pinned && (
                      <Pin size={14} className="text-accent" />
                    )}
                    <Badge variant="info" pill>
                      {NOTE_TYPE_OPTIONS.find((o) => o.value === note.note_type)
                        ?.label ?? note.note_type}
                    </Badge>
                    <span className="text-xs text-text-muted">
                      {note.author_email}
                    </span>
                  </div>
                  <div className="flex items-center gap-1">
                    <span className="text-xs text-text-muted">
                      {formatDate(note.created_at)}
                    </span>
                    {canWrite && (
                      <Button
                        size="sm"
                        variant="ghost"
                        icon={Trash2}
                        onClick={() => {
                          if (confirm("이 노트를 삭제하시겠습니까?"))
                            deleteNote.mutate(note.id);
                        }}
                      />
                    )}
                  </div>
                </div>
                <p className="text-sm whitespace-pre-wrap">{note.content}</p>
                {note.mentions && note.mentions.length > 0 && (
                  <div className="flex flex-wrap gap-1">
                    {note.mentions.map((m) => (
                      <Badge key={m} variant="neutral" pill>
                        @{m}
                      </Badge>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </Card>

      {/* 노트 추가 모달 */}
      <Modal
        open={showNoteModal}
        onClose={() => setShowNoteModal(false)}
        title="노트 추가"
      >
        <form
          onSubmit={(e) => {
            e.preventDefault();
            createNote.mutate(noteForm, {
              onSuccess: () => {
                setShowNoteModal(false);
                setNoteForm({ content: "", note_type: "COMMENT" });
              },
            });
          }}
          className="space-y-4"
        >
          <Select
            label="유형"
            options={NOTE_TYPE_OPTIONS}
            value={noteForm.note_type ?? "COMMENT"}
            onChange={(e) =>
              setNoteForm({
                ...noteForm,
                note_type: e.target.value as NoteType,
              })
            }
          />
          <div>
            <label className="block text-sm font-medium text-text-body mb-1.5">
              내용
            </label>
            <textarea
              required
              rows={4}
              className="w-full px-3 py-2 text-sm rounded-dr-sm border border-gray-border shadow-sm bg-white text-text-body placeholder:text-text-secondary focus:outline-none focus:ring-2 focus:ring-accent/30 focus:border-amic hover:border-amic-400 transition-colors"
              value={noteForm.content}
              onChange={(e) =>
                setNoteForm({ ...noteForm, content: e.target.value })
              }
              placeholder="의사결정, 질문, 메모 등을 기록하세요..."
            />
          </div>
          <Input
            label="멘션 (이메일, 쉼표 구분)"
            value={noteForm.mentions?.join(", ") ?? ""}
            onChange={(e) =>
              setNoteForm({
                ...noteForm,
                mentions: e.target.value
                  ? e.target.value.split(",").map((s) => s.trim())
                  : undefined,
              })
            }
            placeholder="user@example.com, user2@example.com"
          />
          <div className="flex justify-end gap-2 pt-2">
            <Button
              variant="ghost"
              type="button"
              onClick={() => setShowNoteModal(false)}
            >
              취소
            </Button>
            <Button type="submit" loading={createNote.isPending} icon={Send}>
              작성
            </Button>
          </div>
        </form>
      </Modal>

      {/* 승인 요청 모달 */}
      <Modal
        open={showApprovalModal}
        onClose={() => setShowApprovalModal(false)}
        title="승인 요청 생성"
      >
        <form
          onSubmit={(e) => {
            e.preventDefault();
            createApproval.mutate(approvalForm, {
              onSuccess: () => {
                setShowApprovalModal(false);
                setApprovalForm({
                  approval_type: "PHASE_ADVANCE",
                  title: "",
                  approvers: [{ email: "", role: "승인자" }],
                });
              },
            });
          }}
          className="space-y-4"
        >
          <Select
            label="승인 유형"
            options={APPROVAL_TYPE_OPTIONS}
            value={approvalForm.approval_type}
            onChange={(e) =>
              setApprovalForm({
                ...approvalForm,
                approval_type: e.target.value as AppType,
              })
            }
          />
          <Input
            label="제목"
            required
            value={approvalForm.title}
            onChange={(e) =>
              setApprovalForm({ ...approvalForm, title: e.target.value })
            }
            placeholder="예: 마케팅 단계 전환 승인 요청"
          />
          <Input
            label="설명"
            value={approvalForm.description ?? ""}
            onChange={(e) =>
              setApprovalForm({
                ...approvalForm,
                description: e.target.value || undefined,
              })
            }
          />
          <Input
            label="승인자 이메일"
            required
            type="email"
            value={approvalForm.approvers[0]?.email ?? ""}
            onChange={(e) =>
              setApprovalForm({
                ...approvalForm,
                approvers: [{ email: e.target.value, role: "승인자" }],
              })
            }
            placeholder="approver@example.com"
          />
          <Input
            label="기한"
            type="date"
            value={approvalForm.deadline ?? ""}
            onChange={(e) =>
              setApprovalForm({
                ...approvalForm,
                deadline: e.target.value || undefined,
              })
            }
          />
          <div className="flex justify-end gap-2 pt-2">
            <Button
              variant="ghost"
              type="button"
              onClick={() => setShowApprovalModal(false)}
            >
              취소
            </Button>
            <Button type="submit" loading={createApproval.isPending}>
              요청
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
