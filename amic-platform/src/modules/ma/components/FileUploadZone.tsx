import {
  ChevronDown,
  ChevronRight,
  Download,
  FileText,
  Paperclip,
  RefreshCw,
  Trash2,
  Upload,
} from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { Button } from "@/components/ui/Button";
import { cn } from "@/lib/cn";
import {
  getAttachmentDownloadUrl,
  useAttachments,
  useDeleteAttachment,
  useRetryAttachmentProcessing,
  useUploadAttachment,
} from "@/modules/ma/hooks/useAttachments";
import {
  type AttachmentUploadHandler,
  openAttachmentFilePicker,
  uploadAttachmentFiles,
} from "@/modules/ma/components/attachmentUploadUtils";
import type { AttachmentEntityType } from "@/modules/ma/types/attachment";
import {
  ATTACHMENT_CONSTRAINTS,
  ATTACHMENT_MIME_LABELS,
} from "@/modules/ma/types/attachment";
import { formatFileSize, formatISODate } from "@/modules/ma/utils/format";

interface FileUploadZoneProps {
  txnId: string;
  entityType: AttachmentEntityType;
  entityId?: string;
  entityIds?: string[];
  resolveEntityId?: () => Promise<string | undefined>;
  compact?: boolean;
  embedded?: boolean;
  readOnly?: boolean;
  title?: string;
  embeddedLabel?: string;
  uploadLabel?: string;
  emptyTitle?: string;
  emptyDescription?: string;
  emptyHint?: string;
  emptyVariant?: "plain" | "dashed";
  embeddedSeparator?: boolean;
  showUploadAction?: boolean;
  registerOpenPicker?: (openPicker: (() => void) | null) => void;
  onUploaded?: AttachmentUploadHandler;
  suppressListErrorToast?: boolean;
  listErrorMessage?: string;
  uploadOnly?: boolean;
}

function hasDraggedFiles(dataTransfer?: DataTransfer | null) {
  if (!dataTransfer) {
    return false;
  }

  const types = Array.from(dataTransfer.types ?? []);
  return types.includes("Files") || dataTransfer.files.length > 0;
}

function getProcessingLabel(status: string) {
  switch (status) {
    case "SYNCED":
      return {
        label: "동기화 완료",
        className: "bg-emerald-50 text-emerald-700",
      };
    case "RUNNING":
      return {
        label: "처리 중",
        className: "bg-blue-50 text-blue-700",
      };
    case "FAILED":
      return {
        label: "후속 처리 실패",
        className: "bg-amber-50 text-amber-700",
      };
    case "SKIPPED":
      return {
        label: "처리 생략",
        className: "bg-slate-100 text-slate-600",
      };
    case "PENDING":
    default:
      return {
        label: "처리 대기",
        className: "bg-sky-50 text-sky-700",
      };
  }
}

export default function FileUploadZone({
  txnId,
  entityType,
  entityId,
  entityIds,
  resolveEntityId,
  compact = false,
  embedded = false,
  readOnly = false,
  title = "첨부 파일",
  embeddedLabel = "첨부 파일",
  uploadLabel = "업로드",
  emptyTitle,
  emptyDescription = "파일을 여기에 드롭하거나 클릭해서 업로드하세요.",
  emptyHint = `최대 ${ATTACHMENT_CONSTRAINTS.MAX_FILE_SIZE_LABEL}, PDF/DOCX/XLSX/PPTX/HWP 지원`,
  emptyVariant = "plain",
  embeddedSeparator = true,
  showUploadAction = true,
  registerOpenPicker,
  onUploaded,
  suppressListErrorToast = false,
  listErrorMessage = "기존 첨부 목록을 불러오지 못했습니다. 업로드는 계속 가능합니다.",
  uploadOnly = false,
}: FileUploadZoneProps) {
  const [expanded, setExpanded] = useState(!compact);
  const [isEmptyDropActive, setIsEmptyDropActive] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const emptyDragDepthRef = useRef(0);

  const { data, isError: isListError } = useAttachments(
    txnId,
    entityType,
    entityId,
    {
      enabled: !uploadOnly,
      refetchWhileProcessing: !uploadOnly,
      suppressGlobalErrorToast: suppressListErrorToast,
    },
  );
  const uploadMutation = useUploadAttachment(txnId);
  const deleteMutation = useDeleteAttachment(txnId);
  const retryProcessingMutation = useRetryAttachmentProcessing(txnId);

  const items = useMemo(() => {
    const rawItems = data?.items ?? [];
    if (!entityIds) {
      return rawItems;
    }
    if (entityIds.length === 0) {
      return [];
    }

    const entityIdSet = new Set(entityIds);
    return rawItems.filter(
      (attachment) =>
        attachment.entity_id !== null && entityIdSet.has(attachment.entity_id),
    );
  }, [data?.items, entityIds]);

  const isEmpty = items.length === 0;

  const handleUpload = useCallback(
    async (files: File[]) => {
      if (files.length === 0) {
        return;
      }

      for (const file of files) {
        let resolvedEntityId = entityId;

        if (resolveEntityId) {
          try {
            resolvedEntityId = await resolveEntityId();
          } catch {
            return;
          }
        }

        await uploadAttachmentFiles({
          files: [file],
          entityType,
          entityId: resolvedEntityId,
          uploadMutation,
          onUploaded,
        });
      }
    },
    [entityId, entityType, onUploaded, resolveEntityId, uploadMutation],
  );

  const handleDrop = useCallback(
    (event: React.DragEvent<HTMLElement>) => {
      if (!hasDraggedFiles(event.dataTransfer)) {
        return;
      }

      event.preventDefault();
      event.stopPropagation();
      event.dataTransfer.dropEffect = "copy";
      void handleUpload(Array.from(event.dataTransfer.files));
    },
    [handleUpload],
  );

  const handleDragOver = useCallback((event: React.DragEvent<HTMLElement>) => {
    if (!hasDraggedFiles(event.dataTransfer)) {
      return;
    }

    event.preventDefault();
    event.dataTransfer.dropEffect = "copy";
  }, []);

  const handleFileSelect = useCallback(
    (event: React.ChangeEvent<HTMLInputElement>) => {
      void handleUpload(Array.from(event.target.files ?? []));
      event.target.value = "";
    },
    [handleUpload],
  );

  const handleEmptyDragEnter = useCallback(
    (event: React.DragEvent<HTMLDivElement>) => {
      if (!hasDraggedFiles(event.dataTransfer) || readOnly) {
        return;
      }

      event.preventDefault();
      event.stopPropagation();
      emptyDragDepthRef.current += 1;
      setIsEmptyDropActive(true);
      event.dataTransfer.dropEffect = "copy";
    },
    [readOnly],
  );

  const handleEmptyDragOver = useCallback(
    (event: React.DragEvent<HTMLDivElement>) => {
      if (!hasDraggedFiles(event.dataTransfer) || readOnly) {
        return;
      }

      event.preventDefault();
      event.stopPropagation();
      setIsEmptyDropActive(true);
      event.dataTransfer.dropEffect = "copy";
    },
    [readOnly],
  );

  const handleEmptyDragLeave = useCallback(
    (event: React.DragEvent<HTMLDivElement>) => {
      if (!hasDraggedFiles(event.dataTransfer) || readOnly) {
        return;
      }

      event.preventDefault();
      event.stopPropagation();
      emptyDragDepthRef.current = Math.max(0, emptyDragDepthRef.current - 1);
      if (emptyDragDepthRef.current === 0) {
        setIsEmptyDropActive(false);
      }
    },
    [readOnly],
  );

  const handleEmptyDrop = useCallback(
    (event: React.DragEvent<HTMLDivElement>) => {
      if (!hasDraggedFiles(event.dataTransfer) || readOnly) {
        return;
      }

      event.preventDefault();
      event.stopPropagation();
      emptyDragDepthRef.current = 0;
      setIsEmptyDropActive(false);
      event.dataTransfer.dropEffect = "copy";
      void handleUpload(Array.from(event.dataTransfer.files));
    },
    [handleUpload, readOnly],
  );

  const openPicker = useCallback(() => {
    openAttachmentFilePicker(fileInputRef);
  }, []);

  useEffect(() => {
    registerOpenPicker?.(readOnly ? null : openPicker);

    return () => {
      registerOpenPicker?.(null);
    };
  }, [openPicker, readOnly, registerOpenPicker]);

  useEffect(() => {
    if (!isEmpty || readOnly) {
      emptyDragDepthRef.current = 0;
      setIsEmptyDropActive(false);
    }
  }, [isEmpty, readOnly]);

  const hiddenInput = !readOnly && (
    <input
      ref={fileInputRef}
      type="file"
      className="sr-only"
      multiple
      tabIndex={-1}
      accept={ATTACHMENT_CONSTRAINTS.ACCEPT_EXTENSIONS}
      onChange={handleFileSelect}
    />
  );

  const listErrorBanner = !uploadOnly && isListError ? (
    <div className="mb-3 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-800">
      {listErrorMessage}
    </div>
  ) : null;

  const fileList = isEmpty ? (
    <div
      data-file-dropzone="true"
      className={cn(
        "flex flex-col items-center justify-center gap-2 text-center text-sm text-text-muted",
        emptyVariant === "dashed"
          ? "rounded-2xl border border-dashed px-6 py-10"
          : "py-8",
        emptyVariant === "dashed" &&
          (isEmptyDropActive
            ? "border-primary-300 bg-primary-50/40"
            : "border-gray-border bg-bg-cool/20"),
        !readOnly && "cursor-pointer",
      )}
      onClick={readOnly ? undefined : openPicker}
      onDragEnter={handleEmptyDragEnter}
      onDragOver={handleEmptyDragOver}
      onDragLeave={handleEmptyDragLeave}
      onDrop={handleEmptyDrop}
      onKeyDown={
        readOnly
          ? undefined
          : (event) => {
              if (event.key === "Enter" || event.key === " ") {
                event.preventDefault();
                openPicker();
              }
            }
      }
      role={readOnly ? undefined : "button"}
      tabIndex={readOnly ? undefined : 0}
    >
      <Upload
        className={cn(
          "text-text-muted",
          emptyVariant === "dashed" ? "h-10 w-10" : "h-8 w-8",
        )}
      />
      {emptyTitle ? (
        <p className="text-lg font-semibold text-text-dark">{emptyTitle}</p>
      ) : null}
      <p className={cn("max-w-2xl", emptyTitle && "text-text-body")}>
        {emptyDescription}
      </p>
      <p className="max-w-2xl text-xs text-text-secondary">{emptyHint}</p>
    </div>
  ) : (
    <table className="w-full text-sm">
      <thead className="border-b border-gray-border text-left text-xs text-text-secondary">
        <tr>
          <th className="px-5 py-2 font-medium">파일명</th>
          <th className="px-5 py-2 font-medium">형식</th>
          <th className="px-5 py-2 font-medium">크기</th>
          <th className="px-5 py-2 font-medium">처리 상태</th>
          <th className="px-5 py-2 font-medium">업로드일</th>
          <th className="px-5 py-2 font-medium" />
        </tr>
      </thead>
      <tbody>
        {items.map((attachment) => {
          const processing = getProcessingLabel(attachment.processing_status);

          return (
            <tr
              key={attachment.id}
              className="border-b border-gray-border/50 hover:bg-bg-cool/50"
            >
              <td className="px-5 py-2">
                <div className="flex items-center gap-2">
                  <FileText className="h-4 w-4 shrink-0 text-text-muted" />
                  <div className="min-w-0">
                    <span className="block truncate" title={attachment.file_name}>
                      {attachment.file_name}
                    </span>
                    {attachment.processing_error ? (
                      <span className="block truncate text-xs text-amber-700">
                        {attachment.processing_error}
                      </span>
                    ) : null}
                  </div>
                </div>
              </td>
              <td className="px-5 py-2 text-text-secondary">
                {ATTACHMENT_MIME_LABELS[attachment.mime_type] ??
                  attachment.mime_type.split("/")[1]}
              </td>
              <td className="px-5 py-2 text-text-secondary">
                {formatFileSize(attachment.file_size_bytes)}
              </td>
              <td className="px-5 py-2">
                <span
                  className={cn(
                    "inline-flex rounded-full px-2 py-0.5 text-xs font-medium",
                    processing.className,
                  )}
                >
                  {processing.label}
                </span>
              </td>
              <td className="px-5 py-2 text-text-secondary">
                {formatISODate(attachment.created_at)}
              </td>
              <td className="px-5 py-2">
                <div className="flex items-center justify-end gap-1">
                  {attachment.processing_status === "FAILED" && !readOnly ? (
                    <button
                      type="button"
                      className="rounded p-1 text-text-muted hover:bg-bg-cool hover:text-primary"
                      title="후속 처리 재시도"
                      onClick={() =>
                        retryProcessingMutation.mutate(attachment.id)
                      }
                    >
                      <RefreshCw className="h-4 w-4" />
                    </button>
                  ) : null}
                  <a
                    href={getAttachmentDownloadUrl(txnId, attachment.id)}
                    className="rounded p-1 text-text-muted hover:bg-bg-cool hover:text-info"
                    title="다운로드"
                  >
                    <Download className="h-4 w-4" />
                  </a>
                  {!readOnly ? (
                    <button
                      type="button"
                      className="rounded p-1 text-text-muted hover:bg-bg-cool hover:text-negative"
                      title="삭제"
                      onClick={() => deleteMutation.mutate(attachment.id)}
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  ) : null}
                </div>
              </td>
            </tr>
          );
        })}
      </tbody>
    </table>
  );

  if (embedded) {
    const showEmbeddedLabel =
      embeddedLabel.trim().length > 0 && items.length > 0;
    const showEmbeddedHeader =
      showEmbeddedLabel || (!readOnly && showUploadAction);

    return (
      <div
        className={`px-5 ${
          embeddedSeparator ? "mt-4 border-t border-gray-border pt-4" : "py-5"
        }`}
        data-file-dropzone="true"
        onDragOver={readOnly ? undefined : handleDragOver}
        onDrop={readOnly ? undefined : handleDrop}
      >
        {showEmbeddedHeader ? (
          <div className="mb-3 flex items-center justify-between">
            <span className="text-xs font-medium text-text-secondary">
              {showEmbeddedLabel ? embeddedLabel : null}
              {showEmbeddedLabel ? (
                <span className="ml-1.5 rounded-full bg-bg-cool px-2 py-0.5 text-xs text-text-secondary">
                  {items.length}
                </span>
              ) : null}
            </span>
            {!readOnly && showUploadAction ? (
              <Button
                variant="ghost"
                size="sm"
                type="button"
                onClick={openPicker}
                disabled={uploadMutation.isPending}
              >
                <Upload className="mr-1 h-3.5 w-3.5" />
                {uploadLabel}
              </Button>
            ) : null}
          </div>
        ) : null}
        {listErrorBanner}
        {fileList}
        {hiddenInput}
      </div>
    );
  }

  const header = (
    <button
      type="button"
      className="flex w-full items-center gap-2 rounded-lg border border-gray-border bg-white px-4 py-2.5 text-left text-sm hover:bg-bg-cool/50"
      onClick={() => setExpanded((value) => !value)}
    >
      {expanded ? (
        <ChevronDown className="h-4 w-4 text-text-muted" />
      ) : (
        <ChevronRight className="h-4 w-4 text-text-muted" />
      )}
      <Paperclip className="h-4 w-4 text-text-secondary" />
      <span className="font-medium text-text-dark">{title}</span>
      {items.length > 0 ? (
        <span className="rounded-full bg-bg-cool px-2 py-0.5 text-xs text-text-secondary">
          {items.length}
        </span>
      ) : null}
    </button>
  );

  if (compact && !expanded) {
    return <div className="mt-3">{header}</div>;
  }

  return (
    <div className="mt-3">
      {compact ? header : null}

      <div
        className={`${compact ? "mt-1 " : ""}rounded-lg border border-gray-border bg-white`}
        data-file-dropzone="true"
        onDragOver={readOnly ? undefined : handleDragOver}
        onDrop={readOnly ? undefined : handleDrop}
      >
        {!compact ? (
          <div className="flex items-center justify-between border-b border-gray-border px-4 py-2.5">
            <div className="flex items-center gap-2">
              <Paperclip className="h-4 w-4 text-text-secondary" />
              <span className="text-sm font-medium text-text-dark">
                {title}
              </span>
              {items.length > 0 ? (
                <span className="rounded-full bg-bg-cool px-2 py-0.5 text-xs text-text-secondary">
                  {items.length}
                </span>
              ) : null}
            </div>
            {!readOnly && showUploadAction ? (
              <Button
                variant="ghost"
                size="sm"
                type="button"
                onClick={openPicker}
                disabled={uploadMutation.isPending}
              >
                <Upload className="mr-1 h-3.5 w-3.5" />
                {uploadLabel}
              </Button>
            ) : null}
          </div>
        ) : null}

        {compact && !readOnly && showUploadAction ? (
          <div className="flex justify-end border-b border-gray-border px-4 py-2">
            <Button
              variant="ghost"
              size="sm"
              type="button"
              onClick={openPicker}
              disabled={uploadMutation.isPending}
            >
              <Upload className="mr-1 h-3.5 w-3.5" />
              {uploadLabel}
            </Button>
          </div>
        ) : null}

        {listErrorBanner}
        {fileList}
      </div>

      {hiddenInput}
    </div>
  );
}
