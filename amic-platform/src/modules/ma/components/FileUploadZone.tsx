import {
  ChevronDown,
  ChevronRight,
  Download,
  FileText,
  Paperclip,
  Trash2,
  Upload,
} from "lucide-react";
import { useCallback, useRef, useState } from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/Button";
import type { AttachmentEntityType } from "@/modules/ma/types/attachment";
import {
  ATTACHMENT_CONSTRAINTS,
  ATTACHMENT_MIME_LABELS,
} from "@/modules/ma/types/attachment";
import {
  getAttachmentDownloadUrl,
  useAttachments,
  useDeleteAttachment,
  useUploadAttachment,
} from "@/modules/ma/hooks/useAttachments";

interface FileUploadZoneProps {
  txnId: string;
  entityType: AttachmentEntityType;
  entityId?: string;
  /** 접이식 모드 (기본 닫힘) */
  compact?: boolean;
  /** Card 내부 임베드 모드 (래퍼 없이 flat 렌더링) */
  embedded?: boolean;
  /** 읽기 전용 */
  readOnly?: boolean;
  /** 커스텀 제목 */
  title?: string;
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("ko-KR", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  });
}

function validateFile(file: File): string | null {
  if (file.size > ATTACHMENT_CONSTRAINTS.MAX_FILE_SIZE) {
    return `파일 크기(${formatFileSize(file.size)})가 최대 허용량(${ATTACHMENT_CONSTRAINTS.MAX_FILE_SIZE_LABEL})을 초과합니다.`;
  }
  const ext = "." + (file.name.split(".").pop()?.toLowerCase() ?? "");
  if (!ATTACHMENT_CONSTRAINTS.ALLOWED_EXTENSIONS.has(ext)) {
    return `허용되지 않는 파일 형식입니다: ${ext}`;
  }
  return null;
}

export default function FileUploadZone({
  txnId,
  entityType,
  entityId,
  compact = false,
  embedded = false,
  readOnly = false,
  title = "외부 자료",
}: FileUploadZoneProps) {
  const [expanded, setExpanded] = useState(!compact);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const { data } = useAttachments(txnId, entityType, entityId);
  const uploadMutation = useUploadAttachment(txnId);
  const deleteMutation = useDeleteAttachment(txnId);

  const items = data?.items ?? [];

  const handleUpload = useCallback(
    (file: File) => {
      const error = validateFile(file);
      if (error) {
        toast.error(error);
        return;
      }
      uploadMutation.mutate({ file, entityType, entityId });
    },
    [uploadMutation, entityType, entityId],
  );

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      for (const file of Array.from(e.dataTransfer.files)) {
        handleUpload(file);
      }
    },
    [handleUpload],
  );

  const handleFileSelect = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      for (const file of Array.from(e.target.files ?? [])) {
        handleUpload(file);
      }
      e.target.value = "";
    },
    [handleUpload],
  );

  // ── 파일 목록 (공유) ──────────────────────────────────
  const fileList = (
    <>
      {items.length === 0 ? (
        <div
          className="flex flex-col items-center justify-center gap-2 py-8 text-sm text-slate-400"
          onDragOver={(e) => e.preventDefault()}
          onDrop={readOnly ? undefined : handleDrop}
        >
          <Upload className="h-8 w-8 text-slate-300" />
          <p>파일을 여기에 드래그하거나 업로드 버튼을 클릭하세요</p>
          <p className="text-xs">
            최대 {ATTACHMENT_CONSTRAINTS.MAX_FILE_SIZE_LABEL} · PDF, DOCX, XLSX,
            PPTX, HWP 등
          </p>
        </div>
      ) : (
        <table className="w-full text-sm">
          <thead className="border-b border-slate-100 text-left text-xs text-slate-500">
            <tr>
              <th className="px-4 py-2 font-medium">파일명</th>
              <th className="px-4 py-2 font-medium">형식</th>
              <th className="px-4 py-2 font-medium">크기</th>
              <th className="px-4 py-2 font-medium">업로드일</th>
              <th className="px-4 py-2 font-medium" />
            </tr>
          </thead>
          <tbody>
            {items.map((att) => (
              <tr
                key={att.id}
                className="border-b border-slate-50 hover:bg-slate-50"
              >
                <td className="px-4 py-2">
                  <div className="flex items-center gap-2">
                    <FileText className="h-4 w-4 shrink-0 text-slate-400" />
                    <span className="truncate" title={att.file_name}>
                      {att.file_name}
                    </span>
                  </div>
                </td>
                <td className="px-4 py-2 text-slate-500">
                  {ATTACHMENT_MIME_LABELS[att.mime_type] ??
                    att.mime_type.split("/")[1]}
                </td>
                <td className="px-4 py-2 text-slate-500">
                  {formatFileSize(att.file_size_bytes)}
                </td>
                <td className="px-4 py-2 text-slate-500">
                  {formatDate(att.created_at)}
                </td>
                <td className="px-4 py-2">
                  <div className="flex items-center gap-1">
                    <a
                      href={getAttachmentDownloadUrl(txnId, att.id)}
                      className="rounded p-1 text-slate-400 hover:bg-slate-100 hover:text-info"
                      title="다운로드"
                    >
                      <Download className="h-4 w-4" />
                    </a>
                    {!readOnly && (
                      <button
                        type="button"
                        className="rounded p-1 text-slate-400 hover:bg-slate-100 hover:text-negative"
                        title="삭제"
                        onClick={() => deleteMutation.mutate(att.id)}
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

  // ── 숨김 파일 input ────────────────────────────────────
  const hiddenInput = !readOnly && (
    <input
      ref={fileInputRef}
      type="file"
      className="hidden"
      multiple
      accept={ATTACHMENT_CONSTRAINTS.ACCEPT_EXTENSIONS}
      onChange={handleFileSelect}
    />
  );

  // ── embedded 모드: Card 내부에 flat 렌더링 ─────────────
  if (embedded) {
    return (
      <div
        className="mt-4 border-t border-slate-100 pt-4"
        onDragOver={(e) => e.preventDefault()}
        onDrop={readOnly ? undefined : handleDrop}
      >
        <div className="flex items-center justify-between mb-3 px-1">
          <span className="text-xs font-medium text-slate-500">
            첨부 파일
            {items.length > 0 && (
              <span className="ml-1.5 rounded-full bg-slate-100 px-2 py-0.5 text-xs text-slate-500">
                {items.length}
              </span>
            )}
          </span>
          {!readOnly && (
            <Button
              variant="ghost"
              size="sm"
              onClick={() => fileInputRef.current?.click()}
              disabled={uploadMutation.isPending}
            >
              <Upload className="mr-1 h-3.5 w-3.5" />
              업로드
            </Button>
          )}
        </div>
        {fileList}
        {hiddenInput}
      </div>
    );
  }

  // ── 접이식 헤더 ──────────────────────────────────────
  const header = (
    <button
      type="button"
      className="flex w-full items-center gap-2 rounded-lg border border-slate-200 bg-white px-4 py-2.5 text-left text-sm hover:bg-slate-50"
      onClick={() => setExpanded((v) => !v)}
    >
      {expanded ? (
        <ChevronDown className="h-4 w-4 text-slate-400" />
      ) : (
        <ChevronRight className="h-4 w-4 text-slate-400" />
      )}
      <Paperclip className="h-4 w-4 text-slate-500" />
      <span className="font-medium text-slate-700">{title}</span>
      {items.length > 0 && (
        <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs text-slate-500">
          {items.length}
        </span>
      )}
    </button>
  );

  if (compact && !expanded) {
    return <div className="mt-3">{header}</div>;
  }

  // ── 본문 (compact / 기본 모드) ─────────────────────────
  return (
    <div className="mt-3">
      {compact && header}

      <div
        className={`${compact ? "mt-1 " : ""}rounded-lg border border-slate-200 bg-white`}
        onDragOver={(e) => e.preventDefault()}
        onDrop={readOnly ? undefined : handleDrop}
      >
        {/* 헤더 바 (비접이식 모드) */}
        {!compact && (
          <div className="flex items-center justify-between border-b border-slate-100 px-4 py-2.5">
            <div className="flex items-center gap-2">
              <Paperclip className="h-4 w-4 text-slate-500" />
              <span className="text-sm font-medium text-slate-700">
                {title}
              </span>
              {items.length > 0 && (
                <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs text-slate-500">
                  {items.length}
                </span>
              )}
            </div>
            {!readOnly && (
              <Button
                variant="ghost"
                size="sm"
                onClick={() => fileInputRef.current?.click()}
                disabled={uploadMutation.isPending}
              >
                <Upload className="mr-1 h-3.5 w-3.5" />
                업로드
              </Button>
            )}
          </div>
        )}

        {/* 업로드 버튼 (접이식 모드) */}
        {compact && !readOnly && (
          <div className="flex justify-end border-b border-slate-100 px-4 py-2">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => fileInputRef.current?.click()}
              disabled={uploadMutation.isPending}
            >
              <Upload className="mr-1 h-3.5 w-3.5" />
              업로드
            </Button>
          </div>
        )}

        {/* 파일 목록 또는 빈 상태 */}
        {fileList}
      </div>

      {/* 숨김 파일 input */}
      {hiddenInput}
    </div>
  );
}
