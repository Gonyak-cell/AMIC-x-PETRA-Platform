import { useCallback, useEffect, useRef } from "react";
import { Download, FileText, RefreshCw, Upload, X } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui";
import type { UploadableMilestone } from "@/modules/ma/constants";
import type { Attachment } from "@/modules/ma/types/attachment";
import { ATTACHMENT_CONSTRAINTS } from "@/modules/ma/types/attachment";
import {
  getAttachmentDownloadUrl,
  useDeleteAttachment,
  useUploadAttachment,
} from "@/modules/ma/hooks/useAttachments";

interface MilestoneUploadPopoverProps {
  txnId: string;
  /** R7-1: UploadableMilestone으로 타입 narrowing */
  milestone: UploadableMilestone;
  /** 부모에서 전달받은 기존 첨부파일 (중복 API 호출 방지) */
  existingFile?: Attachment;
  onClose: () => void;
}

const MAX_SIZE_LABEL = ATTACHMENT_CONSTRAINTS.MAX_FILE_SIZE_LABEL;
const MAX_SIZE = ATTACHMENT_CONSTRAINTS.MAX_FILE_SIZE;

export default function MilestoneUploadPopover({
  txnId,
  milestone,
  existingFile,
  onClose,
}: MilestoneUploadPopoverProps) {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const popoverRef = useRef<HTMLDivElement>(null);

  const upload = useUploadAttachment(txnId);
  const deleteMutation = useDeleteAttachment(txnId);

  // R8-1: useRef 패턴으로 mutation 참조 안정화
  const uploadRef = useRef(upload);
  uploadRef.current = upload;
  const deleteRef = useRef(deleteMutation);
  deleteRef.current = deleteMutation;

  // R11-1: Escape 키 닫기 + R11-2: 외부 클릭 닫기 + M-13: 포커스 트랩
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        onClose();
        return;
      }
      // M-13: Tab 키 포커스 트랩 — 팝오버 내부에서 순환
      if (e.key === "Tab" && popoverRef.current) {
        const focusable = popoverRef.current.querySelectorAll<HTMLElement>(
          'button, [href], input:not([type="hidden"]):not(.hidden), [tabindex]:not([tabindex="-1"])',
        );
        if (focusable.length === 0) return;
        const first = focusable[0];
        const last = focusable[focusable.length - 1];
        if (e.shiftKey && document.activeElement === first) {
          e.preventDefault();
          last.focus();
        } else if (!e.shiftKey && document.activeElement === last) {
          e.preventDefault();
          first.focus();
        }
      }
    };
    const handleClickOutside = (e: MouseEvent) => {
      if (
        popoverRef.current &&
        !popoverRef.current.contains(e.target as Node)
      ) {
        onClose();
      }
    };
    document.addEventListener("keydown", handleKeyDown);
    document.addEventListener("mousedown", handleClickOutside);
    return () => {
      document.removeEventListener("keydown", handleKeyDown);
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, [onClose]);

  // R11-2: 팝오버 열림 시 포커스 이동
  useEffect(() => {
    const firstFocusable = popoverRef.current?.querySelector<HTMLElement>(
      'button, [href], input:not([type="hidden"]):not(.hidden), [tabindex]:not([tabindex="-1"])',
    );
    firstFocusable?.focus();
  }, []);

  const handleFile = useCallback(
    (file: File) => {
      if (!file.name.toLowerCase().endsWith(".pdf")) {
        toast.error("PDF 파일만 업로드할 수 있습니다.");
        return;
      }
      if (file.size > MAX_SIZE) {
        toast.error(`파일 크기가 ${MAX_SIZE_LABEL}를 초과합니다.`);
        return;
      }
      uploadRef.current.mutate({
        file,
        entityType: "MILESTONE",
        entityId: milestone.milestoneKey,
        description: milestone.documentLabel,
      });
    },
    [milestone.milestoneKey, milestone.documentLabel],
  );

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      const file = e.dataTransfer.files[0];
      if (file) handleFile(file);
    },
    [handleFile],
  );

  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      fileInputRef.current?.click();
    }
  }, []);

  /** 교체: 새 파일 업로드 후 기존 파일 삭제 (원자적 교체) */
  const handleReplace = useCallback(() => {
    fileInputRef.current?.click();
  }, []);

  // P-05: 교체 시 invalidation 1회로 통합
  const handleReplaceFile = useCallback(
    (file: File) => {
      if (!file.name.toLowerCase().endsWith(".pdf")) {
        toast.error("PDF 파일만 업로드할 수 있습니다.");
        return;
      }
      if (file.size > MAX_SIZE) {
        toast.error(`파일 크기가 ${MAX_SIZE_LABEL}를 초과합니다.`);
        return;
      }
      // 새 파일 업로드 성공 후 기존 파일 삭제 (문서 유실 방지)
      uploadRef.current.mutate(
        {
          file,
          entityType: "MILESTONE",
          entityId: milestone.milestoneKey,
          description: milestone.documentLabel,
        },
        {
          onSuccess: () => {
            if (existingFile) {
              // 삭제 실패해도 업로드는 성공 상태 유지
              deleteRef.current.mutate(existingFile.id, {
                onError: () => {
                  toast.warning(
                    "새 파일은 업로드되었지만, 이전 파일 정리에 실패했습니다.",
                  );
                },
              });
            }
          },
        },
      );
    },
    [milestone.milestoneKey, milestone.documentLabel, existingFile],
  );

  return (
    <div className="absolute top-full left-1/2 -translate-x-1/2 mt-2 z-50">
      <div
        ref={popoverRef}
        role="dialog"
        aria-label={`${milestone.documentLabel} 업로드`}
        className="bg-white rounded-xl border border-gray-border shadow-lg p-4 w-72"
      >
        {/* Header */}
        <div className="flex items-center justify-between mb-3">
          <h4 className="text-sm font-heading font-semibold text-text-dark">
            {milestone.documentLabel}
          </h4>
          <button
            type="button"
            onClick={onClose}
            aria-label="팝오버 닫기"
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
                loading={upload.isPending || deleteMutation.isPending}
              >
                교체
              </Button>
            </div>
            <input
              ref={fileInputRef}
              type="file"
              accept=".pdf"
              className="hidden"
              onChange={(e) => {
                const file = e.target.files?.[0];
                if (file) handleReplaceFile(file);
                e.target.value = "";
              }}
            />
          </div>
        ) : (
          /* ── 업로드 영역 ───────────────────── */
          <div
            role="button"
            tabIndex={0}
            aria-label={`${milestone.documentLabel} PDF 파일 업로드 영역. 파일을 드래그하거나 Enter 키를 눌러 선택하세요.`}
            className="border-2 border-dashed rounded-lg p-6 text-center transition-colors border-gray-border hover:border-accent/40"
            onDragOver={(e) => {
              e.preventDefault();
            }}
            onDrop={handleDrop}
            onKeyDown={handleKeyDown}
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
