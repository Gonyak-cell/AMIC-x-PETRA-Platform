import {
  CheckCircle,
  Clock,
  AlertTriangle,
  FileText,
  XCircle,
} from "lucide-react";
import { useMemo } from "react";

import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";
import { Spinner } from "@/components/ui/Spinner";
import { useClassificationStatus } from "@/modules/ma/hooks/useVdr";
import type { DirectUploadBatchResult } from "@/modules/ma/types/vdr";
import { VDR_CATEGORY_LABELS } from "@/modules/ma/types/vdr";

interface DirectUploadResultModalProps {
  open: boolean;
  onClose: () => void;
  txnId: string;
  result: DirectUploadBatchResult;
}

function formatScore(score: number): string {
  return `${score}점`;
}

export default function DirectUploadResultModal({
  open,
  onClose,
  txnId,
  result,
}: DirectUploadResultModalProps) {
  // 1차 심사 통과 (DIRECT) vs 2차 심사 대기 (PENDING_REVIEW)
  const directResults = useMemo(
    () => result.results.filter((r) => r.classification_status === "DIRECT"),
    [result],
  );

  const pendingResults = useMemo(
    () => result.results.filter((r) => r.classification_status !== "DIRECT"),
    [result],
  );

  // 2차 심사 대기 문서만 폴링
  const pendingDocIds = useMemo(
    () =>
      pendingResults
        .filter((r) => r.classification_status === "PENDING_REVIEW")
        .map((r) => r.document.id),
    [pendingResults],
  );

  const { data: classificationStatuses } = useClassificationStatus(
    txnId,
    pendingDocIds,
  );

  // 폴링 결과 매핑
  const statusMap = useMemo(() => {
    const map = new Map<
      string,
      { status: string; folder_name?: string; category?: string }
    >();
    if (classificationStatuses) {
      for (const item of classificationStatuses) {
        map.set(item.document_id, {
          status: item.classification_status,
          folder_name: item.routed_folder?.name,
          category: item.routed_category ?? undefined,
        });
      }
    }
    return map;
  }, [classificationStatuses]);

  return (
    <Modal
      open={open}
      onClose={onClose}
      title="빠른 업로드 결과"
      size="lg"
      footer={
        <Button variant="primary" onClick={onClose}>
          확인
        </Button>
      }
    >
      <div className="space-y-4">
        {/* 요약 */}
        <div className="flex items-center gap-2 text-sm text-slate-600">
          <CheckCircle className="h-4 w-4 text-positive" />
          <span>
            <strong>{result.total_uploaded}</strong>개 파일이 업로드되었습니다
          </span>
          {result.pending_review_count > 0 && (
            <Badge variant="info" pill>
              {result.pending_review_count}건 AI 분석 중
            </Badge>
          )}
          {result.failed_files.length > 0 && (
            <Badge variant="error" pill>
              {result.failed_files.length}건 실패
            </Badge>
          )}
        </div>

        {/* 1차 심사 통과 (즉시 분류) */}
        {directResults.length > 0 && (
          <div className="space-y-2">
            <h4 className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
              즉시 분류 완료
            </h4>
            <div className="divide-y divide-gray-100 rounded-lg border border-gray-200 bg-white">
              {directResults.map((r) => (
                <div
                  key={r.document.id}
                  className="flex items-center gap-3 px-3 py-2.5"
                >
                  <FileText className="h-4 w-4 text-slate-400 flex-shrink-0" />
                  <span className="text-sm text-slate-700 truncate flex-1">
                    {r.document.original_name}
                  </span>
                  <Badge variant="success" pill>
                    {r.routed_category
                      ? (VDR_CATEGORY_LABELS[r.routed_category] ??
                        r.routed_category)
                      : r.routed_folder.name}
                  </Badge>
                  <span className="text-xs text-slate-400 tabular-nums w-10 text-right">
                    {formatScore(r.score)}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* 2차 심사 대기 (AI 분석 중) */}
        {pendingResults.length > 0 && (
          <div className="space-y-2">
            <h4 className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
              AI 심층 분석
            </h4>
            <div className="divide-y divide-gray-100 rounded-lg border border-gray-200 bg-white">
              {pendingResults.map((r) => {
                const polled = statusMap.get(r.document.id);
                const isClassified = polled?.status === "CLASSIFIED";
                const isManualReview = polled?.status === "MANUAL_REVIEW";
                const isPending = !polled || polled.status === "PENDING_REVIEW";

                return (
                  <div
                    key={r.document.id}
                    className="flex items-center gap-3 px-3 py-2.5"
                  >
                    <FileText className="h-4 w-4 text-slate-400 flex-shrink-0" />
                    <span className="text-sm text-slate-700 truncate flex-1">
                      {r.document.original_name}
                    </span>

                    {isPending && (
                      <>
                        <Spinner size="sm" />
                        <Badge variant="info" pill>
                          분류 중...
                        </Badge>
                      </>
                    )}

                    {isClassified && polled && (
                      <Badge variant="success" pill>
                        {polled.category
                          ? (VDR_CATEGORY_LABELS[
                              polled.category as keyof typeof VDR_CATEGORY_LABELS
                            ] ?? polled.category)
                          : (polled.folder_name ?? "분류 완료")}
                      </Badge>
                    )}

                    {isManualReview && (
                      <>
                        <AlertTriangle className="h-4 w-4 text-caution flex-shrink-0" />
                        <Badge variant="warning" pill>
                          수동 확인 필요
                        </Badge>
                      </>
                    )}
                  </div>
                );
              })}
            </div>
            {pendingDocIds.length > 0 && (
              <p className="text-xs text-slate-400 flex items-center gap-1.5">
                <Clock className="h-3 w-3" />
                AI가 문서 본문을 분석하여 자동 분류합니다 (보통 1~2분 소요)
              </p>
            )}
          </div>
        )}

        {/* 업로드 실패 파일 */}
        {result.failed_files.length > 0 && (
          <div className="space-y-2">
            <h4 className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
              업로드 실패
            </h4>
            <div className="divide-y divide-gray-100 rounded-lg border border-red-200 bg-red-50">
              {result.failed_files.map((f) => (
                <div
                  key={f.filename}
                  className="flex items-center gap-3 px-3 py-2.5"
                >
                  <XCircle className="h-4 w-4 text-red-400 flex-shrink-0" />
                  <span className="text-sm text-slate-700 truncate flex-1">
                    {f.filename}
                  </span>
                  <span className="text-xs text-red-500">{f.reason}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </Modal>
  );
}
