import { useState } from "react";
import { Plus, Trash2, Sparkles, Scale } from "lucide-react";
import {
  Badge,
  Button,
  Card,
  EmptyState,
  Input,
  Modal,
  Select,
} from "@/components/ui";
import {
  NEGOTIATION_ISSUE_STATUS_OPTIONS,
  NEGOTIATION_ISSUE_PRIORITY_OPTIONS,
  NEGOTIATION_ISSUE_STATUS_VARIANT,
} from "@/modules/ma/constants";
import type {
  NegotiationIssue,
  NegotiationIssueCreate,
  NegotiationIssueStatus,
} from "@/modules/ma/types/negotiation_issue";

interface NegotiationIssuePanelProps {
  issues: NegotiationIssue[];
  canWrite: boolean;
  onCreate: (body: NegotiationIssueCreate) => void;
  onUpdate: (
    issueId: string,
    body: Partial<
      NegotiationIssueCreate & {
        status: NegotiationIssueStatus;
        resolution: string;
      }
    >,
  ) => void;
  onDelete: (issueId: string) => void;
  onAISuggest: (issueId: string) => void;
  isAISuggestPending?: boolean;
}

export default function NegotiationIssuePanel({
  issues,
  canWrite,
  onCreate,
  onUpdate,
  onDelete,
  onAISuggest,
  isAISuggestPending,
}: NegotiationIssuePanelProps) {
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
    setTitle("");
    setClause("");
    setCategory("");
    setOurPos("");
    setCounterPos("");
    setLegalReview("");
    setPriority("HIGH");
    setShowForm(false);
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
    });
    resetForm();
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-heading font-semibold text-text-dark flex items-center gap-2">
          <Scale className="h-4 w-4" /> 협상 이견 ({issues.length})
        </h3>
        {canWrite && (
          <Button icon={Plus} onClick={() => setShowForm(true)}>
            이견 등록
          </Button>
        )}
      </div>

      {issues.length === 0 && (
        <EmptyState
          title="등록된 협상 이견이 없습니다"
          description="이견이 발생하면 여기에서 양측 입장을 추적하세요."
        />
      )}

      {/* 이견 목록 */}
      <div className="space-y-3">
        {issues.map((issue) => (
          <Card key={issue.id} className="p-4">
            <div className="flex items-start justify-between mb-2">
              <div>
                <h4 className="text-sm font-semibold text-text-dark">
                  {issue.title}
                </h4>
                {issue.clause_reference && (
                  <span className="text-xs text-text-muted">
                    {issue.clause_reference}
                  </span>
                )}
              </div>
              <div className="flex items-center gap-2">
                <Badge variant={NEGOTIATION_ISSUE_STATUS_VARIANT[issue.status]}>
                  {
                    NEGOTIATION_ISSUE_STATUS_OPTIONS.find(
                      (o) => o.value === issue.status,
                    )?.label
                  }
                </Badge>
                <Badge
                  variant={
                    issue.priority === "CRITICAL"
                      ? "error"
                      : issue.priority === "HIGH"
                        ? "warning"
                        : "neutral"
                  }
                >
                  {
                    NEGOTIATION_ISSUE_PRIORITY_OPTIONS.find(
                      (o) => o.value === issue.priority,
                    )?.label
                  }
                </Badge>
              </div>
            </div>

            {/* 3컬럼: 우리측 / 상대측 / 법률검토 */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mt-3">
              <div className="rounded-lg bg-blue-50 border border-blue-200 p-3">
                <p className="text-xs font-semibold text-blue-700 mb-1">
                  우리측 입장
                </p>
                <p className="text-xs text-blue-900 whitespace-pre-wrap">
                  {issue.our_position || "-"}
                </p>
              </div>
              <div className="rounded-lg bg-orange-50 border border-orange-200 p-3">
                <p className="text-xs font-semibold text-orange-700 mb-1">
                  상대측 입장
                </p>
                <p className="text-xs text-orange-900 whitespace-pre-wrap">
                  {issue.counterpart_position || "-"}
                </p>
              </div>
              <div className="rounded-lg bg-purple-50 border border-purple-200 p-3">
                <p className="text-xs font-semibold text-purple-700 mb-1">
                  법률 검토
                </p>
                <p className="text-xs text-purple-900 whitespace-pre-wrap">
                  {issue.legal_review || "-"}
                </p>
              </div>
            </div>

            {/* AI 제안 */}
            {issue.ai_suggestion && (
              <div className="mt-3 rounded-lg bg-green-50 border border-green-200 p-3">
                <p className="text-xs font-semibold text-green-700 mb-1 flex items-center gap-1">
                  <Sparkles className="h-3.5 w-3.5" /> AI 조항 수정 제안
                </p>
                <p className="text-xs text-green-900 whitespace-pre-wrap">
                  {issue.ai_suggestion}
                </p>
              </div>
            )}

            {/* 합의/해결 */}
            {issue.resolution && (
              <div className="mt-2 rounded-lg bg-gray-50 border border-gray-200 p-2">
                <p className="text-xs text-text-secondary">
                  해결: {issue.resolution}
                </p>
              </div>
            )}

            {/* 액션 버튼 */}
            <div className="flex items-center gap-2 mt-3">
              {canWrite && (
                <>
                  <Button
                    size="sm"
                    variant="ghost"
                    icon={Sparkles}
                    onClick={() => onAISuggest(issue.id)}
                    disabled={isAISuggestPending}
                  >
                    AI 제안
                  </Button>
                  {issue.status === "OPEN" && (
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() =>
                        onUpdate(issue.id, { status: "IN_PROGRESS" })
                      }
                    >
                      논의 시작
                    </Button>
                  )}
                  {issue.status === "IN_PROGRESS" && (
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() =>
                        onUpdate(issue.id, {
                          status: "AGREED",
                          resolution: "합의 완료",
                        })
                      }
                    >
                      합의 완료
                    </Button>
                  )}
                  <Button
                    size="sm"
                    variant="ghost"
                    className="text-red-500"
                    icon={Trash2}
                    onClick={() => onDelete(issue.id)}
                  >
                    삭제
                  </Button>
                </>
              )}
            </div>
          </Card>
        ))}
      </div>

      {/* 생성 모달 */}
      <Modal
        open={showForm}
        onClose={resetForm}
        title="협상 이견 등록"
        size="lg"
      >
        <div className="space-y-4">
          <Input
            label="제목"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="이견 제목"
            required
          />
          <div className="grid grid-cols-2 gap-4">
            <Input
              label="조항 참조"
              value={clause}
              onChange={(e) => setClause(e.target.value)}
              placeholder="예: SPA 제4.2조"
            />
            <Input
              label="카테고리"
              value={category}
              onChange={(e) => setCategory(e.target.value)}
              placeholder="예: 가격, 진술보장"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-text-dark mb-1">
              우리측 입장
            </label>
            <textarea
              className="w-full rounded-lg border border-gray-border bg-white px-3 py-2 text-sm"
              rows={3}
              value={ourPos}
              onChange={(e) => setOurPos(e.target.value)}
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-text-dark mb-1">
              상대측 입장
            </label>
            <textarea
              className="w-full rounded-lg border border-gray-border bg-white px-3 py-2 text-sm"
              rows={3}
              value={counterPos}
              onChange={(e) => setCounterPos(e.target.value)}
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-text-dark mb-1">
              법률 검토
            </label>
            <textarea
              className="w-full rounded-lg border border-gray-border bg-white px-3 py-2 text-sm"
              rows={3}
              value={legalReview}
              onChange={(e) => setLegalReview(e.target.value)}
            />
          </div>
          <Select
            label="우선순위"
            value={priority}
            onChange={(e) => setPriority(e.target.value)}
            options={NEGOTIATION_ISSUE_PRIORITY_OPTIONS}
          />
          <div className="flex justify-end gap-2 pt-2">
            <Button variant="ghost" onClick={resetForm}>
              취소
            </Button>
            <Button onClick={handleCreate} disabled={!title.trim()}>
              등록
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
