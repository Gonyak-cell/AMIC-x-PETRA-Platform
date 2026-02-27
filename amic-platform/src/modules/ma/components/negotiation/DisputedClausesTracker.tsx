import { useState } from "react";
import { Plus, Trash2, Sparkles, AlertTriangle, ChevronDown, ChevronUp, Filter } from "lucide-react";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Modal } from "@/components/ui/Modal";
import { Select } from "@/components/ui/Select";
import { Skeleton } from "@/components/ui/Skeleton";
import {
  NEGOTIATION_ISSUE_STATUS_OPTIONS,
  NEGOTIATION_ISSUE_PRIORITY_OPTIONS,
  ISSUE_DECISION_STATUS_OPTIONS,
} from "@/modules/ma/constants";
import type {
  NegotiationIssue,
  NegotiationIssueCreate,
  NegotiationIssueStatus,
  IssueDecisionStatus,
} from "@/modules/ma/types/negotiation_issue";

const STATUS_VARIANT: Record<NegotiationIssueStatus, "success" | "warning" | "neutral" | "error" | "info"> = {
  OPEN: "neutral",
  IN_PROGRESS: "warning",
  AGREED: "success",
  DEFERRED: "info",
  DEADLOCKED: "error",
};

const PRIORITY_ORDER: Record<string, number> = { CRITICAL: 0, HIGH: 1, MEDIUM: 2, LOW: 3 };

const DECISION_STYLE: Record<IssueDecisionStatus, string> = {
  PENDING: "border-gray-300 bg-gray-50 text-text-muted",
  CONSIDER_ACCEPTING: "border-amber-400 bg-amber-50 text-amber-700",
  CANNOT_ACCEPT: "border-red-400 bg-red-50 text-red-700",
};

const DECISION_ACTIVE_STYLE: Record<IssueDecisionStatus, string> = {
  PENDING: "bg-gray-200 text-gray-700 ring-1 ring-gray-400",
  CONSIDER_ACCEPTING: "bg-amber-200 text-amber-800 ring-1 ring-amber-500",
  CANNOT_ACCEPT: "bg-red-200 text-red-800 ring-1 ring-red-500",
};

interface DisputedClausesTrackerProps {
  txnId: string;
  contractId: string | null;
  issues: NegotiationIssue[];
  isLoading: boolean;
  canWrite: boolean;
  onUpdateDecision: (issueId: string, decision: IssueDecisionStatus) => void;
  onUpdate: (issueId: string, body: Partial<NegotiationIssueCreate & { status: NegotiationIssueStatus; resolution: string }>) => void;
  onCreate: (body: NegotiationIssueCreate) => void;
  onDelete: (issueId: string) => void;
  onAISuggest: (issueId: string) => void;
  isAISuggestPending?: boolean;
}

export function DisputedClausesTracker({
  txnId,
  contractId,
  issues,
  isLoading,
  canWrite,
  onUpdateDecision,
  onUpdate,
  onCreate,
  onDelete,
  onAISuggest,
  isAISuggestPending,
}: DisputedClausesTrackerProps) {
  const [priorityFilter, setPriorityFilter] = useState<string>("ALL");
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);

  // 생성 폼 상태
  const [title, setTitle] = useState("");
  const [clause, setClause] = useState("");
  const [category, setCategory] = useState("");
  const [ourPos, setOurPos] = useState("");
  const [counterPos, setCounterPos] = useState("");
  const [legalReview, setLegalReview] = useState("");
  const [priority, setPriority] = useState("HIGH");

  const resetForm = () => {
    setTitle(""); setClause(""); setCategory("");
    setOurPos(""); setCounterPos(""); setLegalReview("");
    setPriority("HIGH"); setShowForm(false);
  };

  const handleCreate = () => {
    if (!title.trim()) return;
    onCreate({
      title: title.trim(),
      clause_reference: clause.trim() || undefined,
      category: category.trim() || undefined,
      our_position: ourPos.trim() || undefined,
      counterpart_position: counterPos.trim() || undefined,
      legal_review: legalReview.trim() || undefined,
      priority: priority as NegotiationIssueCreate["priority"],
      contract_id: contractId || undefined,
    });
    resetForm();
  };

  // 필터 + 정렬
  const filtered = issues
    .filter((i) => priorityFilter === "ALL" || i.priority === priorityFilter)
    .sort((a, b) => {
      const pa = PRIORITY_ORDER[a.priority] ?? 9;
      const pb = PRIORITY_ORDER[b.priority] ?? 9;
      if (pa !== pb) return pa - pb;
      return a.status.localeCompare(b.status);
    });

  const openCount = issues.filter((i) => i.status === "OPEN" || i.status === "IN_PROGRESS").length;

  if (isLoading) {
    return (
      <div className="space-y-3 p-4">
        <Skeleton className="h-6 w-32" />
        <Skeleton className="h-24 w-full" />
        <Skeleton className="h-24 w-full" />
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col">
      {/* 헤더 */}
      <div className="flex items-center justify-between border-b border-gray-border px-4 py-2.5">
        <h3 className="text-sm font-heading font-semibold text-text-dark">
          미해결 쟁점 ({openCount})
        </h3>
        <div className="flex items-center gap-2">
          <div className="flex items-center gap-1">
            <Filter className="h-3.5 w-3.5 text-text-muted" />
            <select
              value={priorityFilter}
              onChange={(e) => setPriorityFilter(e.target.value)}
              className="rounded border border-gray-border bg-white px-1.5 py-0.5 text-xs text-text-secondary"
            >
              <option value="ALL">전체</option>
              {NEGOTIATION_ISSUE_PRIORITY_OPTIONS.map((o) => (
                <option key={o.value} value={o.value}>{o.label}</option>
              ))}
            </select>
          </div>
          {canWrite && (
            <Button size="sm" variant="secondary" onClick={() => setShowForm(true)}>
              <Plus className="mr-1 h-3.5 w-3.5" /> 추가
            </Button>
          )}
        </div>
      </div>

      {/* 이견 목록 */}
      <div className="flex-1 overflow-y-auto">
        {filtered.length === 0 ? (
          <div className="flex h-full flex-col items-center justify-center p-6 text-center">
            <p className="text-sm text-text-muted">
              {issues.length === 0 ? "등록된 쟁점이 없습니다." : "필터 조건에 맞는 쟁점이 없습니다."}
            </p>
          </div>
        ) : (
          <div className="space-y-1 p-2">
            {filtered.map((issue) => {
              const isExpanded = expandedId === issue.id;
              const hasLinked = issue.linked_issue_ids && issue.linked_issue_ids.length > 0;

              return (
                <div
                  key={issue.id}
                  className="rounded-lg border border-gray-border bg-white transition-shadow hover:shadow-sm"
                >
                  {/* 카드 헤더 */}
                  <button
                    onClick={() => setExpandedId(isExpanded ? null : issue.id)}
                    className="flex w-full items-start gap-2 px-3 py-2.5 text-left"
                  >
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-1.5">
                        <h4 className="truncate text-xs font-semibold text-text-dark">{issue.title}</h4>
                        {hasLinked && (
                          <span title="교차 계약 연동 쟁점 존재">
                            <AlertTriangle className="h-3.5 w-3.5 shrink-0 text-amber-500" />
                          </span>
                        )}
                      </div>
                      {issue.clause_reference && (
                        <span className="mt-0.5 inline-block rounded bg-gray-100 px-1.5 py-0.5 text-[10px] text-text-muted">
                          {issue.clause_reference}
                        </span>
                      )}
                    </div>
                    <div className="flex shrink-0 items-center gap-1">
                      <Badge
                        variant={
                          issue.priority === "CRITICAL" ? "error"
                            : issue.priority === "HIGH" ? "warning"
                              : "neutral"
                        }
                      >
                        {NEGOTIATION_ISSUE_PRIORITY_OPTIONS.find((o) => o.value === issue.priority)?.label}
                      </Badge>
                      <Badge variant={STATUS_VARIANT[issue.status]}>
                        {NEGOTIATION_ISSUE_STATUS_OPTIONS.find((o) => o.value === issue.status)?.label}
                      </Badge>
                      {isExpanded ? (
                        <ChevronUp className="h-3.5 w-3.5 text-text-muted" />
                      ) : (
                        <ChevronDown className="h-3.5 w-3.5 text-text-muted" />
                      )}
                    </div>
                  </button>

                  {/* 3-상태 결정 토글 */}
                  {canWrite && (
                    <div className="flex gap-1 border-t border-gray-100 px-3 py-1.5">
                      {(["PENDING", "CONSIDER_ACCEPTING", "CANNOT_ACCEPT"] as IssueDecisionStatus[]).map((ds) => {
                        const isActive = issue.decision_status === ds;
                        const label = ISSUE_DECISION_STATUS_OPTIONS.find((o) => o.value === ds)?.label ?? ds;
                        return (
                          <button
                            key={ds}
                            onClick={(e) => { e.stopPropagation(); onUpdateDecision(issue.id, ds); }}
                            className={`flex-1 rounded px-2 py-1 text-[10px] font-medium transition-colors ${
                              isActive ? DECISION_ACTIVE_STYLE[ds] : DECISION_STYLE[ds]
                            }`}
                          >
                            {label}
                          </button>
                        );
                      })}
                    </div>
                  )}

                  {/* 확장 영역 */}
                  {isExpanded && (
                    <div className="border-t border-gray-100 px-3 py-3">
                      {/* 3-컬럼: 우리측 / 상대측 / 법률검토 */}
                      <div className="space-y-2">
                        <div className="rounded bg-blue-50 p-2">
                          <p className="text-[10px] font-semibold text-blue-700">우리측 입장</p>
                          <p className="mt-0.5 text-xs text-blue-900 whitespace-pre-wrap">
                            {issue.our_position || "-"}
                          </p>
                        </div>
                        <div className="rounded bg-orange-50 p-2">
                          <p className="text-[10px] font-semibold text-orange-700">상대측 입장</p>
                          <p className="mt-0.5 text-xs text-orange-900 whitespace-pre-wrap">
                            {issue.counterpart_position || "-"}
                          </p>
                        </div>
                        <div className="rounded bg-purple-50 p-2">
                          <p className="text-[10px] font-semibold text-purple-700">법률 검토</p>
                          <p className="mt-0.5 text-xs text-purple-900 whitespace-pre-wrap">
                            {issue.legal_review || "-"}
                          </p>
                        </div>
                      </div>

                      {/* AI 제안 */}
                      {issue.ai_suggestion && (
                        <div className="mt-2 rounded bg-green-50 p-2">
                          <p className="text-[10px] font-semibold text-green-700 flex items-center gap-1">
                            <Sparkles className="h-3 w-3" /> AI 조항 수정 제안
                          </p>
                          <p className="mt-0.5 text-xs text-green-900 whitespace-pre-wrap">{issue.ai_suggestion}</p>
                          {issue.ai_suggestion_rationale && (
                            <p className="mt-1 text-[10px] text-green-700 italic">{issue.ai_suggestion_rationale}</p>
                          )}
                        </div>
                      )}

                      {/* 해결 */}
                      {issue.resolution && (
                        <div className="mt-2 rounded bg-gray-50 p-2">
                          <p className="text-[10px] font-semibold text-text-muted">해결</p>
                          <p className="text-xs text-text-secondary">{issue.resolution}</p>
                        </div>
                      )}

                      {/* 교차 계약 연동 */}
                      {hasLinked && (
                        <div className="mt-2 flex items-center gap-1 text-[10px] text-amber-600">
                          <AlertTriangle className="h-3 w-3" />
                          {issue.linked_issue_ids!.length}개 교차 계약 쟁점 연동
                        </div>
                      )}

                      {/* 마크업 버전 */}
                      {issue.markup_version_number && (
                        <p className="mt-1 text-[10px] text-text-muted">
                          최초 제기: v{issue.markup_version_number}
                        </p>
                      )}

                      {/* 액션 버튼 */}
                      {canWrite && (
                        <div className="mt-2 flex items-center gap-1 border-t border-gray-100 pt-2">
                          <Button
                            size="sm"
                            variant="ghost"
                            onClick={() => onAISuggest(issue.id)}
                            disabled={isAISuggestPending}
                          >
                            <Sparkles className="mr-1 h-3 w-3" /> AI 제안
                          </Button>
                          {issue.status === "OPEN" && (
                            <Button
                              size="sm"
                              variant="ghost"
                              onClick={() => onUpdate(issue.id, { status: "IN_PROGRESS" })}
                            >
                              논의 시작
                            </Button>
                          )}
                          {issue.status === "IN_PROGRESS" && (
                            <Button
                              size="sm"
                              variant="ghost"
                              onClick={() => onUpdate(issue.id, { status: "AGREED", resolution: "합의 완료" })}
                            >
                              합의
                            </Button>
                          )}
                          <Button
                            size="sm"
                            variant="ghost"
                            className="ml-auto text-red-500"
                            onClick={() => onDelete(issue.id)}
                          >
                            <Trash2 className="h-3 w-3" />
                          </Button>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* 생성 모달 */}
      <Modal open={showForm} onClose={resetForm} title="쟁점 등록" size="lg">
        <div className="space-y-4">
          <Input label="제목" value={title} onChange={(e) => setTitle(e.target.value)} placeholder="쟁점 제목" required />
          <div className="grid grid-cols-2 gap-4">
            <Input label="조항 참조" value={clause} onChange={(e) => setClause(e.target.value)} placeholder="예: SPA 제4.2조" />
            <Input label="카테고리" value={category} onChange={(e) => setCategory(e.target.value)} placeholder="예: 가격, 진술보장" />
          </div>
          <div>
            <label className="block text-sm font-medium text-text-dark mb-1">우리측 입장</label>
            <textarea className="w-full rounded-lg border border-gray-border bg-white px-3 py-2 text-sm" rows={3} value={ourPos} onChange={(e) => setOurPos(e.target.value)} />
          </div>
          <div>
            <label className="block text-sm font-medium text-text-dark mb-1">상대측 입장</label>
            <textarea className="w-full rounded-lg border border-gray-border bg-white px-3 py-2 text-sm" rows={3} value={counterPos} onChange={(e) => setCounterPos(e.target.value)} />
          </div>
          <div>
            <label className="block text-sm font-medium text-text-dark mb-1">법률 검토</label>
            <textarea className="w-full rounded-lg border border-gray-border bg-white px-3 py-2 text-sm" rows={3} value={legalReview} onChange={(e) => setLegalReview(e.target.value)} />
          </div>
          <Select label="우선순위" value={priority} onChange={(e) => setPriority(e.target.value)} options={NEGOTIATION_ISSUE_PRIORITY_OPTIONS} />
          <div className="flex justify-end gap-2 pt-2">
            <Button variant="ghost" onClick={resetForm}>취소</Button>
            <Button onClick={handleCreate} disabled={!title.trim()}>등록</Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
