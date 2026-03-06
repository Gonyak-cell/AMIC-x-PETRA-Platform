import { Upload } from "lucide-react";
import { useCallback, useRef, useState } from "react";
import { toast } from "sonner";

import { Spinner } from "@/components/ui/Spinner";
import { useDirectUpload } from "@/modules/ma/hooks/useVdr";
import type { DirectUploadBatchResult } from "@/modules/ma/types/vdr";
import { VDR_CONSTRAINTS } from "@/modules/ma/types/vdr";

interface DirectUploadZoneProps {
  txnId: string;
  onUploadComplete: (result: DirectUploadBatchResult) => void;
  disabled?: boolean;
}

function validateFiles(files: File[]): { valid: File[]; errors: string[] } {
  const valid: File[] = [];
  const errors: string[] = [];

  for (const file of files) {
    if (file.size > VDR_CONSTRAINTS.MAX_FILE_SIZE) {
      errors.push(`${file.name}: ${VDR_CONSTRAINTS.MAX_FILE_SIZE_LABEL} 초과`);
      continue;
    }
    if (file.type && !VDR_CONSTRAINTS.ALLOWED_MIME_TYPES.has(file.type)) {
      errors.push(`${file.name}: 허용되지 않는 파일 형식 (${file.type})`);
      continue;
    }
    valid.push(file);
  }

  return { valid, errors };
}

export default function DirectUploadZone({
  txnId,
  onUploadComplete,
  disabled = false,
}: DirectUploadZoneProps) {
  const [isDragOver, setIsDragOver] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const directUpload = useDirectUpload(txnId);

  const handleFiles = useCallback(
    async (fileList: FileList | File[]) => {
      const files = Array.from(fileList);
      if (files.length === 0) return;

      if (directUpload.isPending) return;

      const { valid, errors } = validateFiles(files);
      if (errors.length > 0) {
        toast.warning(errors.join("\n"));
      }
      if (valid.length === 0) return;

      directUpload.mutate(valid, {
        onSuccess: (result) => {
          onUploadComplete(result);
        },
      });
    },
    [directUpload, onUploadComplete],
  );

  const handleDragOver = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      e.stopPropagation();
      if (!disabled) setIsDragOver(true);
    },
    [disabled],
  );

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(false);
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      e.stopPropagation();
      setIsDragOver(false);
      if (!disabled && e.dataTransfer.files.length > 0) {
        handleFiles(e.dataTransfer.files);
      }
    },
    [disabled, handleFiles],
  );

  const handleClick = useCallback(() => {
    if (!disabled) fileInputRef.current?.click();
  }, [disabled]);

  const handleInputChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      if (e.target.files && e.target.files.length > 0) {
        handleFiles(e.target.files);
      }
      // 동일 파일 재선택 허용
      e.target.value = "";
    },
    [handleFiles],
  );

  const isUploading = directUpload.isPending;

  return (
    <div
      className={`
        flex flex-col items-center justify-center gap-3 p-8 rounded-lg border-2 border-dashed
        transition-colors cursor-pointer select-none
        ${isDragOver ? "border-accent bg-accent/5" : "border-gray-300 bg-slate-50 hover:border-slate-400"}
        ${disabled || isUploading ? "opacity-50 cursor-not-allowed" : ""}
      `}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
      onClick={handleClick}
      role="button"
      tabIndex={0}
      aria-label="파일 드래그 앤 드롭 또는 클릭하여 업로드"
      aria-disabled={disabled || isUploading}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          handleClick();
        }
      }}
    >
      <input
        ref={fileInputRef}
        type="file"
        multiple
        accept={VDR_CONSTRAINTS.ACCEPT_EXTENSIONS}
        className="hidden"
        onChange={handleInputChange}
      />

      {isUploading ? (
        <>
          <Spinner size="md" />
          <p className="text-sm text-slate-600">파일 업로드 및 분류 중...</p>
        </>
      ) : (
        <>
          <Upload className="h-8 w-8 text-slate-400" />
          <div className="text-center">
            <p className="text-sm font-medium text-slate-600">
              파일을 끌어다 놓으세요
            </p>
            <p className="text-xs text-slate-400 mt-1">
              AI가 자동으로 분류합니다 · 최대{" "}
              {VDR_CONSTRAINTS.MAX_FILE_SIZE_LABEL} / 파일
            </p>
          </div>
        </>
      )}
    </div>
  );
}
