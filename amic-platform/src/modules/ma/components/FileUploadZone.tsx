import {
  ChevronDown,
  ChevronRight,
  Download,
  FileText,
  Paperclip,
  Trash2,
  Upload,
} from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";

import { Button } from "@/components/ui/Button";
import {
  getAttachmentDownloadUrl,
  useAttachments,
  useDeleteAttachment,
  useUploadAttachment,
} from "@/modules/ma/hooks/useAttachments";
import type {
  Attachment,
  AttachmentEntityType,
} from "@/modules/ma/types/attachment";
import {
  ATTACHMENT_CONSTRAINTS,
  ATTACHMENT_MIME_LABELS,
} from "@/modules/ma/types/attachment";
import { formatFileSize, formatISODate } from "@/modules/ma/utils/format";
import {
  openAttachmentFilePicker,
  uploadAttachmentFiles,
} from "@/modules/ma/components/attachmentUploadUtils";

interface FileUploadZoneProps {
  txnId: string;
  entityType: AttachmentEntityType;
  entityId?: string;
  compact?: boolean;
  embedded?: boolean;
  readOnly?: boolean;
  title?: string;
  embeddedLabel?: string;
  uploadLabel?: string;
  emptyDescription?: string;
  emptyHint?: string;
  embeddedSeparator?: boolean;
  showUploadAction?: boolean;
  registerOpenPicker?: (openPicker: (() => void) | null) => void;
  onUploaded?: (attachment: Attachment, file: File) => Promise<void> | void;
}

export default function FileUploadZone({
  txnId,
  entityType,
  entityId,
  compact = false,
  embedded = false,
  readOnly = false,
  title = "첨부 자료",
  embeddedLabel = "첨부 파일",
  uploadLabel = "업로드",
  emptyDescription = "파일을 여기에 드래그하거나 업로드 버튼을 클릭하세요.",
  emptyHint = `최대 ${ATTACHMENT_CONSTRAINTS.MAX_FILE_SIZE_LABEL} · PDF, DOCX, XLSX, PPTX, HWP 등`,
  embeddedSeparator = true,
  showUploadAction = true,
  registerOpenPicker,
  onUploaded,
}: FileUploadZoneProps) {
  const [expanded, setExpanded] = useState(!compact);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const { data } = useAttachments(txnId, entityType, entityId);
  const uploadMutation = useUploadAttachment(txnId);
  const deleteMutation = useDeleteAttachment(txnId);

  const items = data?.items ?? [];

  const handleUpload = useCallback(
    async (files: File[]) => {
      await uploadAttachmentFiles({
        files,
        entityType,
        entityId,
        uploadMutation,
        onUploaded,
      });
    },
    [entityId, entityType, onUploaded, uploadMutation],
  );

  const handleDrop = useCallback(
    (event: React.DragEvent) => {
      event.preventDefault();
      void handleUpload(Array.from(event.dataTransfer.files));
    },
    [handleUpload],
  );

  const handleFileSelect = useCallback(
    (event: React.ChangeEvent<HTMLInputElement>) => {
      void handleUpload(Array.from(event.target.files ?? []));
      event.target.value = "";
    },
    [handleUpload],
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

  const fileList = (
    <>
      {items.length === 0 ? (
        <div
          className={`flex flex-col items-center justify-center gap-2 py-8 text-sm text-text-muted ${
            readOnly ? "" : "cursor-pointer"
          }`}
          onDragOver={(event) => event.preventDefault()}
          onDrop={readOnly ? undefined : handleDrop}
          onClick={readOnly ? undefined : openPicker}
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
          <Upload className="h-8 w-8 text-text-muted" />
          <p>{emptyDescription}</p>
          <p className="text-xs">{emptyHint}</p>
        </div>
      ) : (
        <table className="w-full text-sm">
          <thead className="border-b border-gray-border text-left text-xs text-text-secondary">
            <tr>
              <th className="px-5 py-2 font-medium">파일명</th>
              <th className="px-5 py-2 font-medium">형식</th>
              <th className="px-5 py-2 font-medium">크기</th>
              <th className="px-5 py-2 font-medium">업로드일</th>
              <th className="px-5 py-2 font-medium" />
            </tr>
          </thead>
          <tbody>
            {items.map((attachment) => (
              <tr
                key={attachment.id}
                className="border-b border-gray-border/50 hover:bg-bg-cool/50"
              >
                <td className="px-5 py-2">
                  <div className="flex items-center gap-2">
                    <FileText className="h-4 w-4 shrink-0 text-text-muted" />
                    <span className="truncate" title={attachment.file_name}>
                      {attachment.file_name}
                    </span>
                  </div>
                </td>
                <td className="px-5 py-2 text-text-secondary">
                  {ATTACHMENT_MIME_LABELS[attachment.mime_type] ??
                    attachment.mime_type.split("/")[1]}
                </td>
                <td className="px-5 py-2 text-text-secondary">
                  {formatFileSize(attachment.file_size_bytes)}
                </td>
                <td className="px-5 py-2 text-text-secondary">
                  {formatISODate(attachment.created_at)}
                </td>
                <td className="px-5 py-2">
                  <div className="flex items-center gap-1">
                    <a
                      href={getAttachmentDownloadUrl(txnId, attachment.id)}
                      className="rounded p-1 text-text-muted hover:bg-bg-cool hover:text-info"
                      title="다운로드"
                    >
                      <Download className="h-4 w-4" />
                    </a>
                    {!readOnly && (
                      <button
                        type="button"
                        className="rounded p-1 text-text-muted hover:bg-bg-cool hover:text-negative"
                        title="삭제"
                        onClick={() => deleteMutation.mutate(attachment.id)}
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    )}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </>
  );

  if (embedded) {
    const showEmbeddedLabel =
      embeddedLabel.trim().length > 0 && items.length > 0;
    const showEmbeddedHeader = showEmbeddedLabel || (!readOnly && showUploadAction);

    return (
      <div
        className={`px-5 ${
          embeddedSeparator ? "mt-4 border-t border-gray-border pt-4" : "py-5"
        }`}
        onDragOver={(event) => event.preventDefault()}
        onDrop={readOnly ? undefined : handleDrop}
      >
        {showEmbeddedHeader && (
          <div className="mb-3 flex items-center justify-between">
            <span className="text-xs font-medium text-text-secondary">
              {showEmbeddedLabel ? embeddedLabel : null}
              {showEmbeddedLabel && (
                <span className="ml-1.5 rounded-full bg-bg-cool px-2 py-0.5 text-xs text-text-secondary">
                  {items.length}
                </span>
              )}
            </span>
            {!readOnly && showUploadAction && (
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
            )}
          </div>
        )}
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
      {items.length > 0 && (
        <span className="rounded-full bg-bg-cool px-2 py-0.5 text-xs text-text-secondary">
          {items.length}
        </span>
      )}
    </button>
  );

  if (compact && !expanded) {
    return <div className="mt-3">{header}</div>;
  }

  return (
    <div className="mt-3">
      {compact && header}

      <div
        className={`${compact ? "mt-1 " : ""}rounded-lg border border-gray-border bg-white`}
        onDragOver={(event) => event.preventDefault()}
        onDrop={readOnly ? undefined : handleDrop}
      >
        {!compact && (
          <div className="flex items-center justify-between border-b border-gray-border px-4 py-2.5">
            <div className="flex items-center gap-2">
              <Paperclip className="h-4 w-4 text-text-secondary" />
              <span className="text-sm font-medium text-text-dark">
                {title}
              </span>
              {items.length > 0 && (
                <span className="rounded-full bg-bg-cool px-2 py-0.5 text-xs text-text-secondary">
                  {items.length}
                </span>
              )}
            </div>
            {!readOnly && showUploadAction && (
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
            )}
          </div>
        )}

        {compact && !readOnly && showUploadAction && (
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
        )}

        {fileList}
      </div>

      {hiddenInput}
    </div>
  );
}
