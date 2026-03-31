import { useCallback, useMemo, useRef, useState } from "react";
import { FileText, Send, Trash2 } from "lucide-react";

import {
  Badge,
  Button,
  Card,
  DataTable,
  EmptyState,
  Modal,
} from "@/components/ui";
import {
  openAttachmentFilePicker,
  uploadAttachmentFiles,
} from "@/modules/ma/components/attachmentUploadUtils";
import DistributionModal from "@/modules/ma/components/DistributionModal";
import FileUploadZone from "@/modules/ma/components/FileUploadZone";
import ExtractionReviewModal from "@/modules/ma/components/extraction/ExtractionReviewModal";
import MMSourceRoutingPreviewPanel from "@/modules/ma/components/marketing/MMSourceRoutingPreviewPanel";
import {
  getAttachmentDownloadUrl,
  useAttachments,
  useDeleteAttachment,
  useUploadAttachment,
} from "@/modules/ma/hooks/useAttachments";
import {
  canStartExtractionFromUpload,
  useAttachmentExtractionFlow,
} from "@/modules/ma/hooks/useAttachmentExtractionFlow";
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
import { cn } from "@/lib/cn";

interface MarketingMaterialsTabProps {
  txnId: string;
  canWrite: boolean;
  showSourcePreview?: boolean;
  surface?: "card" | "flat";
}

type ExternalMarketingUpload = Attachment & {
  docType: MarketingDocType | null;
};

const EMPTY_MARKETING_MATERIALS: MarketingMaterial[] = [];
const EMPTY_ATTACHMENTS: Attachment[] = [];

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
    generateDescription: "Teaser Memo 초안을 생성해 바로 관리합니다.",
    uploadTitle: "TM 업로드",
    uploadDescription: "외부에서 작성한 TM 파일을 바로 등록합니다.",
    materialTitle: "Teaser Memo",
  },
  DM: {
    triggerLabel: "+ Discussion (DM)",
    triggerVariant: "secondary",
    modalTitle: "Discussion (DM)",
    generateTitle: "DM 생성",
    generateDescription: "Discussion Memo 초안을 생성합니다.",
    uploadTitle: "DM 업로드",
    uploadDescription: "외부에서 작성한 DM 파일을 바로 등록합니다.",
    materialTitle: "Discussion Memo",
  },
  IM: {
    triggerLabel: "+ Information (IM)",
    triggerVariant: "primary",
    modalTitle: "Information (IM)",
    generateTitle: "IM 생성",
    generateDescription: "Information Memo 초안을 생성합니다.",
    uploadTitle: "IM 업로드",
    uploadDescription: "외부에서 작성한 IM 파일을 업로드합니다.",
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

function buildUploadedMarketingMaterialTitle(
  fileName: string,
  fallbackTitle: string,
) {
  const stem = fileName.trim().replace(/\.[^.]+$/, "").trim();
  return stem || fallbackTitle;
}

function hasDraggedFiles(dataTransfer?: DataTransfer | null) {
  if (!dataTransfer) {
    return false;
  }

  const types = Array.from(dataTransfer.types ?? []);
  return types.includes("Files") || dataTransfer.files.length > 0;
}

interface MarketingMaterialInlineUploadCardProps {
  txnId: string;
  docType: MarketingDocType;
  title: string;
  description: string;
  onUploaded: (
    attachment: Attachment,
    file: File,
    docType: MarketingDocType,
  ) => Promise<void> | void;
}

function MarketingMaterialInlineUploadCard({
  txnId,
  docType,
  title,
  description,
  onUploaded,
}: MarketingMaterialInlineUploadCardProps) {
  const uploadMutation = useUploadAttachment(txnId);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const dragDepthRef = useRef(0);
  const [isDragActive, setIsDragActive] = useState(false);

  const handleUpload = useCallback(
    async (files: File[]) => {
      await uploadAttachmentFiles({
        files,
        entityType: "MARKETING_MATERIAL",
        entityId: docType,
        uploadMutation,
        onUploaded: (attachment, file) => onUploaded(attachment, file, docType),
      });
    },
    [docType, onUploaded, uploadMutation],
  );

  const openPicker = useCallback(() => {
    openAttachmentFilePicker(fileInputRef);
  }, []);

  return (
    <div
      data-file-dropzone="true"
      role="button"
      tabIndex={0}
      className={cn(
        "rounded-lg border border-gray-border bg-bg-cool/30 transition-colors outline-none",
        "cursor-pointer focus-visible:ring-2 focus-visible:ring-accent/30",
        isDragActive && "border-primary-300 bg-primary-50/40",
      )}
      onClick={openPicker}
      onKeyDown={(event) => {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          openPicker();
        }
      }}
      onDragEnter={(event) => {
        if (!hasDraggedFiles(event.dataTransfer)) {
          return;
        }
        event.preventDefault();
        event.stopPropagation();
        dragDepthRef.current += 1;
        setIsDragActive(true);
        event.dataTransfer.dropEffect = "copy";
      }}
      onDragOver={(event) => {
        if (!hasDraggedFiles(event.dataTransfer)) {
          return;
        }
        event.preventDefault();
        event.stopPropagation();
        setIsDragActive(true);
        event.dataTransfer.dropEffect = "copy";
      }}
      onDragLeave={(event) => {
        if (!hasDraggedFiles(event.dataTransfer)) {
          return;
        }
        event.preventDefault();
        event.stopPropagation();
        dragDepthRef.current = Math.max(0, dragDepthRef.current - 1);
        if (dragDepthRef.current === 0) {
          setIsDragActive(false);
        }
      }}
      onDrop={(event) => {
        if (!hasDraggedFiles(event.dataTransfer)) {
          return;
        }
        event.preventDefault();
        event.stopPropagation();
        dragDepthRef.current = 0;
        setIsDragActive(false);
        event.dataTransfer.dropEffect = "copy";
        void handleUpload(Array.from(event.dataTransfer.files));
      }}
    >
      <div className="border-b border-gray-border px-4 py-3">
        <p className="text-sm font-semibold text-text-dark">{title}</p>
        <p className="mt-1 text-xs leading-5 text-text-secondary">
          {description}
        </p>
      </div>
      <div className="min-h-[132px]" />
      <input
        ref={fileInputRef}
        type="file"
        className="sr-only"
        multiple
        tabIndex={-1}
        accept=".pdf,.docx,.doc,.xlsx,.xls,.pptx,.ppt,.hwp,.hwpx,.txt"
        onChange={(event) => {
          void handleUpload(Array.from(event.target.files ?? []));
          event.target.value = "";
        }}
      />
    </div>
  );
}

interface MarketingMaterialActionModalProps {
  open: boolean;
  txnId: string;
  docType: MarketingDocType;
  generating: boolean;
  onClose: () => void;
  onGenerate: (docType: MarketingDocType) => void;
  onUploaded: (
    attachment: Attachment,
    file: File,
    docType: MarketingDocType,
  ) => Promise<void> | void;
}

function MarketingMaterialActionModal({
  open,
  txnId,
  docType,
  generating,
  onClose,
  onGenerate,
  onUploaded,
}: MarketingMaterialActionModalProps) {
  const meta = DOC_TYPE_ACTION_META[docType];

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
      <div className="space-y-4">
        <div>
          <p className="text-sm font-semibold text-text-dark">
            {meta.modalTitle} 자료를 어떻게 준비할까요?
          </p>
          <p className="mt-1 text-sm text-text-secondary">
            생성하거나 업로드해 바로 관리할 수 있습니다.
          </p>
        </div>

        <div className="grid gap-3 sm:grid-cols-2">
          <Button
            type="button"
            variant="primary"
            className="h-auto min-h-[132px] flex-col items-stretch justify-start px-4 py-4 text-left whitespace-normal"
            loading={generating}
            onClick={() => onGenerate(docType)}
          >
            <div className="flex w-full items-center gap-2 text-sm font-semibold">
              <FileText className="h-4 w-4" />
              <span>{meta.generateTitle}</span>
            </div>
            <p className="w-full whitespace-normal break-keep text-xs leading-5 text-white/90">
              {meta.generateDescription}
            </p>
          </Button>

          {docType !== "IM" ? (
            <MarketingMaterialInlineUploadCard
              txnId={txnId}
              docType={docType}
              title={meta.uploadTitle}
              description={meta.uploadDescription}
              onUploaded={onUploaded}
            />
          ) : (
            <div className="rounded-lg border border-gray-border bg-bg-cool/30">
              <div className="border-b border-gray-border px-4 py-3">
                <p className="text-sm font-semibold text-text-dark">
                  {meta.uploadTitle}
                </p>
                <p className="mt-1 text-xs leading-5 text-text-secondary">
                  {meta.uploadDescription}
                </p>
              </div>
              <FileUploadZone
                txnId={txnId}
                entityType="MARKETING_MATERIAL"
                entityId={docType}
                embedded
                embeddedLabel=""
                uploadLabel="파일 업로드"
                emptyDescription="IM 파일을 여기에 드롭해 업로드하세요."
                emptyHint="PDF는 OCR 검토를 열고, 다른 파일은 첨부로 저장됩니다."
                embeddedSeparator={false}
                onUploaded={(attachment, file) =>
                  onUploaded(attachment, file, docType)
                }
              />
            </div>
          )}
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
  const { activeReview, closeReview, startExtractionFromUpload } =
    useAttachmentExtractionFlow(txnId);
  const [distTarget, setDistTarget] = useState<MarketingMaterial | null>(null);
  const [actionTarget, setActionTarget] = useState<MarketingDocType | null>(
    null,
  );
  const isFlatSurface = surface === "flat";

  const managedMaterials = useMemo(
    () => marketingMaterials ?? EMPTY_MARKETING_MATERIALS,
    [marketingMaterials],
  );
  const marketingAttachments = useMemo(
    () => uploadedMaterials?.items ?? EMPTY_ATTACHMENTS,
    [uploadedMaterials?.items],
  );
  const linkedAttachmentIds = useMemo(
    () =>
      new Set(
        managedMaterials
          .map((material) => material.attachment_id)
          .filter((attachmentId): attachmentId is string => Boolean(attachmentId)),
      ),
    [managedMaterials],
  );
  const generatedMaterials = managedMaterials;
  const uploadedMaterialRecords = managedMaterials.filter(
    (material) => material.source_mode === "UPLOADED",
  );
  const externalUploads: ExternalMarketingUpload[] = marketingAttachments
    .filter((attachment) => !linkedAttachmentIds.has(attachment.id))
    .map((attachment) => ({
      ...attachment,
      docType: resolveMarketingDocType(attachment.entity_id),
    }));

  const hasGeneratedMaterials = generatedMaterials.length > 0;
  const hasUploadedMaterialRecords = uploadedMaterialRecords.length > 0;
  const hasExternalUploads = externalUploads.length > 0;
  const hasAnyMaterials =
    hasGeneratedMaterials || hasUploadedMaterialRecords || hasExternalUploads;

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

  const handleUploadedMaterial = useCallback(
    async (
      attachment: Attachment,
      file: File,
      docType: MarketingDocType,
    ) => {
      try {
        const material = await createMarketingMaterial.mutateAsync({
          doc_type: docType,
          title: buildUploadedMarketingMaterialTitle(
            file.name,
            buildMarketingMaterialPayload(docType, txn?.code_name ?? undefined).title,
          ),
          project_code: txn?.code_name ?? undefined,
          attachment_id: attachment.id,
        });

        if (canStartExtractionFromUpload(attachment, file)) {
          await startExtractionFromUpload({
            attachment,
            file,
            docCategoryHint: "TEASER_IM",
            reviewContext: {
              source: "marketing-material",
              marketingDocType: docType,
              marketingMaterialId: material.id,
            },
          });
        }
      } catch {
        // Mutation hook already surfaces the error.
      } finally {
        setActionTarget(null);
      }
    },
    [createMarketingMaterial, startExtractionFromUpload, txn?.code_name],
  );

  return (
    <div className="space-y-4">
      {showSourcePreview && <MMSourceRoutingPreviewPanel txnId={txnId} />}

      <Card
        padding="none"
        className={
          isFlatSurface
            ? "border-0 shadow-none rounded-none bg-transparent"
            : undefined
        }
      >
        {canWrite ? (
          <div className="flex flex-wrap justify-end gap-2 border-b border-gray-border px-5 py-3">
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
        ) : null}
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
          generating={createMarketingMaterial.isPending}
          onClose={() => setActionTarget(null)}
          onGenerate={handleGenerateMaterial}
          onUploaded={handleUploadedMaterial}
        />
      )}

      <ExtractionReviewModal
        txnId={txnId}
        extraction={activeReview?.extraction ?? null}
        reviewContext={activeReview?.context}
        open={activeReview !== null}
        onClose={closeReview}
      />
    </div>
  );
}
