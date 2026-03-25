import { useMemo, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { Download, FileText, Send } from "lucide-react";
import { toast } from "sonner";

import { extractApiError } from "@/api/errors";
import { maApi } from "@/api/maClient";
import { Badge, Button, Card, DataTable, EmptyState } from "@/components/ui";
import FileUploadZone from "@/modules/ma/components/FileUploadZone";
import { useMarketingMaterials } from "@/modules/ma/hooks/useMarketingMaterials";
import type { Attachment } from "@/modules/ma/types/attachment";
import type { BuyerCandidate } from "@/modules/ma/types/buyer";
import type { MarketingMaterial } from "@/modules/ma/types/marketing_material";
import {
  buildVersionedMarketingMaterials,
  getLatestRecipientDistribution,
  getRecipientDistributionDate,
  isDistributedToRecipient,
  type VersionedMarketingMaterial,
} from "@/modules/ma/utils/marketingMaterialRecipients";

interface BuyerTeaserSectionProps {
  txnId: string;
  buyer: BuyerCandidate;
  canWrite: boolean;
  onUploaded: (attachment: Attachment, file: File) => Promise<void> | void;
}

export default function BuyerTeaserSection({
  txnId,
  buyer,
  canWrite,
  onUploaded,
}: BuyerTeaserSectionProps) {
  const queryClient = useQueryClient();
  const { data: marketingMaterials } = useMarketingMaterials(txnId);
  const [pendingMaterialId, setPendingMaterialId] = useState<string | null>(null);

  const teaserMaterials = useMemo(
    () => buildVersionedMarketingMaterials(marketingMaterials ?? [], "TM"),
    [marketingMaterials],
  );
  const latestTeaser = useMemo(
    () => getLatestRecipientDistribution(teaserMaterials, buyer.company_name),
    [buyer.company_name, teaserMaterials],
  );

  async function updateDistribution(
    materialId: string,
    body: { distributed_to: string[]; distributed_at?: string },
  ) {
    const { data } = await maApi.put<MarketingMaterial>(
      `/transactions/${txnId}/marketing-materials/${materialId}/distribute`,
      body,
    );
    return data;
  }

  async function handleSendTeaser(target: VersionedMarketingMaterial) {
    if (!canWrite || pendingMaterialId) {
      return;
    }

    const recipient = buyer.company_name;
    const distributedAt = new Date().toISOString();
    setPendingMaterialId(target.material.id);

    try {
      for (const teaser of teaserMaterials) {
        const currentlyAssigned = isDistributedToRecipient(teaser.material, recipient);
        const shouldAssign = teaser.material.id === target.material.id;

        if (currentlyAssigned === shouldAssign) {
          continue;
        }

        const recipients = new Set(teaser.material.distributed_to ?? []);
        if (shouldAssign) {
          recipients.add(recipient);
        } else {
          recipients.delete(recipient);
        }

        await updateDistribution(teaser.material.id, {
          distributed_to: Array.from(recipients),
          distributed_at: shouldAssign
            ? distributedAt
            : teaser.material.distributed_at ?? undefined,
        });
      }

      await queryClient.invalidateQueries({
        queryKey: ["ma", "transactions", txnId, "marketing-materials"],
      });
      await queryClient.invalidateQueries({
        queryKey: ["ma", "transactions", txnId, "short-list", "overview"],
      });
      toast.success(
        `${buyer.company_name}에 ${target.versionLabel} Teaser 송부 기록을 반영했습니다.`,
      );
    } catch (error) {
      toast.error(extractApiError(error, "Teaser 송부 기록 저장에 실패했습니다."));
    } finally {
      setPendingMaterialId(null);
    }
  }

  return (
    <Card title="Teaser" headerBar padding="none">
      <div className="border-b border-gray-border px-5 py-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <p className="text-sm font-semibold text-text-dark">
              {buyer.company_name} 대상 Teaser 송부 관리
            </p>
            <p className="mt-1 text-xs text-text-secondary">
              거래에 등록된 TM 버전 중 현재 매수자에게 송부된 버전을 한 개 기준으로 관리합니다.
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <Badge variant={latestTeaser ? "info" : "neutral"}>
              {latestTeaser ? `송부됨 ${latestTeaser.versionLabel}` : "미송부"}
            </Badge>
            <Badge variant="neutral">{teaserMaterials.length} version(s)</Badge>
          </div>
        </div>
        {latestTeaser ? (
          <p className="mt-2 text-xs text-text-secondary">
            최신 송부일 {getRecipientDistributionDate(latestTeaser.material)}
          </p>
        ) : null}
      </div>

      {teaserMaterials.length > 0 ? (
        <DataTable<VersionedMarketingMaterial>
          columns={[
            {
              key: "versionLabel",
              header: "버전",
              width: "92px",
              render: (row) => <Badge variant="neutral">{row.versionLabel}</Badge>,
            },
            {
              key: "title",
              header: "Teaser",
              render: (row) => (
                <div className="min-w-0">
                  <p className="truncate text-sm font-medium text-text-dark">
                    {row.material.title}
                  </p>
                  <p className="mt-1 truncate text-xs text-text-secondary">
                    {row.material.file_name ?? row.material.project_code ?? "-"}
                  </p>
                </div>
              ),
            },
            {
              key: "sent",
              header: "송부 여부",
              render: (row) => {
                const isSent = isDistributedToRecipient(
                  row.material,
                  buyer.company_name,
                );

                return (
                  <div className="flex flex-col items-start gap-1">
                    <Badge variant={isSent ? "success" : "neutral"}>
                      {isSent ? "송부됨" : "미송부"}
                    </Badge>
                    {isSent ? (
                      <span className="text-xs text-text-secondary">
                        {getRecipientDistributionDate(row.material)}
                      </span>
                    ) : null}
                  </div>
                );
              },
            },
            {
              key: "actions",
              header: "",
              width: "200px",
              render: (row) => {
                const isSent = isDistributedToRecipient(
                  row.material,
                  buyer.company_name,
                );
                const canDistribute = row.material.distribution_eligible === true;

                return (
                  <div className="flex items-center justify-end gap-2">
                    {(row.material.status === "READY" ||
                      row.material.status === "CONDITIONAL_READY") && (
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() =>
                          window.open(
                            `/api/ma/transactions/${txnId}/marketing-materials/${row.material.id}/download`,
                            "_blank",
                          )
                        }
                      >
                        <Download className="mr-1 h-3.5 w-3.5" />
                        다운로드
                      </Button>
                    )}
                    {canWrite ? (
                      <Button
                        size="sm"
                        variant={isSent ? "secondary" : "primary"}
                        disabled={isSent || !canDistribute || pendingMaterialId !== null}
                        loading={pendingMaterialId === row.material.id}
                        title={
                          !canDistribute
                            ? "품질 검증을 통과한 Teaser만 송부할 수 있습니다."
                            : undefined
                        }
                        onClick={() => {
                          void handleSendTeaser(row);
                        }}
                      >
                        <Send className="mr-1 h-3.5 w-3.5" />
                        {isSent ? "현재 송부본" : "이 버전 송부"}
                      </Button>
                    ) : null}
                  </div>
                );
              },
            },
        ]}
          data={teaserMaterials}
          keyField="versionLabel"
        />
      ) : (
        <EmptyState
          icon={FileText}
          title="등록된 Teaser 없음"
          description="Teaser 자료를 업로드하면 매수자별 송부 버전과 송부 여부를 여기서 관리할 수 있습니다."
        />
      )}

      <FileUploadZone
        txnId={txnId}
        entityType="MARKETING_MATERIAL"
        entityId="TM"
        embedded
        embeddedLabel="Teaser 업로드"
        uploadLabel="Teaser 업로드"
        emptyDescription="Teaser PDF/PPTX 파일을 여기에 드롭하거나 업로드 버튼으로 추가하세요."
        emptyHint="PDF 업로드는 OCR 검토를 열고, 검토 확정 후 TM 자료로 연결할 수 있습니다."
        onUploaded={onUploaded}
        readOnly={!canWrite}
      />
    </Card>
  );
}
