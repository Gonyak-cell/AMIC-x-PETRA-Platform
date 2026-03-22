import { useState } from "react";
import { FileText, Send, Trash2 } from "lucide-react";

import DistributionModal from "@/modules/ma/components/DistributionModal";
import MMSourceRoutingPreviewPanel from "@/modules/ma/components/marketing/MMSourceRoutingPreviewPanel";
import {
  useCreateMarketingMaterial,
  useDeleteMarketingMaterial,
  useMarketingMaterials,
  getDownloadUrl,
} from "@/modules/ma/hooks/useMarketingMaterials";
import { useTransaction } from "@/modules/ma/hooks/useTransactions";
import type { MarketingMaterial } from "@/modules/ma/types/marketing_material";
import {
  MARKETING_STATUS_LABELS,
  QUALITY_STATUS_LABELS,
  QUALITY_STATUS_VARIANT,
} from "@/modules/ma/types/marketing_material";
import { Badge, Button, Card, DataTable, EmptyState } from "@/components/ui";

interface MarketingMaterialsTabProps {
  txnId: string;
  canWrite: boolean;
  showSourcePreview?: boolean;
  surface?: "card" | "flat";
}

export default function MarketingMaterialsTab({
  txnId,
  canWrite,
  showSourcePreview = true,
  surface = "card",
}: MarketingMaterialsTabProps) {
  const { data: txn } = useTransaction(txnId);
  const { data: marketingMaterials } = useMarketingMaterials(txnId);
  const createMarketingMaterial = useCreateMarketingMaterial(txnId);
  const deleteMarketingMaterial = useDeleteMarketingMaterial(txnId);
  const [distTarget, setDistTarget] = useState<MarketingMaterial | null>(null);
  const isFlatSurface = surface === "flat";

  return (
    <div className="space-y-4">
      {showSourcePreview && <MMSourceRoutingPreviewPanel txnId={txnId} />}

      <Card
        title="마케팅 자료"
        headerBar
        className={
          isFlatSurface
            ? "border-0 shadow-none rounded-none bg-transparent"
            : undefined
        }
        actions={
          canWrite ? (
            <div className="flex gap-2">
              <Button
                size="sm"
                variant="secondary"
                onClick={() =>
                  createMarketingMaterial.mutate({
                    doc_type: "TM",
                    title: `${txn?.code_name ?? "Project"} · Teaser Memo`,
                    project_code: txn?.code_name ?? undefined,
                  })
                }
              >
                + Teaser (TM)
              </Button>
              <Button
                size="sm"
                variant="secondary"
                onClick={() =>
                  createMarketingMaterial.mutate({
                    doc_type: "DM",
                    title: `${txn?.code_name ?? "Project"} · Discussion Memo`,
                    project_code: txn?.code_name ?? undefined,
                  })
                }
              >
                + Discussion (DM)
              </Button>
              <Button
                size="sm"
                onClick={() =>
                  createMarketingMaterial.mutate({
                    doc_type: "IM",
                    title: `${txn?.code_name ?? "Project"} · Information Memo`,
                    project_code: txn?.code_name ?? undefined,
                  })
                }
              >
                + Information (IM)
              </Button>
            </div>
          ) : undefined
        }
      >
        {!marketingMaterials?.length ? (
          <EmptyState
            icon={FileText}
            title="마케팅 자료 없음"
            description="TM, DM, IM 자료를 생성하고 관리하세요."
          />
        ) : (
          <DataTable<MarketingMaterial>
            columns={[
              {
                key: "doc_type",
                label: "유형",
                render: (row) => (
                  <Badge
                    variant={
                      row.doc_type === "TM"
                        ? "info"
                        : row.doc_type === "DM"
                          ? "warning"
                          : "success"
                    }
                    pill
                  >
                    {row.doc_type}
                  </Badge>
                ),
              },
              { key: "title", label: "제목" },
              {
                key: "status",
                label: "상태",
                render: (row) => (
                  <Badge
                    variant={
                      row.status === "READY"
                        ? "success"
                        : row.status === "CONDITIONAL_READY"
                          ? "warning"
                          : row.status === "GENERATING"
                            ? "warning"
                            : row.status === "FAILED"
                              ? "error"
                              : "neutral"
                    }
                    pill
                  >
                    {MARKETING_STATUS_LABELS[row.status] ?? row.status}
                  </Badge>
                ),
              },
              {
                key: "quality_status",
                label: "품질",
                render: (row) =>
                  row.quality_status ? (
                    <Badge
                      variant={
                        (QUALITY_STATUS_VARIANT[row.quality_status] ??
                          "neutral") as
                          | "success"
                          | "warning"
                          | "error"
                          | "neutral"
                      }
                      pill
                    >
                      {QUALITY_STATUS_LABELS[row.quality_status] ??
                        row.quality_status}
                    </Badge>
                  ) : (
                    <span className="text-xs text-text-secondary">--</span>
                  ),
              },
              {
                key: "slide_count",
                label: "슬라이드",
                render: (row) =>
                  row.slide_count != null ? (
                    <span className="text-xs">{row.slide_count}장</span>
                  ) : (
                    <span className="text-xs text-text-secondary">--</span>
                  ),
              },
              {
                key: "pipeline_metrics",
                label: "소요 시간",
                render: (row) => {
                  const total = row.pipeline_metrics?.total_ms;
                  if (total == null) {
                    return (
                      <span className="text-xs text-text-secondary">--</span>
                    );
                  }
                  return (
                    <span className="text-xs">
                      {total >= 1000
                        ? `${(total / 1000).toFixed(1)}s`
                        : `${total}ms`}
                    </span>
                  );
                },
              },
              {
                key: "distributed_to",
                label: "배포",
                render: (row) =>
                  row.distributed_to?.length
                    ? `${row.distributed_to.length}곳`
                    : "미배포",
              },
              {
                key: "file_size_bytes",
                label: "크기",
                render: (row) =>
                  row.file_size_bytes
                    ? `${Math.round(row.file_size_bytes / 1024)} KB`
                    : "—",
              },
              {
                key: "id",
                label: "작업",
                render: (row) => (
                  <div className="flex gap-2">
                    {(row.status === "READY" ||
                      row.status === "CONDITIONAL_READY") && (
                      <>
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={() =>
                            window.open(getDownloadUrl(txnId, row.id), "_blank")
                          }
                        >
                          다운로드
                        </Button>
                        {canWrite && (
                          <Button
                            size="sm"
                            variant="ghost"
                            onClick={() => setDistTarget(row)}
                            disabled={row.distribution_eligible !== true}
                            title={
                              row.distribution_eligible !== true
                                ? "품질 검증을 통과한 자료만 배포할 수 있습니다."
                                : undefined
                            }
                          >
                            <Send size={14} className="mr-1" />
                            배포
                          </Button>
                        )}
                      </>
                    )}
                    {canWrite && (
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => {
                          if (
                            window.confirm(
                              "마케팅 자료를 삭제하시겠습니까? 이 작업은 되돌릴 수 없습니다.",
                            )
                          ) {
                            deleteMarketingMaterial.mutate(row.id);
                          }
                        }}
                      >
                        <Trash2 size={14} />
                      </Button>
                    )}
                  </div>
                ),
              },
            ]}
            data={marketingMaterials}
            keyField="id"
          />
        )}
      </Card>

      {distTarget && (
        <DistributionModal
          open={!!distTarget}
          onClose={() => setDistTarget(null)}
          material={distTarget}
          txnId={txnId}
        />
      )}
    </div>
  );
}
