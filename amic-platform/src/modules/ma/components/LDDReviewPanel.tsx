/**
 * LDD 체크리스트 리뷰 패널 — 52개 항목 승인/반려 + 진행률 표시.
 */
import { useState, useCallback } from "react";
import { Button, Card } from "@/components/ui";
import {
  useLDDReport,
  useReviewProgress,
  useReviewLDDItem,
  useBulkReviewLDD,
  useFinalizeLDD,
  type LDDItem,
  type LDDSection,
} from "@/modules/ma/hooks/useLDDReports";

interface LDDReviewPanelProps {
  txnId: string;
  reportId: string;
}

const STATUS_BADGE: Record<string, { label: string; className: string }> = {
  OK: { label: "적정", className: "bg-green-100 text-green-800" },
  ISSUE: { label: "이슈", className: "bg-red-100 text-red-800" },
  NA: { label: "해당없음", className: "bg-neutral-100 text-neutral-600" },
  PENDING: { label: "검토 대기", className: "bg-yellow-100 text-yellow-800" },
};

const LEVEL_COLOR: Record<string, string> = {
  CRITICAL: "text-red-600 font-bold",
  HIGH: "text-amber-600 font-semibold",
  MEDIUM: "text-amber-500",
  LOW: "text-green-600",
};

export default function LDDReviewPanel({ txnId, reportId }: LDDReviewPanelProps) {
  const { data: report, isLoading } = useLDDReport(txnId, reportId);
  const { data: progress } = useReviewProgress(txnId, reportId);
  const reviewItem = useReviewLDDItem(txnId, reportId);
  const bulkReview = useBulkReviewLDD(txnId, reportId);
  const finalize = useFinalizeLDD(txnId, reportId);

  const [expandedSection, setExpandedSection] = useState<string | null>(null);
  const [commentInputs, setCommentInputs] = useState<Record<string, string>>({});

  const handleApprove = useCallback(
    (item: LDDItem) => {
      reviewItem.mutate({
        item_id: item.item_id,
        user_approved: true,
        user_comment: commentInputs[item.item_id] || "",
      });
    },
    [reviewItem, commentInputs]
  );

  const handleReject = useCallback(
    (item: LDDItem) => {
      reviewItem.mutate({
        item_id: item.item_id,
        user_approved: false,
        user_comment: commentInputs[item.item_id] || "",
      });
    },
    [reviewItem, commentInputs]
  );

  const handleApproveAll = useCallback(() => {
    if (!report?.sections) return;
    const items = report.sections.flatMap((s: LDDSection) =>
      s.items
        .filter((i: LDDItem) => i.user_approved === null)
        .map((i: LDDItem) => ({
          item_id: i.item_id,
          user_approved: true,
          user_comment: "",
        }))
    );
    if (items.length > 0) {
      bulkReview.mutate(items);
    }
  }, [report, bulkReview]);

  const handleFinalize = useCallback(() => {
    finalize.mutate({});
  }, [finalize]);

  if (isLoading || !report) {
    return <div className="p-6 text-neutral-500">보고서를 불러오는 중...</div>;
  }

  const isReviewState = report.status === "REVIEW";
  const sections = report.sections || [];

  return (
    <div className="space-y-6">
      {/* 진행률 바 */}
      {progress && (
        <Card className="p-4">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium text-neutral-700">리뷰 진행률</span>
            <span className="text-sm text-neutral-500">
              {progress.approved + progress.rejected} / {progress.total} ({progress.progress_pct}%)
            </span>
          </div>
          <div className="w-full bg-neutral-200 rounded-full h-2">
            <div
              className="bg-blue-600 h-2 rounded-full transition-all"
              style={{ width: `${progress.progress_pct}%` }}
            />
          </div>
          <div className="flex gap-4 mt-2 text-xs text-neutral-500">
            <span className="text-green-600">승인: {progress.approved}</span>
            <span className="text-red-600">반려: {progress.rejected}</span>
            <span>미검토: {progress.pending}</span>
          </div>
        </Card>
      )}

      {/* 액션 버튼 */}
      {isReviewState && (
        <div className="flex gap-3">
          <Button variant="outline" size="sm" onClick={handleApproveAll}>
            미검토 항목 전체 승인
          </Button>
          <Button
            size="sm"
            onClick={handleFinalize}
            disabled={finalize.isPending}
          >
            {finalize.isPending ? "최종 보고서 생성 중..." : "최종 보고서 생성 (Finalize)"}
          </Button>
        </div>
      )}

      {/* 상태 표시 */}
      {(report.status === "ANALYZING" || report.status === "FINALIZING") && (
        <Card className="p-4 bg-blue-50 border-blue-200">
          <div className="flex items-center gap-2">
            <div className="w-4 h-4 border-2 border-blue-600 border-t-transparent rounded-full animate-spin" />
            <span className="text-sm font-medium text-blue-700">
              {report.status === "ANALYZING"
                ? "AI 분석 진행 중 (Ralph Loop #1)..."
                : "최종 보고서 생성 중 (Ralph Loop #2)..."}
            </span>
          </div>
          {report.draft_score != null && (
            <span className="text-xs text-blue-500 mt-1 block">
              초안 품질 점수: {report.draft_score.toFixed(2)}
            </span>
          )}
        </Card>
      )}

      {/* 섹션별 체크리스트 */}
      {sections.map((section: LDDSection) => {
        const isExpanded = expandedSection === section.section_type;
        const sectionIssues = section.items.filter((i) => i.status === "ISSUE").length;
        const sectionReviewed = section.items.filter((i) => i.user_approved !== null).length;

        return (
          <Card key={section.section_type} className="overflow-hidden">
            <button
              className="w-full flex items-center justify-between p-4 hover:bg-neutral-50 transition"
              onClick={() =>
                setExpandedSection(isExpanded ? null : section.section_type)
              }
            >
              <div className="flex items-center gap-3">
                <span className="text-sm font-semibold">{section.title}</span>
                {sectionIssues > 0 && (
                  <span className="text-xs bg-red-100 text-red-700 px-2 py-0.5 rounded-full">
                    이슈 {sectionIssues}건
                  </span>
                )}
              </div>
              <div className="flex items-center gap-2 text-xs text-neutral-500">
                <span>
                  {sectionReviewed}/{section.items.length} 검토
                </span>
                <span>{isExpanded ? "▲" : "▼"}</span>
              </div>
            </button>

            {isExpanded && (
              <div className="border-t divide-y">
                {section.items.map((item: LDDItem) => {
                  const badge = STATUS_BADGE[item.status] || STATUS_BADGE.PENDING;

                  return (
                    <div key={item.item_id} className="p-4 space-y-2">
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          <div className="flex items-center gap-2">
                            <code className="text-xs text-neutral-400">
                              {item.item_id}
                            </code>
                            <span className="text-sm font-medium">{item.name}</span>
                            <span
                              className={`text-xs px-2 py-0.5 rounded ${badge.className}`}
                            >
                              {badge.label}
                            </span>
                            {item.issue_level && (
                              <span
                                className={`text-xs ${LEVEL_COLOR[item.issue_level] || ""}`}
                              >
                                {item.issue_level}
                              </span>
                            )}
                            {item.confidence > 0 && (
                              <span className="text-xs text-neutral-400">
                                신뢰도: {(item.confidence * 100).toFixed(0)}%
                              </span>
                            )}
                          </div>
                          {item.description && (
                            <p className="text-sm text-neutral-600 mt-1">
                              {item.description}
                            </p>
                          )}
                          {item.deal_impact && (
                            <p className="text-xs text-neutral-500 mt-1">
                              <strong>거래 영향:</strong> {item.deal_impact}
                            </p>
                          )}
                          {item.recommendation && (
                            <p className="text-xs text-neutral-500">
                              <strong>권고:</strong> {item.recommendation}
                            </p>
                          )}
                          {item.evidence_refs.length > 0 && (
                            <div className="text-xs text-blue-500 mt-1">
                              근거 문서: {item.evidence_refs.join(", ")}
                            </div>
                          )}
                        </div>

                        {/* 리뷰 상태 */}
                        <div className="flex items-center gap-1 ml-4 shrink-0">
                          {item.user_approved === true && (
                            <span className="text-xs bg-green-100 text-green-700 px-2 py-1 rounded">
                              승인됨
                            </span>
                          )}
                          {item.user_approved === false && (
                            <span className="text-xs bg-red-100 text-red-700 px-2 py-1 rounded">
                              반려됨
                            </span>
                          )}
                        </div>
                      </div>

                      {/* 리뷰 액션 */}
                      {isReviewState && (
                        <div className="flex items-center gap-2 mt-2">
                          <input
                            className="flex-1 text-sm border rounded px-2 py-1"
                            placeholder="코멘트 (선택)"
                            value={commentInputs[item.item_id] || ""}
                            onChange={(e) =>
                              setCommentInputs((prev) => ({
                                ...prev,
                                [item.item_id]: e.target.value,
                              }))
                            }
                          />
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => handleApprove(item)}
                            disabled={reviewItem.isPending}
                          >
                            승인
                          </Button>
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => handleReject(item)}
                            disabled={reviewItem.isPending}
                            className="text-red-600 border-red-300 hover:bg-red-50"
                          >
                            반려
                          </Button>
                        </div>
                      )}

                      {item.user_comment && (
                        <p className="text-xs text-neutral-500 italic mt-1">
                          리뷰어 코멘트: {item.user_comment}
                        </p>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </Card>
        );
      })}
    </div>
  );
}
