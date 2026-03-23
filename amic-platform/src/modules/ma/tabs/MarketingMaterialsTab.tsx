import { type ChangeEvent, useCallback, useRef, useState } from "react";
import { FileText, Send, Trash2, Upload } from "lucide-react";

import {
  Badge,
  Button,
  Card,
  DataTable,
  EmptyState,
  Modal,
} from "@/components/ui";
import DistributionModal from "@/modules/ma/components/DistributionModal";
import MMSourceRoutingPreviewPanel from "@/modules/ma/components/marketing/MMSourceRoutingPreviewPanel";
import {
  getAttachmentDownloadUrl,
  useAttachments,
  useDeleteAttachment,
  useUploadAttachment,
} from "@/modules/ma/hooks/useAttachments";
import {
  getDownloadUrl,
  useCreateMarketingMaterial,
  useDeleteMarketingMaterial,
  useMarketingMaterials,
} from "@/modules/ma/hooks/useMarketingMaterials";
import { useTransaction } from "@/modules/ma/hooks/useTransactions";
import type { Attachment } from "@/modules/ma/types/attachment";
import type {
  MarketingDocType,
  MarketingMaterial,
} from "@/modules/ma/types/marketing_material";
import {
  MARKETING_DOC_LABELS,
  MARKETING_STATUS_LABELS,
  QUALITY_STATUS_LABELS,
  QUALITY_STATUS_VARIANT,
} from "@/modules/ma/types/marketing_material";
import { formatFileSize, formatISODate } from "@/modules/ma/utils/format";
import {
  openAttachmentFilePicker,
  uploadAttachmentFiles,
} from "@/modules/ma/components/attachmentUploadUtils";

interface MarketingMaterialsTabProps {
  txnId: string;
  canWrite: boolean;
  showSourcePreview?: boolean;
  surface?: "card" | "flat";
}

type ExternalMarketingUpload = Attachment & {
  docType: MarketingDocType | null;
};

const DOC_TYPE_ACTION_META: Record<
  MarketingDocType,
  {
    triggerLabel: string;
    triggerVariant: "primary" | "secondary";
    modalTitle: string;
    generateTitle: string;
    generateDescription: string;
    uploadTitle: string;
    uploadDescription: string;
    materialTitle: string;
  }
> = {
  TM: {
    triggerLabel: "+ Teaser (TM)",
    triggerVariant: "secondary",
    modalTitle: "Teaser (TM)",
    generateTitle: "TM 생성",
    generateDescription: "플랫폼에서 Teaser Memo 초안을 생성해 바로 관리합니다.",
    uploadTitle: "TM 업로드",
    uploadDescription: "외부에서 작성한 TM 파일을 올려 기존 자료 흐름에 합칩니다.",
    materialTitle: "Teaser Memo",
  },
  DM: {
    triggerLabel: "+ Discussion (DM)",
    triggerVariant: "secondary",
    modalTitle: "Discussion (DM)",
    generateTitle: "DM 생성",
    generateDescription:
      "플랫폼에서 Discussion Memo 초안을 생성해 버전과 배포를 이어갑니다.",
    uploadTitle: "DM 업로드",
    uploadDescription: "외부에서 작성한 DM 파일을 올려 동일한 화면에서 관리합니다.",
    materialTitle: "Discussion Memo",
  },
  IM: {
    triggerLabel: "+ Information (IM)",
    triggerVariant: "primary",
    modalTitle: "Information (IM)",
    generateTitle: "IM 생성",
    generateDescription:
      "플랫폼에서 Information Memo 초안을 생성해 후속 배포까지 연결합니다.",
    uploadTitle: "IM 업로드",
    uploadDescription: "외부에서 작성한 IM 파일을 올려 자료 이력을 이어서 관리합니다.",
    materialTitle: "Information Memo",
  },
};

const DOC_TYPE_BADGE_VARIANT: Record<
  MarketingDocType,
  "info" | "warning" | "success"
> = {
  TM: "info",
  DM: "warning",
  IM: "success",
};

function resolveMarketingDocType(
  entityId: string | null,
): MarketingDocType | null {
  if (entityId === "TM" || entityId === "DM" || entityId === "IM") {
    return entityId;
  }
  return null;
}

function renderDocTypeBadge(docType: MarketingDocType | null) {
  if (!docType) {
    return (
      <Badge variant="neutral" pill>
        {"\uAE30\uD0C0"}
      </Badge>
    );
  }

  return (
    <Badge variant={DOC_TYPE_BADGE_VARIANT[docType]} pill>
      {docType}
    </Badge>
  );
}

function buildMarketingMaterialPayload(
  docType: MarketingDocType,
  projectCode?: string,
) {
  return {
    doc_type: docType,
    title: `${projectCode ?? "Project"} - ${DOC_TYPE_ACTION_META[docType].materialTitle}`,
    project_code: projectCode ?? undefined,
  };
}

interface MarketingMaterialActionModalProps {
  open: boolean;
  txnId: string;
  docType: MarketingDocType;
  projectCode?: string;
  generating: boolean;
  onClose: () => void;
  onGenerate: (docType: MarketingDocType) => void;
}

function MarketingMaterialActionModal({
  open,
  txnId,
  docType,
  projectCode,
  generating,
  onClose,
  onGenerate,
}: MarketingMaterialActionModalProps) {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const uploadMutation = useUploadAttachment(txnId);
  const meta = DOC_TYPE_ACTION_META[docType];

  const handlePickFile = useCallback(() => {
    openAttachmentFilePicker(fileInputRef);
  }, []);

  const handleFileSelect = useCallback(
    async (event: ChangeEvent<HTMLInputElement>) => {
      const files = Array.from(event.target.files ?? []);
      if (files.length === 0) {
        return;
      }

      await uploadAttachmentFiles({
        files,
        entityType: "MARKETING_MATERIAL",
        entityId: docType,
        uploadMutation,
      });
      event.target.value = "";
      onClose();
    },
    [docType, onClose, uploadMutation],
  );

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={`${meta.modalTitle} 선택`}
      size="md"
      footer={
        <Button type="button" variant="ghost" onClick={onClose}>
          닫기
        </Button>
      }
    >
      <input
        ref={fileInputRef}
        type="file"
        className="sr-only"
        multiple
        tabIndex={-1}
        onChange={handleFileSelect}
      />

      <div className="space-y-4">
        <div>
          <p className="text-sm font-semibold text-text-dark">
            {meta.modalTitle} 자료를 어떻게 준비할까요?
          </p>
          <p className="mt-1 text-sm text-text-secondary">
            새로 생성하거나, 이미 작성된 파일을 업로드해서 같은 자료 흐름에서
            관리할 수 있습니다.
          </p>
          {projectCode && (
            <p className="mt-2 text-xs text-text-secondary">
              생성 시 제목: {buildMarketingMaterialPayload(docType, projectCode).title}
            </p>
          )}
        </div>

        <div className="grid gap-3 sm:grid-cols-2">
          <Button
            type="button"
            variant="primary"
            className="h-auto min-h-[132px] flex-col items-start justify-start px-4 py-4 text-left"
            loading={generating}
            disabled={uploadMutation.isPending}
            onClick={() => onGenerate(docType)}
          >
            <div className="flex items-center gap-2 text-sm font-semibold">
              <FileText className="h-4 w-4" />
              <span>{meta.generateTitle}</span>
            </div>
            <p className="text-xs leading-5 text-white/90">
              {meta.generateDescription}
            </p>
          </Button>

          <Button
            type="button"
            variant="secondary"
            className="h-auto min-h-[132px] flex-col items-start justify-start px-4 py-4 text-left"
            loading={uploadMutation.isPending}
            disabled={generating}
            onClick={handlePickFile}
          >
            <div className="flex items-center gap-2 text-sm font-semibold">
              <Upload className="h-4 w-4" />
              <span>{meta.uploadTitle}</span>
            </div>
            <p className="text-xs leading-5 text-text-secondary">
              {meta.uploadDescription}
            </p>
          </Button>
        </div>
      </div>
    </Modal>
  );
}

export default function MarketingMaterialsTab({
  txnId,
  canWrite,
  showSourcePreview = true,
  surface = "card",
}: MarketingMaterialsTabProps) {
  const { data: txn } = useTransaction(txnId);
  const { data: marketingMaterials } = useMarketingMaterials(txnId);
  const { data: uploadedMaterials } = useAttachments(
    txnId,
    "MARKETING_MATERIAL",
  );
  const createMarketingMaterial = useCreateMarketingMaterial(txnId);
  const deleteMarketingMaterial = useDeleteMarketingMaterial(txnId);
  const deleteAttachment = useDeleteAttachment(txnId);
  const [distTarget, setDistTarget] = useState<MarketingMaterial | null>(null);
  const [actionTarget, setActionTarget] = useState<MarketingDocType | null>(
    null,
  );
  const isFlatSurface = surface === "flat";

  const generatedMaterials = marketingMaterials ?? [];
  const externalUploads: ExternalMarketingUpload[] = (
    uploadedMaterials?.items ?? []
  ).map((attachment) => ({
    ...attachment,
    docType: resolveMarketingDocType(attachment.entity_id),
  }));

  const hasGeneratedMaterials = generatedMaterials.length > 0;
  const hasExternalUploads = externalUploads.length > 0;
  const hasAnyMaterials = hasGeneratedMaterials || hasExternalUploads;

  const handleGenerateMaterial = useCallback(
    (docType: MarketingDocType) => {
      createMarketingMaterial.mutate(
        buildMarketingMaterialPayload(docType, txn?.code_name ?? undefined),
        {
          onSuccess: () => setActionTarget(null),
        },
      );
    },
    [createMarketingMaterial, txn?.code_name],
  );

  return (
    <div className="space-y-4">
      {showSourcePreview && <MMSourceRoutingPreviewPanel txnId={txnId} />}

      <Card
        title={"\uB9C8\uCF00\uD305 \uC790\uB8CC"}
        headerBar
        padding="none"
        className={
          isFlatSurface
            ? "border-0 shadow-none rounded-none bg-transparent"
            : undefined
        }
        actions={
          canWrite ? (
            <div className="flex flex-wrap justify-end gap-2">
              {(["TM", "DM", "IM"] as MarketingDocType[]).map((docType) => (
                <Button
                  key={docType}
                  size="sm"
                  variant={DOC_TYPE_ACTION_META[docType].triggerVariant}
                  onClick={() => setActionTarget(docType)}
                >
                  {DOC_TYPE_ACTION_META[docType].triggerLabel}
                </Button>
              ))}
            </div>
          ) : undefined
        }
      >
        {!hasAnyMaterials ? (
          <EmptyState
            icon={FileText}
            title={"\uB9C8\uCF00\uD305 \uC790\uB8CC \uC5C6\uC74C"}
            description={
              "TM, DM, IM \uC790\uB8CC\uB97C \uC0DD\uC131\uD558\uAC70\uB098 \uC678\uBD80\uC5D0\uC11C \uC791\uC131\uD55C \uD30C\uC77C\uC744 \uC5C5\uB85C\uB4DC\uD574 \uAD00\uB9AC\uD558\uC138\uC694."
            }
          />
        ) : (
          <>
            {hasGeneratedMaterials && (
              <div>
                <div className="px-5 py-3 border-b border-gray-border">
                  <p className="text-sm font-semibold text-text-dark">
                    {"\uC0DD\uC131 \uC790\uB8CC"}
                  </p>
                  <p className="mt-1 text-xs text-text-secondary">
                    {
                      "\uD50C\uB7AB\uD3FC\uC5D0\uC11C \uC0DD\uC131\uD55C TM, DM, IM \uC790\uB8CC\uC640 \uBC30\uD3EC \uC0C1\uD0DC\uB97C \uAD00\uB9AC\uD569\uB2C8\uB2E4."
                    }
                  </p>
                </div>
                <DataTable<MarketingMaterial>
                  columns={[
                    {
                      key: "doc_type",
                      label: "\uC720\uD615",
                      render: (row) => renderDocTypeBadge(row.doc_type),
                    },
                    { key: "title", label: "\uC81C\uBAA9" },
                    {
                      key: "status",
                      label: "\uC0C1\uD0DC",
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
                      label: "\uD488\uC9C8",
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
                          <span className="text-xs text-text-secondary">
                            --
                          </span>
                        ),
                    },
                    {
                      key: "slide_count",
                      label: "\uC2AC\uB77C\uC774\uB4DC",
                      render: (row) =>
                        row.slide_count != null ? (
                          <span className="text-xs">
                            {row.slide_count}
                            {"\uC7A5"}
                          </span>
                        ) : (
                          <span className="text-xs text-text-secondary">
                            --
                          </span>
                        ),
                    },
                    {
                      key: "pipeline_metrics",
                      label: "\uC18C\uC694 \uC2DC\uAC04",
                      render: (row) => {
                        const total = row.pipeline_metrics?.total_ms;
                        if (total == null) {
                          return (
                            <span className="text-xs text-text-secondary">
                              --
                            </span>
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
                      label: "\uBC30\uD3EC",
                      render: (row) =>
                        row.distributed_to?.length
                          ? `${row.distributed_to.length}\uACF3`
                          : "\uBBF8\uBC30\uD3EC",
                    },
                    {
                      key: "file_size_bytes",
                      label: "\uD06C\uAE30",
                      render: (row) => formatFileSize(row.file_size_bytes),
                    },
                    {
                      key: "id",
                      label: "\uC791\uC5C5",
                      render: (row) => (
                        <div className="flex gap-2">
                          {(row.status === "READY" ||
                            row.status === "CONDITIONAL_READY") && (
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
                                {"\uB2E4\uC6B4\uB85C\uB4DC"}
                              </Button>
                              {canWrite && (
                                <Button
                                  size="sm"
                                  variant="ghost"
                                  onClick={() => setDistTarget(row)}
                                  disabled={row.distribution_eligible !== true}
                                  title={
                                    row.distribution_eligible !== true
                                      ? "\uD488\uC9C8 \uAC80\uC99D\uC744 \uD1B5\uACFC\uD55C \uC790\uB8CC\uB9CC \uBC30\uD3EC\uD560 \uC218 \uC788\uC2B5\uB2C8\uB2E4."
                                      : undefined
                                  }
                                >
                                  <Send size={14} className="mr-1" />
                                  {"\uBC30\uD3EC"}
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
                                    "\uB9C8\uCF00\uD305 \uC790\uB8CC\uB97C \uC0AD\uC81C\uD558\uC2DC\uACA0\uC2B5\uB2C8\uAE4C? \uC774 \uC791\uC5C5\uC740 \uB418\uB3CC\uB9B4 \uC218 \uC5C6\uC2B5\uB2C8\uB2E4.",
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
                  data={generatedMaterials}
                  keyField="id"
                />
              </div>
            )}

            {hasExternalUploads && (
              <div className={hasGeneratedMaterials ? "border-t border-gray-border" : undefined}>
                <div className="px-5 py-3 border-b border-gray-border">
                  <p className="text-sm font-semibold text-text-dark">
                    {"\uC678\uBD80 \uC5C5\uB85C\uB4DC \uC790\uB8CC"}
                  </p>
                  <p className="mt-1 text-xs text-text-secondary">
                    {
                      "\uBCC4\uB3C4\uB85C \uC791\uC131\uD55C TM, DM, IM \uD30C\uC77C\uC744 \uC5C5\uB85C\uB4DC\uD558\uACE0 \uB0B4\uB824\uBC1B\uC744 \uC218 \uC788\uC2B5\uB2C8\uB2E4."
                    }
                  </p>
                </div>
                <DataTable<ExternalMarketingUpload>
                  columns={[
                    {
                      key: "docType",
                      label: "\uC720\uD615",
                      render: (row) => renderDocTypeBadge(row.docType),
                    },
                    { key: "file_name", label: "\uD30C\uC77C\uBA85" },
                    {
                      key: "description",
                      label: "\uC124\uBA85",
                      render: (row) =>
                        row.description ??
                        (row.docType
                          ? `${MARKETING_DOC_LABELS[row.docType]} \uC5C5\uB85C\uB4DC\uBCF8`
                          : "\uC678\uBD80 \uC5C5\uB85C\uB4DC \uC790\uB8CC"),
                    },
                    {
                      key: "file_size_bytes",
                      label: "\uD06C\uAE30",
                      render: (row) => formatFileSize(row.file_size_bytes),
                    },
                    {
                      key: "created_at",
                      label: "\uC5C5\uB85C\uB4DC\uC77C",
                      render: (row) => formatISODate(row.created_at),
                    },
                    {
                      key: "id",
                      label: "\uC791\uC5C5",
                      render: (row) => (
                        <div className="flex gap-2">
                          <Button
                            size="sm"
                            variant="ghost"
                            onClick={() =>
                              window.open(
                                getAttachmentDownloadUrl(txnId, row.id),
                                "_blank",
                              )
                            }
                          >
                            {"\uB2E4\uC6B4\uB85C\uB4DC"}
                          </Button>
                          {canWrite && (
                            <Button
                              size="sm"
                              variant="ghost"
                              onClick={() => {
                                if (
                                  window.confirm(
                                    "\uC5C5\uB85C\uB4DC\uD55C \uB9C8\uCF00\uD305 \uC790\uB8CC\uB97C \uC0AD\uC81C\uD558\uC2DC\uACA0\uC2B5\uB2C8\uAE4C? \uC774 \uC791\uC5C5\uC740 \uB418\uB3CC\uB9B4 \uC218 \uC5C6\uC2B5\uB2C8\uB2E4.",
                                  )
                                ) {
                                  deleteAttachment.mutate(row.id);
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
                  data={externalUploads}
                  keyField="id"
                />
              </div>
            )}
          </>
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

      {actionTarget && (
        <MarketingMaterialActionModal
          open={!!actionTarget}
          txnId={txnId}
          docType={actionTarget}
          projectCode={txn?.code_name ?? undefined}
          generating={createMarketingMaterial.isPending}
          onClose={() => setActionTarget(null)}
          onGenerate={handleGenerateMaterial}
        />
      )}
    </div>
  );
}
