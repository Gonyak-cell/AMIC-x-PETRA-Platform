import { useState } from "react";
import { ArrowLeft, Download, Trash2, FileSpreadsheet } from "lucide-react";
import { cn } from "@/lib/cn";
import {
  useFinancialModels,
  useCreateFinancialModel,
  useDeleteFinancialModel,
  getFMDownloadUrl,
} from "@/modules/ma/hooks/useFinancialModels";
import { useTransaction } from "@/modules/ma/hooks/useTransactions";
import type { FinancialModel } from "@/modules/ma/types/financial_model";
import {
  FM_MODEL_TYPE_LABELS,
  FM_STATUS_LABELS,
  FM_STATUS_COLORS,
  FM_QUALITY_STATUS_COLORS,
  FM_QUALITY_STATUS_LABELS,
} from "@/modules/ma/types/financial_model";
import FMChecklistReview from "@/modules/ma/components/fm/FMChecklistReview";
import FileUploadZone from "@/modules/ma/components/FileUploadZone";

import { Button, Card, DataTable, EmptyState } from "@/components/ui";

interface ModelsTabProps {
  txnId: string;
  canWrite: boolean;
}

export default function ModelsTab({ txnId, canWrite }: ModelsTabProps) {
  const { data: txn } = useTransaction(txnId);
  const { data: financialModels } = useFinancialModels(txnId);
  const createFinancialModel = useCreateFinancialModel(txnId);
  const deleteFinancialModel = useDeleteFinancialModel(txnId);
  const [selectedFMId, setSelectedFMId] = useState<string | null>(null);
  const selectedModel =
    financialModels?.find((model) => model.id === selectedFMId) ?? null;

  return (
    <div className="space-y-4">
      {selectedFMId ? (
        // 체크리스트 리뷰 뷰
        <div>
          <Button
            variant="ghost"
            size="sm"
            icon={ArrowLeft}
            onClick={() => setSelectedFMId(null)}
            className="mb-4"
          >
            모델 목록으로
          </Button>
          <FMChecklistReview
            txnId={txnId}
            fmId={selectedFMId}
            model={selectedModel}
          />
        </div>
      ) : (
        // 모델 목록 뷰
        <Card
          title="재무모델"
          headerBar
          actions={
            canWrite ? (
              <div className="flex gap-2">
                <Button
                  size="sm"
                  variant="secondary"
                  onClick={() =>
                    createFinancialModel.mutate({
                      model_type: "DCF",
                      title: `${txn?.code_name ?? "Project"} — DCF Valuation`,
                    })
                  }
                >
                  + DCF
                </Button>
                <Button
                  size="sm"
                  variant="secondary"
                  onClick={() =>
                    createFinancialModel.mutate({
                      model_type: "COMPS",
                      title: `${txn?.code_name ?? "Project"} — 비교기업 분석`,
                    })
                  }
                >
                  + COMPS
                </Button>
                <Button
                  size="sm"
                  onClick={() =>
                    createFinancialModel.mutate({
                      model_type: "FULL",
                      title: `${txn?.code_name ?? "Project"} — Full Financial Model`,
                    })
                  }
                >
                  + Full Model
                </Button>
              </div>
            ) : undefined
          }
        >
          {!financialModels?.length ? (
            <EmptyState
              icon={FileSpreadsheet}
              title="재무모델 없음"
              description="DCF, LBO, COMPS 등 재무모델을 생성하면 VDR 자료에서 가정값을 자동 추출하여 Excel을 생성합니다."
            />
          ) : (
            <DataTable<FinancialModel>
              columns={[
                {
                  key: "model_type",
                  header: "유형",
                  render: (row) => (
                    <span className="text-sm font-medium">
                      {FM_MODEL_TYPE_LABELS[row.model_type]}
                    </span>
                  ),
                },
                {
                  key: "title",
                  header: "제목",
                  render: (row) => (
                    <button
                      type="button"
                      onClick={() => {
                        if (
                          row.status === "PENDING_REVIEW" ||
                          row.status === "READY" ||
                          row.status === "FAILED"
                        ) {
                          setSelectedFMId(row.id);
                        }
                      }}
                      className="text-sm text-amic hover:underline text-left"
                    >
                      {row.title}
                    </button>
                  ),
                },
                {
                  key: "status",
                  header: "상태",
                  render: (row) => (
                    <span
                      className={cn(
                        "inline-flex px-2 py-0.5 text-xs font-semibold rounded-full",
                        FM_STATUS_COLORS[row.status],
                      )}
                    >
                      {FM_STATUS_LABELS[row.status]}
                    </span>
                  ),
                },
                {
                  key: "version",
                  header: "버전",
                  render: (row) => (
                    <span className="text-xs">v{row.version}</span>
                  ),
                },
                {
                  key: "ralph_score",
                  header: "Ralph 점수",
                  render: (row) =>
                    row.ralph_score != null ? (
                      <span className="text-xs font-medium">
                        {row.ralph_score.toFixed(1)}
                      </span>
                    ) : (
                      <span className="text-xs text-text-secondary">--</span>
                    ),
                },
                {
                  key: "quality_status",
                  header: "품질",
                  render: (row) =>
                    row.quality_status ? (
                      <span
                        className={cn(
                          "inline-flex px-2 py-0.5 text-xs font-semibold rounded-full",
                          FM_QUALITY_STATUS_COLORS[row.quality_status] ??
                            "bg-gray-100 text-gray-500",
                        )}
                      >
                        {FM_QUALITY_STATUS_LABELS[row.quality_status] ??
                          row.quality_status}
                      </span>
                    ) : (
                      <span className="text-xs text-text-secondary">--</span>
                    ),
                },
                {
                  key: "actions" as keyof FinancialModel,
                  header: "",
                  render: (row) => (
                    <div className="flex items-center gap-1">
                      {row.status === "READY" && (
                        <Button
                          variant="ghost"
                          size="sm"
                          icon={Download}
                          onClick={() =>
                            window.open(
                              getFMDownloadUrl(txnId, row.id),
                              "_blank",
                            )
                          }
                        >
                          다운로드
                        </Button>
                      )}
                      {canWrite && (
                        <Button
                          variant="ghost"
                          size="sm"
                          icon={Trash2}
                          onClick={() => deleteFinancialModel.mutate(row.id)}
                          className="text-negative hover:bg-negative/10"
                        />
                      )}
                    </div>
                  ),
                },
              ]}
              data={financialModels}
              keyField="id"
            />
          )}
          <FileUploadZone txnId={txnId} entityType="FINANCIAL_MODEL" embedded />
        </Card>
      )}
    </div>
  );
}
