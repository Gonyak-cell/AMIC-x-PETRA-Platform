import { useMemo, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { Download, Send } from "lucide-react";
import { toast } from "sonner";

import { extractApiError } from "@/api/errors";
import { maApi } from "@/api/maClient";
import { Badge, Button, Card, DataTable } from "@/components/ui";
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
  const hasTeasers = teaserMaterials.length > 0;

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
        `${buyer.company_name}\uc5d0 ${target.versionLabel} Teaser \uc1a1\ubd80 \uae30\ub85d\uc774 \ubc18\uc601\ub418\uc5c8\uc2b5\ub2c8\ub2e4.`,
      );
    } catch (error) {
      toast.error(
        extractApiError(
          error,
          "Teaser \uc1a1\ubd80 \uae30\ub85d \uc800\uc7a5\uc5d0 \uc2e4\ud328\ud588\uc2b5\ub2c8\ub2e4.",
        ),
      );
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
              {buyer.company_name} \ub300\uc0c1 Teaser \uc1a1\ubd80 \uad00\ub9ac
            </p>
            <p className="mt-1 text-xs text-text-secondary">
              \uac70\ub798\uc5d0 \ub4f1\ub85d\ub41c TM \ubc84\uc804 \uc911 \ud604\uc7ac \ub9e4\uc218\uc790\uc5d0\uac8c \uc1a1\ubd80\ub41c \ubc84\uc804\uc744 \ud55c \uac1c \uae30\uc900\uc73c\ub85c \uad00\ub9ac\ud569\ub2c8\ub2e4.
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <Badge variant={latestTeaser ? "info" : "neutral"}>
              {latestTeaser
                ? `\uc1a1\ubd80\ub428 ${latestTeaser.versionLabel}`
                : "\ubbf8\uc1a1\ubd80"}
            </Badge>
            <Badge variant="neutral">{teaserMaterials.length} version(s)</Badge>
          </div>
        </div>
        {latestTeaser ? (
          <p className="mt-2 text-xs text-text-secondary">
            \ucd5c\uc2e0 \uc1a1\ubd80\uc77c {getRecipientDistributionDate(latestTeaser.material)}
          </p>
        ) : null}
      </div>

      {hasTeasers ? (
        <DataTable<VersionedMarketingMaterial>
          columns={[
            {
              key: "versionLabel",
              header: "\ubc84\uc804",
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
              header: "\uc1a1\ubd80 \uc5ec\ubd80",
              render: (row) => {
                const isSent = isDistributedToRecipient(
                  row.material,
                  buyer.company_name,
                );

                return (
                  <div className="flex flex-col items-start gap-1">
                    <Badge variant={isSent ? "success" : "neutral"}>
                      {isSent ? "\uc1a1\ubd80\ub428" : "\ubbf8\uc1a1\ubd80"}
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
                        \ub2e4\uc6b4\ub85c\ub4dc
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
                            ? "\ud488\uc9c8 \uac80\uc99d\uc744 \ud1b5\uacfc\ud55c Teaser\ub9cc \uc1a1\ubd80\ud560 \uc218 \uc788\uc2b5\ub2c8\ub2e4."
                            : undefined
                        }
                        onClick={() => {
                          void handleSendTeaser(row);
                        }}
                      >
                        <Send className="mr-1 h-3.5 w-3.5" />
                        {isSent
                          ? "\ud604\uc7ac \uc1a1\ubd80\ubcf8"
                          : "\uc774 \ubc84\uc804 \uc1a1\ubd80"}
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
      ) : null}

      <FileUploadZone
        txnId={txnId}
        entityType="MARKETING_MATERIAL"
        entityId="TM"
        embedded
        embeddedLabel={hasTeasers ? "Teaser \uc5c5\ub85c\ub4dc" : ""}
        uploadLabel={"Teaser \uc5c5\ub85c\ub4dc"}
        emptyTitle={hasTeasers ? undefined : "\ub4f1\ub85d\ub41c Teaser \uc5c6\uc74c"}
        emptyDescription={
          hasTeasers
            ? "Teaser PDF/PPTX \ud30c\uc77c\uc744 \uc5ec\uae30\uc5d0 \ub4dc\ub86d\ud558\uac70\ub098 \uc5c5\ub85c\ub4dc \ubc84\ud2bc\uc73c\ub85c \ucd94\uac00\ud558\uc138\uc694."
            : "Teaser \uc790\ub8cc\ub97c \uc5c5\ub85c\ub4dc\ud558\uba74 \ub9e4\uc218\uc790\ubcc4 \uc1a1\ubd80 \ubc84\uc804\uacfc \uc1a1\ubd80 \uc5ec\ubd80\ub97c \uc5ec\uae30\uc11c \uad00\ub9ac\ud560 \uc218 \uc788\uc2b5\ub2c8\ub2e4."
        }
        emptyHint={
          hasTeasers
            ? "PDF \uc5c5\ub85c\ub4dc\ub294 OCR \uac80\ud1a0\ub97c \uc5f4\uace0, \uac80\ud1a0 \ud655\uc815 \ud6c4 TM \uc790\ub8cc\ub85c \uc5f0\uacb0\ud560 \uc218 \uc788\uc2b5\ub2c8\ub2e4."
            : "Teaser PDF/PPTX \ud30c\uc77c\uc744 \uc5ec\uae30\uc5d0 \ub4dc\ub86d\ud558\uac70\ub098 \ud074\ub9ad\ud558\uc5ec \ucd94\uac00\ud558\uc138\uc694. PDF \uc5c5\ub85c\ub4dc\ub294 OCR \uac80\ud1a0\ub97c \uc5f4\uace0, \uac80\ud1a0 \ud655\uc815 \ud6c4 TM \uc790\ub8cc\ub85c \uc5f0\uacb0\ud560 \uc218 \uc788\uc2b5\ub2c8\ub2e4."
        }
        embeddedSeparator={hasTeasers}
        showUploadAction={hasTeasers}
        onUploaded={onUploaded}
        readOnly={!canWrite}
      />
    </Card>
  );
}
