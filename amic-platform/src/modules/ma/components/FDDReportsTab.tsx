import { useNavigate } from "react-router-dom";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import {
  Plus,
  Download,
  ExternalLink,
  RefreshCw,
  FileText,
  CheckCircle2,
} from "lucide-react";
import { useTransaction } from "@/modules/ma/hooks/useTransactions";
import {
  useReportVersions,
  useFinalizeReportVersion,
} from "@/modules/fdd/hooks/useReportVersions";
import type { ReportVersion } from "@/modules/fdd/types/report-version";
import { extractApiError } from "@/api/errors";
import { maApi } from "@/api/maClient";

interface FDDReportsTabProps {
  txnId: string;
}

const FORMAT_LABELS: Record<string, string> = {
  pptx: "PPTX",
  docx: "DOCX",
  json: "JSON",
};

const STATUS_STYLES: Record<string, string> = {
  DRAFT: "bg-caution-light text-amber-700",
  FINAL: "bg-positive-light text-positive",
};

export default function FDDReportsTab({ txnId }: FDDReportsTabProps) {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { data: txn, isLoading: txnLoading } = useTransaction(txnId);
  const fddDealId = txn?.fdd_deal_id ?? "";
  const {
    data: versions,
    isLoading: versionsLoading,
  } = useReportVersions(fddDealId);
  const finalizeMut = useFinalizeReportVersion(fddDealId);
  const linkFddMut = useMutation({
    mutationFn: async () => {
      const { data } = await maApi.post(
        `/transactions/${txnId}/integrations/fdd/link`,
        {
          target_name: txn?.target_company_name ?? txn?.name ?? "Untitled",
          industry: null,
        },
      );
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["ma", "transactions", txnId] });
      toast.success("FDD deal linked.");
    },
    onError: (err) => {
      toast.error(extractApiError(err, "Failed to link FDD deal."));
    },
  });
  const uploadFddMut = useMutation({
    mutationFn: async (file: File) => {
      const formData = new FormData();
      formData.append("file", file);
      const { data } = await maApi.post(
        `/transactions/${txnId}/integrations/fdd/uploads`,
        formData,
        { timeout: 300_000 },
      );
      const uploadId = data?.data?.id;
      if (uploadId) {
        await maApi.post(
          `/transactions/${txnId}/integrations/fdd/uploads/${uploadId}/ingest`,
          {},
          { timeout: 300_000 },
        );
      }
      return data;
    },
    onSuccess: () => {
      toast.success("FDD file uploaded.");
    },
    onError: (err) => {
      toast.error(extractApiError(err, "Failed to upload FDD file."));
    },
  });

  const isLoading = txnLoading || (!!fddDealId && versionsLoading);

  if (isLoading) {
    return (
      <div className="flex h-40 items-center justify-center">
        <RefreshCw className="h-5 w-5 animate-spin text-text-tertiary" />
      </div>
    );
  }

  // FDD 딜이 연결되지 않은 경우
  if (!fddDealId) {
    return (
      <div className="flex flex-col gap-4">
        <div>
          <h3 className="text-sm font-semibold text-text-primary">재무실사(FDD) 보고서</h3>
          <p className="text-xs text-text-secondary">
            FDD 딜을 먼저 생성하여 연결해야 합니다
          </p>
        </div>
        <div className="flex flex-col items-center justify-center gap-3 rounded-xl border border-dashed border-border py-12 text-center">
          <FileText className="h-8 w-8 text-text-tertiary" />
          <div>
            <p className="text-sm font-medium text-text-secondary">
              연결된 FDD 딜이 없습니다
            </p>
            <p className="text-xs text-text-tertiary">
              Document Studio에서 FDD 딜을 생성하면 자동으로 연결됩니다
            </p>
          </div>
          <button
            type="button"
            onClick={() => linkFddMut.mutate()}
            disabled={linkFddMut.isPending}
            className="mt-1 flex items-center gap-1.5 rounded-lg bg-accent-primary px-4 py-2 text-sm font-medium text-white hover:bg-accent-primary/90"
          >
            <Plus className="h-4 w-4" />
            FDD 딜 생성
          </button>
        </div>
      </div>
    );
  }

  // FDD 딜이 연결된 경우 — 보고서 버전 목록
  const draftCount = versions?.filter((v) => v.status === "DRAFT").length ?? 0;
  const finalCount = versions?.filter((v) => v.status === "FINAL").length ?? 0;

  return (
    <div className="flex flex-col gap-4">
      {/* 헤더 */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-sm font-semibold text-text-primary">재무실사(FDD) 보고서</h3>
          <p className="text-xs text-text-secondary">
            QoE, NWC, Net Debt 분석 기반 재무실사 보고서
          </p>
        </div>
        <div className="flex gap-2">
          <button
            type="button"
            onClick={() => navigate(`/fdd/deals/${fddDealId}`)}
            className="flex items-center gap-1.5 rounded-lg border border-border px-3 py-1.5 text-xs font-medium text-text-secondary hover:border-accent-primary hover:text-accent-primary"
          >
            <ExternalLink className="h-3.5 w-3.5" />
            FDD 워크스페이스
          </button>
          <button
            type="button"
            onClick={() => navigate(`/fdd/deals/${fddDealId}/report`)}
            className="flex items-center gap-1.5 rounded-lg bg-accent-primary px-3 py-1.5 text-xs font-medium text-white hover:bg-accent-primary/90"
          >
            <Plus className="h-3.5 w-3.5" />
            새 보고서
          </button>
        </div>
      </div>

      <div className="flex items-center justify-between rounded-lg border border-border bg-white px-4 py-3">
        <div>
          <p className="text-sm font-medium text-text-primary">Financial source upload</p>
          <p className="text-xs text-text-secondary">Upload GL, trial balance, or balance detail Excel files.</p>
        </div>
        <label className="flex cursor-pointer items-center gap-1.5 rounded-lg border border-border px-3 py-1.5 text-xs font-medium text-text-secondary hover:border-accent-primary hover:text-accent-primary">
          <Plus className="h-3.5 w-3.5" />
          {uploadFddMut.isPending ? "Uploading..." : "Upload Excel"}
          <input
            type="file"
            accept=".xlsx,.xls"
            className="hidden"
            disabled={uploadFddMut.isPending}
            onChange={(event) => {
              const file = event.currentTarget.files?.[0];
              event.currentTarget.value = "";
              if (file) {
                uploadFddMut.mutate(file);
              }
            }}
          />
        </label>
      </div>

      {/* KPI */}
      {versions && versions.length > 0 && (
        <div className="grid grid-cols-2 gap-3">
          <div className="rounded-lg border border-amber-200 bg-caution-light px-4 py-3">
            <p className="text-xs text-amber-500 font-medium">초안 (Draft)</p>
            <p className="text-2xl font-bold text-amber-700">{draftCount}</p>
          </div>
          <div className="rounded-lg border border-green-200 bg-positive-light px-4 py-3">
            <p className="text-xs text-positive font-medium">확정 (Final)</p>
            <p className="text-2xl font-bold text-positive">{finalCount}</p>
          </div>
        </div>
      )}

      {/* 버전 목록 */}
      {!versions || versions.length === 0 ? (
        <div className="flex flex-col items-center justify-center gap-3 rounded-xl border border-dashed border-border py-12 text-center">
          <FileText className="h-8 w-8 text-text-tertiary" />
          <div>
            <p className="text-sm font-medium text-text-secondary">
              생성된 FDD 보고서가 없습니다
            </p>
            <p className="text-xs text-text-tertiary">
              FDD 워크스페이스에서 분석을 완료하고 보고서를 생성하세요
            </p>
          </div>
          <button
            type="button"
            onClick={() => navigate(`/fdd/deals/${fddDealId}/report`)}
            className="mt-1 flex items-center gap-1.5 rounded-lg bg-accent-primary px-4 py-2 text-sm font-medium text-white hover:bg-accent-primary/90"
          >
            <Plus className="h-4 w-4" />
            새 보고서 생성
          </button>
        </div>
      ) : (
        <div className="overflow-hidden rounded-xl border border-border">
          <table className="w-full text-sm">
            <thead className="bg-white">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-medium text-text-tertiary">버전</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-text-tertiary">포맷</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-text-tertiary">포함 섹션</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-text-tertiary">상태</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-text-tertiary">생성일</th>
                <th className="px-4 py-3 text-right text-xs font-medium text-text-tertiary">작업</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {versions.map((ver: ReportVersion) => {
                const sections = Object.entries(ver.options)
                  .filter(([, v]) => v)
                  .map(([k]) => k.replace("include_", "").toUpperCase());

                return (
                  <tr key={ver.id} className="hover:bg-white-elevated/50">
                    <td className="px-4 py-3 text-sm font-medium text-text-primary">
                      v{ver.version}
                    </td>
                    <td className="px-4 py-3">
                      <span className="rounded-full bg-white-alt px-2 py-0.5 text-xs font-medium text-text-secondary">
                        {FORMAT_LABELS[ver.file_format] ?? ver.file_format}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex flex-wrap gap-1">
                        {sections.map((s) => (
                          <span
                            key={s}
                            className="rounded bg-white px-1.5 py-0.5 text-[10px] font-medium text-text-tertiary"
                          >
                            {s}
                          </span>
                        ))}
                        {sections.length === 0 && (
                          <span className="text-xs text-text-tertiary">전체</span>
                        )}
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <span
                        className={`rounded-full px-2 py-0.5 text-xs font-medium ${STATUS_STYLES[ver.status] ?? ""}`}
                      >
                        {ver.status === "DRAFT" ? "초안" : "확정"}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-xs text-text-tertiary">
                      {new Date(ver.created_at).toLocaleDateString("ko-KR")}
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center justify-end gap-1">
                        {ver.file_path && (
                          <a
                            href={`/api/fdd/deals/${fddDealId}/reports/versions/${ver.version}/download`}
                            download
                            className="flex items-center gap-1 rounded-md p-1.5 text-text-secondary hover:bg-white hover:text-accent-primary"
                            title="다운로드"
                          >
                            <Download className="h-4 w-4" />
                          </a>
                        )}
                        {ver.status === "DRAFT" && (
                          <button
                            type="button"
                            onClick={() =>
                              finalizeMut.mutate({ version: ver.version })
                            }
                            disabled={finalizeMut.isPending}
                            className="rounded-md p-1.5 text-text-tertiary hover:bg-white hover:text-positive disabled:opacity-40"
                            title="확정"
                          >
                            <CheckCircle2 className="h-4 w-4" />
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
