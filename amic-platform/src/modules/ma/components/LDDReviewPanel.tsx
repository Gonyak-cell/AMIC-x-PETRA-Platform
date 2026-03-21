/**
 * LDD review panel with item approvals plus source-control visibility.
 */
import { useCallback, useState } from "react";
import { Button, Card } from "@/components/ui";
import {
  useBulkReviewLDD,
  useFinalizeLDD,
  useLDDReport,
  useReviewLDDItem,
  useReviewProgress,
  type LDDEvidenceLedgerItem,
  type LDDItem,
  type LDDSection,
} from "@/modules/ma/hooks/useLDDReports";

interface LDDReviewPanelProps {
  txnId: string;
  reportId: string;
  onFinalized?: () => void;
}

const STATUS_BADGE: Record<string, { label: string; className: string }> = {
  OK: { label: "확정", className: "bg-green-100 text-green-800" },
  ISSUE: { label: "이슈", className: "bg-red-100 text-red-800" },
  NA: { label: "해당없음", className: "bg-neutral-100 text-neutral-600" },
  PENDING: { label: "검토대기", className: "bg-yellow-100 text-yellow-800" },
};

const LEVEL_COLOR: Record<string, string> = {
  CRITICAL: "text-red-600 font-bold",
  HIGH: "text-amber-600 font-semibold",
  MEDIUM: "text-amber-500",
  LOW: "text-green-600",
};

function EvidenceMeta({ meta }: { meta: LDDEvidenceLedgerItem | undefined }) {
  const primaryEvidence = meta?.documents?.[0];
  if (!meta) return null;

  return (
    <div className="mt-2 space-y-1">
      <div className="flex flex-wrap gap-2 text-xs">
        <span className="rounded bg-slate-100 px-2 py-0.5 text-slate-600">
          직접 {meta.direct_evidence_count}
        </span>
        <span className="rounded bg-slate-100 px-2 py-0.5 text-slate-600">
          간접 {meta.indirect_evidence_count}
        </span>
        <span className="rounded bg-blue-50 px-2 py-0.5 text-blue-700">
          문체 권장: {meta.recommended_modality}
        </span>
        {meta.requires_manual_review && (
          <span className="rounded bg-amber-50 px-2 py-0.5 text-amber-700">
            수동 검토 필요
          </span>
        )}
        {meta.missing_required_evidence && (
          <span className="rounded bg-red-50 px-2 py-0.5 text-red-700">
            필수 근거 부족
          </span>
        )}
        {meta.missing_direct_evidence_for_material_issue && (
          <span className="rounded bg-red-50 px-2 py-0.5 text-red-700">
            직접 근거 부족
          </span>
        )}
        {meta.foreign_workstream_refs.length > 0 && (
          <span className="rounded bg-red-50 px-2 py-0.5 text-red-700">
            타 workstream 오염 {meta.foreign_workstream_refs.length}
          </span>
        )}
        {meta.unresolved_refs.length > 0 && (
          <span className="rounded bg-red-50 px-2 py-0.5 text-red-700">
            미해결 ref {meta.unresolved_refs.length}
          </span>
        )}
      </div>
      {primaryEvidence?.snippet && (
        <p className="text-xs text-neutral-500">
          <strong>근거 추적:</strong>{" "}
          {primaryEvidence.page_reference ? `${primaryEvidence.page_reference} - ` : ""}
          {primaryEvidence.snippet}
        </p>
      )}
    </div>
  );
}

export default function LDDReviewPanel({
  txnId,
  reportId,
  onFinalized,
}: LDDReviewPanelProps) {
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
    [reviewItem, commentInputs],
  );

  const handleReject = useCallback(
    (item: LDDItem) => {
      reviewItem.mutate({
        item_id: item.item_id,
        user_approved: false,
        user_comment: commentInputs[item.item_id] || "",
      });
    },
    [reviewItem, commentInputs],
  );

  const handleApproveAll = useCallback(() => {
    if (!report?.sections) return;
    const items = report.sections.flatMap((section: LDDSection) =>
      section.items
        .filter((item: LDDItem) => item.user_approved === null)
        .map((item: LDDItem) => ({
          item_id: item.item_id,
          user_approved: true,
          user_comment: "",
        })),
    );
    if (items.length > 0) {
      bulkReview.mutate(items);
    }
  }, [bulkReview, report]);

  const handleFinalize = useCallback(() => {
    finalize.mutate(
      {},
      {
        onSuccess: (nextReport) => {
          if (nextReport.status === "READY") {
            onFinalized?.();
          }
        },
      },
    );
  }, [finalize, onFinalized]);

  if (isLoading || !report) {
    return <div className="p-6 text-neutral-500">보고서를 불러오는 중입니다.</div>;
  }

  const isReviewState = report.status === "REVIEW";
  const sections = report.sections || [];
  const routingSummary = report.source_routing?.summary;
  const ledgerSummary = report.evidence_ledger?.summary;

  return (
    <div className="space-y-6">
      {isReviewState && report.error_message && (
        <div className="rounded-lg border border-amber-200 bg-amber-50 p-3">
          <p className="text-sm text-amber-700">{report.error_message}</p>
        </div>
      )}

      {progress && (
        <Card className="p-4">
          <div className="mb-2 flex items-center justify-between">
            <span className="text-sm font-medium text-neutral-700">리뷰 진행률</span>
            <span className="text-sm text-neutral-500">
              {progress.approved + progress.rejected} / {progress.total} ({progress.progress_pct}%)
            </span>
          </div>
          <div className="h-2 w-full rounded-full bg-neutral-200">
            <div
              className="h-2 rounded-full bg-blue-600 transition-all"
              style={{ width: `${progress.progress_pct}%` }}
            />
          </div>
          <div className="mt-2 flex gap-4 text-xs text-neutral-500">
            <span className="text-green-600">확인: {progress.approved}</span>
            <span className="text-red-600">반려: {progress.rejected}</span>
            <span>미검토: {progress.pending}</span>
          </div>
        </Card>
      )}

      {(routingSummary || ledgerSummary) && (
        <Card className="p-4">
          <div className="flex flex-wrap gap-3 text-xs text-neutral-600">
            {routingSummary && (
              <>
                <span>LDD 입력 문서: {routingSummary.included_for_ldd ?? 0}</span>
                <span>제외 문서: {routingSummary.excluded_from_ldd ?? 0}</span>
                <span>수동검토 필요: {routingSummary.manual_review_documents}</span>
              </>
            )}
            {ledgerSummary && (
              <>
                <span>직접 근거: {ledgerSummary.direct_refs}</span>
                <span>간접 근거: {ledgerSummary.indirect_refs}</span>
                <span>근거 부족 item: {ledgerSummary.items_missing_evidence}</span>
                <span>미해결 ref: {ledgerSummary.unresolved_refs}</span>
              </>
            )}
          </div>
        </Card>
      )}

      {isReviewState && (
        <div className="flex gap-3">
          <Button variant="secondary" size="sm" onClick={handleApproveAll}>
            미검토 항목 전체 확인
          </Button>
          <Button size="sm" onClick={handleFinalize} disabled={finalize.isPending}>
            {finalize.isPending ? "최종 보고서 생성 중..." : "최종 보고서 생성 (Finalize)"}
          </Button>
        </div>
      )}

      {(report.status === "ANALYZING" || report.status === "FINALIZING") && (
        <Card className="border-blue-200 bg-blue-50 p-4">
          <div className="flex items-center gap-2">
            <div className="h-4 w-4 animate-spin rounded-full border-2 border-blue-600 border-t-transparent" />
            <span className="text-sm font-medium text-blue-700">
              {report.status === "ANALYZING"
                ? "AI 분석 진행 중 (Ralph Loop #1)..."
                : "최종 보고서 생성 중 (Ralph Loop #2)..."}
            </span>
          </div>
          {report.draft_score != null && (
            <span className="mt-1 block text-xs text-blue-500">
              초안 점수: {report.draft_score.toFixed(2)}
            </span>
          )}
        </Card>
      )}

      {sections.map((section: LDDSection) => {
        const isExpanded = expandedSection === section.section_type;
        const sectionIssues = section.items.filter((item) => item.status === "ISSUE").length;
        const sectionReviewed = section.items.filter((item) => item.user_approved !== null).length;

        return (
          <Card key={section.section_type} className="overflow-hidden">
            <button
              className="flex w-full items-center justify-between p-4 transition hover:bg-neutral-50"
              onClick={() => setExpandedSection(isExpanded ? null : section.section_type)}
            >
              <div className="flex items-center gap-3">
                <span className="text-sm font-semibold">{section.title}</span>
                {sectionIssues > 0 && (
                  <span className="rounded-full bg-red-100 px-2 py-0.5 text-xs text-red-700">
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
              <div className="divide-y border-t">
                {section.items.map((item: LDDItem) => {
                  const badge = STATUS_BADGE[item.status] || STATUS_BADGE.PENDING;
                  const evidenceMeta: LDDEvidenceLedgerItem | undefined =
                    report.evidence_ledger?.by_item_id?.[item.item_id];

                  return (
                    <div key={item.item_id} className="space-y-2 p-4">
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          <div className="flex items-center gap-2">
                            <code className="text-xs text-neutral-400">{item.item_id}</code>
                            <span className="text-sm font-medium">{item.name}</span>
                            <span className={`rounded px-2 py-0.5 text-xs ${badge.className}`}>
                              {badge.label}
                            </span>
                            {item.issue_level && (
                              <span className={`text-xs ${LEVEL_COLOR[item.issue_level] || ""}`}>
                                {item.issue_level}
                              </span>
                            )}
                            {item.confidence > 0 && (
                              <span className="text-xs text-neutral-400">
                                신뢰도 {(item.confidence * 100).toFixed(0)}%
                              </span>
                            )}
                          </div>
                          {item.description && <p className="mt-1 text-sm text-neutral-600">{item.description}</p>}
                          {item.deal_impact && (
                            <p className="mt-1 text-xs text-neutral-500">
                              <strong>거래 영향:</strong> {item.deal_impact}
                            </p>
                          )}
                          {item.recommendation && (
                            <p className="text-xs text-neutral-500">
                              <strong>권고:</strong> {item.recommendation}
                            </p>
                          )}
                          {item.evidence_refs.length > 0 && (
                            <div className="mt-1 text-xs text-blue-500">
                              근거 문서: {item.evidence_refs.join(", ")}
                            </div>
                          )}
                          <EvidenceMeta meta={evidenceMeta} />
                        </div>

                        <div className="ml-4 flex shrink-0 items-center gap-1">
                          {item.user_approved === true && (
                            <span className="rounded bg-green-100 px-2 py-1 text-xs text-green-700">
                              확인됨
                            </span>
                          )}
                          {item.user_approved === false && (
                            <span className="rounded bg-red-100 px-2 py-1 text-xs text-red-700">
                              반려됨
                            </span>
                          )}
                        </div>
                      </div>

                      {isReviewState && (
                        <div className="mt-2 flex items-center gap-2">
                          <input
                            className="flex-1 rounded border px-2 py-1 text-sm"
                            placeholder="코멘트 (선택)"
                            value={commentInputs[item.item_id] || ""}
                            onChange={(event) =>
                              setCommentInputs((prev) => ({
                                ...prev,
                                [item.item_id]: event.target.value,
                              }))
                            }
                          />
                          <Button
                            variant="secondary"
                            size="sm"
                            onClick={() => handleApprove(item)}
                            disabled={reviewItem.isPending}
                          >
                            확인
                          </Button>
                          <Button
                            variant="secondary"
                            size="sm"
                            onClick={() => handleReject(item)}
                            disabled={reviewItem.isPending}
                            className="border-red-300 text-red-600 hover:bg-red-50"
                          >
                            반려
                          </Button>
                        </div>
                      )}

                      {item.user_comment && (
                        <p className="mt-1 text-xs italic text-neutral-500">
                          리뷰 코멘트: {item.user_comment}
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
