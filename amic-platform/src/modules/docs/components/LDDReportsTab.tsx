import { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import {
  Plus,
  Download,
  Trash2,
  RefreshCw,
  ClipboardList,
  AlertCircle,
  ShieldAlert,
  ClipboardCheck,
  ArrowLeft,
} from "lucide-react";
import {
  useLDDReports,
  useDeleteLDDReport,
  useRegenerateLDDReport,
  getLDDReportDownloadUrl,
  formatFileSize,
} from "@/modules/docs/hooks/useLDDReports";
import type { LDDReport } from "@/modules/docs/types/ldd_report";
import {
  LDD_STATUS_LABELS,
  LDD_STATUS_COLORS,
  LDD_REPORT_TYPE_LABELS,
} from "@/modules/docs/types/ldd_report";
import LDDReviewPanel from "@/modules/ma/components/LDDReviewPanel";

interface LDDReportsTabProps {
  txnId: string;
}

export default function LDDReportsTab({ txnId }: LDDReportsTabProps) {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const { data: reports, isLoading } = useLDDReports(txnId);
  const deleteMut = useDeleteLDDReport(txnId);
  const regenMut = useRegenerateLDDReport(txnId);
  const reviewReportId = searchParams.get("review_report_id");
  const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null);
  const [reviewTarget, setReviewTarget] = useState<string | null>(reviewReportId);

  useEffect(() => {
    if (reviewReportId) {
      setReviewTarget(reviewReportId);
    }
  }, [reviewReportId]);

  const clearReviewTarget = () => {
    setReviewTarget(null);
    if (!reviewReportId) return;
    const next = new URLSearchParams(searchParams);
    next.delete("review_report_id");
    setSearchParams(next, { replace: true });
  };

  const handleNew = () => {
    navigate(`/docs/ldd/new?txn_id=${txnId}`);
  };

  const handleDelete = async (reportId: string) => {
    if (confirmDeleteId === reportId) {
      await deleteMut.mutateAsync(reportId);
      setConfirmDeleteId(null);
    } else {
      setConfirmDeleteId(reportId);
    }
  };

  if (isLoading) {
    return (
      <div className="flex h-40 items-center justify-center">
        <RefreshCw className="h-5 w-5 animate-spin text-text-tertiary" />
      </div>
    );
  }

  // 리뷰 모드 — LDDReviewPanel 렌더링
  if (reviewTarget) {
    return (
      <div className="flex flex-col gap-4">
        <button
          type="button"
          onClick={clearReviewTarget}
          className="flex items-center gap-1.5 text-sm text-text-secondary hover:text-text-primary"
        >
          <ArrowLeft className="h-4 w-4" />
          보고서 목록
        </button>
        <LDDReviewPanel
          txnId={txnId}
          reportId={reviewTarget}
          onFinalized={clearReviewTarget}
        />
      </div>
    );
  }

  // 전체 KPI 집계
  const totalRed = reports?.reduce((s, r) => s + r.red_count, 0) ?? 0;
  const totalAmber = reports?.reduce((s, r) => s + r.amber_count, 0) ?? 0;
  const totalRFI = reports?.reduce((s, r) => s + r.rfi_count, 0) ?? 0;

  return (
    <div className="flex flex-col gap-4">
      {/* 헤더 */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-sm font-semibold text-text-primary">
            법률실사(LDD) 보고서
          </h3>
          <p className="text-xs text-text-secondary">
            DDRL 체크리스트 기반 법률실사보고서 생성
          </p>
        </div>
        <div className="flex gap-2">
          <button
            type="button"
            onClick={() => navigate(`/docs/ldd/new?txn_id=${txnId}&type=FULL`)}
            className="flex items-center gap-1.5 rounded-lg border border-border px-3 py-1.5 text-xs font-medium text-text-secondary hover:border-accent-primary hover:text-accent-primary"
          >
            <Plus className="h-3.5 w-3.5" />
            정식 LDD
          </button>
          <button
            type="button"
            onClick={() =>
              navigate(`/docs/ldd/new?txn_id=${txnId}&type=REDFLAG`)
            }
            className="flex items-center gap-1.5 rounded-lg border border-negative/30 px-3 py-1.5 text-xs font-medium text-negative hover:bg-negative-light"
          >
            <ShieldAlert className="h-3.5 w-3.5" />
            Redflag DD
          </button>
        </div>
      </div>

      {/* KPI 카드 (보고서가 있을 때만) */}
      {reports && reports.length > 0 && (
        <div className="grid grid-cols-3 gap-3">
          <div className="rounded-lg border border-negative/30 bg-negative-light px-4 py-3">
            <p className="text-xs text-negative font-medium">Critical (Red)</p>
            <p className="text-2xl font-bold text-negative">{totalRed}</p>
          </div>
          <div className="rounded-lg border border-amber-200 bg-caution-light px-4 py-3">
            <p className="text-xs text-amber-500 font-medium">
              High/Medium (Amber)
            </p>
            <p className="text-2xl font-bold text-amber-700">{totalAmber}</p>
          </div>
          <div className="rounded-lg border border-info bg-info-light px-4 py-3">
            <p className="text-xs text-blue-500 font-medium">RFI 요청</p>
            <p className="text-2xl font-bold text-info">{totalRFI}</p>
          </div>
        </div>
      )}

      {/* 보고서 목록 */}
      {!reports || reports.length === 0 ? (
        <div className="flex flex-col items-center justify-center gap-3 rounded-xl border border-dashed border-border py-12 text-center">
          <ClipboardList className="h-8 w-8 text-text-tertiary" />
          <div>
            <p className="text-sm font-medium text-text-secondary">
              생성된 LDD 보고서가 없습니다
            </p>
            <p className="text-xs text-text-tertiary">
              위 버튼으로 법률실사 보고서를 생성하세요
            </p>
          </div>
          <button
            type="button"
            onClick={handleNew}
            className="mt-1 flex items-center gap-1.5 rounded-lg bg-accent-primary px-4 py-2 text-sm font-medium text-white hover:bg-accent-primary/90"
          >
            <Plus className="h-4 w-4" />새 LDD 보고서 생성
          </button>
        </div>
      ) : (
        <div className="overflow-hidden rounded-xl border border-border">
          <table className="w-full text-sm">
            <thead className="bg-white">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-medium text-text-tertiary">
                  유형
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-text-tertiary">
                  제목
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-text-tertiary">
                  이슈 현황
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-text-tertiary">
                  상태
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-text-tertiary">
                  크기
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-text-tertiary">
                  생성일
                </th>
                <th className="px-4 py-3 text-right text-xs font-medium text-text-tertiary">
                  작업
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {reports.map((report: LDDReport) => (
                <tr key={report.id} className="hover:bg-white-elevated/50">
                  {/* 유형 */}
                  <td className="px-4 py-3">
                    <span
                      className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                        report.report_type === "REDFLAG"
                          ? "bg-negative-light text-negative"
                          : "bg-info-light text-info"
                      }`}
                    >
                      {LDD_REPORT_TYPE_LABELS[report.report_type]}
                    </span>
                  </td>

                  {/* 제목 */}
                  <td className="max-w-[180px] px-4 py-3">
                    <p className="truncate text-sm font-medium text-text-primary">
                      {report.title}
                    </p>
                    {report.target_company && (
                      <p className="text-xs text-text-tertiary truncate">
                        {report.target_company}
                      </p>
                    )}
                  </td>

                  {/* 이슈 현황 */}
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-1.5">
                      {report.red_count > 0 && (
                        <span className="text-xs px-1.5 py-0.5 rounded-full bg-negative-light text-negative font-medium">
                          R{report.red_count}
                        </span>
                      )}
                      {report.amber_count > 0 && (
                        <span className="text-xs px-1.5 py-0.5 rounded-full bg-caution-light text-amber-700 font-medium">
                          A{report.amber_count}
                        </span>
                      )}
                      {report.green_count > 0 && (
                        <span className="text-xs px-1.5 py-0.5 rounded-full bg-positive-light text-positive">
                          G{report.green_count}
                        </span>
                      )}
                      {report.issue_count === 0 && (
                        <span className="text-xs text-text-tertiary">—</span>
                      )}
                    </div>
                  </td>

                  {/* 상태 */}
                  <td className="px-4 py-3">
                    <span
                      className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                        LDD_STATUS_COLORS[report.status]
                      } ${report.status === "GENERATING" ? "animate-pulse" : ""}`}
                    >
                      {LDD_STATUS_LABELS[report.status]}
                    </span>
                    {report.status === "FAILED" && report.error_message && (
                      <div className="mt-1 flex items-center gap-1 text-xs text-negative">
                        <AlertCircle className="h-3 w-3" />
                        <span
                          className="truncate max-w-[120px]"
                          title={report.error_message}
                        >
                          오류 발생
                        </span>
                      </div>
                    )}
                    {(report.draft_score != null ||
                      report.final_score != null) && (
                      <div className="mt-1 text-xs text-text-tertiary">
                        QA: {report.final_score ?? report.draft_score}/5
                      </div>
                    )}
                  </td>

                  {/* 크기 */}
                  <td className="px-4 py-3 text-xs text-text-tertiary">
                    {formatFileSize(report.file_size_bytes)}
                  </td>

                  {/* 생성일 */}
                  <td className="px-4 py-3 text-xs text-text-tertiary">
                    {new Date(report.created_at).toLocaleDateString("ko-KR")}
                  </td>

                  {/* 작업 */}
                  <td className="px-4 py-3">
                    <div className="flex items-center justify-end gap-1">
                      {/* REVIEW 상태: 리뷰 진입 버튼 */}
                      {report.status === "REVIEW" && (
                        <button
                          type="button"
                          onClick={() => setReviewTarget(report.id)}
                          className="flex items-center gap-1 rounded-md px-2 py-1 text-xs font-medium text-amber-700 bg-amber-50 hover:bg-amber-100"
                        >
                          <ClipboardCheck className="h-3.5 w-3.5" />
                          리뷰
                        </button>
                      )}
                      {/* ANALYZING/FINALIZING: 진행 중 표시 */}
                      {(report.status === "ANALYZING" ||
                        report.status === "FINALIZING") && (
                        <span className="flex items-center gap-1 text-xs text-text-tertiary">
                          <RefreshCw className="h-3 w-3 animate-spin" />
                          분석 중
                        </span>
                      )}
                      {report.status === "READY" && (
                        <a
                          href={getLDDReportDownloadUrl(txnId, report.id)}
                          download={report.file_name ?? `LDD_${report.id}.docx`}
                          className="flex items-center gap-1 rounded-md p-1.5 text-text-secondary hover:bg-white hover:text-accent-primary"
                          title="다운로드"
                        >
                          <Download className="h-4 w-4" />
                        </a>
                      )}
                      {(report.status === "READY" ||
                        report.status === "FAILED") && (
                        <button
                          type="button"
                          onClick={() => regenMut.mutate(report.id)}
                          disabled={regenMut.isPending}
                          className="rounded-md p-1.5 text-text-tertiary hover:bg-white hover:text-accent-primary disabled:opacity-40"
                          title="재생성"
                        >
                          <RefreshCw
                            className={`h-4 w-4 ${regenMut.isPending ? "animate-spin" : ""}`}
                          />
                        </button>
                      )}
                      <button
                        type="button"
                        onClick={() => handleDelete(report.id)}
                        disabled={deleteMut.isPending}
                        className={`rounded-md p-1.5 hover:bg-white ${
                          confirmDeleteId === report.id
                            ? "text-negative"
                            : "text-text-tertiary hover:text-negative"
                        }`}
                        title={
                          confirmDeleteId === report.id
                            ? "다시 클릭하면 삭제됩니다"
                            : "삭제"
                        }
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
