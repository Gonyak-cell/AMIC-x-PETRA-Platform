import { useCallback, useRef, useState } from "react";
import { Download, FileText, RefreshCw, Upload, X } from "lucide-react";

import { Button } from "@/components/ui";
import type { PhaseMilestone } from "@/modules/ma/constants";
import {
  getAttachmentDownloadUrl,
  useAttachments,
  useDeleteAttachment,
  useUploadAttachment,
} from "@/modules/ma/hooks/useAttachments";

interface MilestoneUploadPopoverProps {
  txnId: string;
  milestone: PhaseMilestone;
  onClose: () => void;
}

export default function MilestoneUploadPopover({
  txnId,
  milestone,
  onClose,
}: MilestoneUploadPopoverProps) {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [dragOver, setDragOver] = useState(false);

  const { data: attachments } = useAttachments(
    txnId,
    "MILESTONE",
    milestone.milestoneKey,
  );
  const upload = useUploadAttachment(txnId);
  const del = useDeleteAttachment(txnId);

  const existingFile = attachments?.items?.[0];

  const handleFile = useCallback(
    (file: File) => {
      if (!file.name.toLowerCase().endsWith(".pdf")) {
        return;
      }
      upload.mutate({
        file,
        entityType: "MILESTONE",
        entityId: milestone.milestoneKey,
        description: milestone.documentLabel,
      });
    },
    [upload, milestone],
  );

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragOver(false);
      const file = e.dataTransfer.files[0];
      if (file) handleFile(file);
    },
    [handleFile],
  );

  const handleReplace = useCallback(() => {
    if (existingFile) {
      del.mutate(existingFile.id, {
        onSuccess: () => fileInputRef.current?.click(),
      });
    }
  }, [existingFile, del]);

  return (
    <div className="absolute top-full left-1/2 -translate-x-1/2 mt-2 z-50">
      <div className="bg-white rounded-xl border border-gray-border shadow-lg p-4 w-72">
        {/* Header */}
        <div className="flex items-center justify-between mb-3">
          <h4 className="text-sm font-heading font-semibold text-text-dark">
            {milestone.documentLabel}
          </h4>
          <button
            type="button"
            onClick={onClose}
            className="p-0.5 hover:bg-gray-100 rounded"
          >
            <X size={14} className="text-text-muted" />
          </button>
        </div>

        {existingFile ? (
          /* ── 업로드된 파일 표시 ─────────────── */
          <div className="space-y-2">
            <div className="flex items-center gap-2 p-2 bg-bg-cool rounded-lg">
              <FileText size={16} className="text-accent shrink-0" />
              <div className="min-w-0 flex-1">
                <p className="text-xs font-medium text-text-dark truncate">
                  {existingFile.file_name}
                </p>
                <p className="text-[10px] text-text-muted">
                  {(existingFile.file_size_bytes / 1024).toFixed(0)} KB
                </p>
              </div>
            </div>
            <div className="flex gap-2">
              <a
                href={getAttachmentDownloadUrl(txnId, existingFile.id)}
                target="_blank"
                rel="noopener noreferrer"
                className="flex-1"
              >
                <Button variant="secondary" icon={Download} className="w-full">
                  다운로드
                </Button>
              </a>
              <Button
                variant="ghost"
                icon={RefreshCw}
                onClick={handleReplace}
                loading={del.isPending}
              >
                교체
              </Button>
            </div>
          </div>
        ) : (
          /* ── 업로드 영역 ───────────────────── */
          <div
            className={`border-2 border-dashed rounded-lg p-6 text-center transition-colors ${
              dragOver
                ? "border-accent bg-accent/5"
                : "border-gray-border hover:border-accent/40"
            }`}
            onDragOver={(e) => {
              e.preventDefault();
              setDragOver(true);
            }}
            onDragLeave={() => setDragOver(false)}
            onDrop={handleDrop}
          >
            <Upload size={24} className="mx-auto mb-2 text-text-muted" />
            <p className="text-xs text-text-secondary mb-1">
              PDF 파일을 드래그하거나
            </p>
            <Button
              variant="secondary"
              size="sm"
              onClick={() => fileInputRef.current?.click()}
              loading={upload.isPending}
            >
              파일 선택
            </Button>
            <input
              ref={fileInputRef}
              type="file"
              accept=".pdf"
              className="hidden"
              onChange={(e) => {
                const file = e.target.files?.[0];
                if (file) handleFile(file);
                e.target.value = "";
              }}
            />
          </div>
        )}
      </div>
    </div>
  );
}
