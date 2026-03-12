import { useState } from "react";
import { FileText, Send, Trash2 } from "lucide-react";
import {
  useMarketingMaterials,
  useCreateMarketingMaterial,
  useDeleteMarketingMaterial,
  getDownloadUrl,
} from "@/modules/ma/hooks/useMarketingMaterials";
import type { MarketingMaterial } from "@/modules/ma/types/marketing_material";
import { MARKETING_STATUS_LABELS } from "@/modules/ma/types/marketing_material";
import { useTransaction } from "@/modules/ma/hooks/useTransactions";
import FileUploadZone from "@/modules/ma/components/FileUploadZone";
import DistributionModal from "@/modules/ma/components/DistributionModal";

import { Badge, Button, Card, DataTable, EmptyState } from "@/components/ui";

interface MarketingMaterialsTabProps {
  txnId: string;
  canWrite: boolean;
}

export default function MarketingMaterialsTab({
  txnId,
  canWrite,
}: MarketingMaterialsTabProps) {
  const { data: txn } = useTransaction(txnId);
  const { data: marketingMaterials } = useMarketingMaterials(txnId);
  const createMarketingMaterial = useCreateMarketingMaterial(txnId);
  const deleteMarketingMaterial = useDeleteMarketingMaterial(txnId);

  const [distTarget, setDistTarget] = useState<MarketingMaterial | null>(null);

  return (
    <div className="space-y-4">
      <Card
        title="마케팅 자료"
        headerBar
        actions={
          canWrite ? (
            <div className="flex gap-2">
              <Button
                size="sm"
                variant="secondary"
                onClick={() =>
                  createMarketingMaterial.mutate({
                    doc_type: "TM",
                    title: `${txn?.code_name ?? "Project"} — Teaser Memo`,
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
                    title: `${txn?.code_name ?? "Project"} — Discussion Memo`,
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
                    title: `${txn?.code_name ?? "Project"} — Information Memo`,
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
                    : "\u2014",
              },
              {
                key: "id",
                label: "작업",
                render: (row) => (
                  <div className="flex gap-2">
                    {row.status === "READY" && (
                      <>
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={() =>
                            window.open(
                              getDownloadUrl(txnId, row.id),
                              "_blank",
                            )
                          }
                        >
                          다운로드
                        </Button>
                        {canWrite && (
                          <Button
                            size="sm"
                            variant="ghost"
                            onClick={() => setDistTarget(row)}
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
        <FileUploadZone
          txnId={txnId}
          entityType="MARKETING_MATERIAL"
          embedded
        />
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
