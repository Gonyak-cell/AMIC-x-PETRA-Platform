import { useState, useRef, useId, useEffect } from "react";
import { Upload } from "lucide-react";
import { Button, Input } from "@/components/ui";
import { useUploadRevision } from "@/modules/ma/hooks/useDocumentVersions";

interface RevisionUploadDialogProps {
  open: boolean;
  onClose: () => void;
  txnId: string;
  docId: string;
}

export default function RevisionUploadDialog({
  open,
  onClose,
  txnId,
  docId,
}: RevisionUploadDialogProps) {
  const uploadRevision = useUploadRevision(txnId, docId);
  const fileRef = useRef<HTMLInputElement>(null);
  const fileInputId = useId();
  const titleId = useId();
  const [changesSummary, setChangesSummary] = useState("");

  useEffect(() => {
    if (!open) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [open, onClose]);

  if (!open) return null;

  const handleSubmit = () => {
    const file = fileRef.current?.files?.[0];
    if (!file) return;

    const fd = new FormData();
    fd.append("file", file);
    if (changesSummary.trim()) {
      fd.append("changes_summary", changesSummary.trim());
    }

    uploadRevision.mutate(fd, {
      onSuccess: () => {
        onClose();
      },
    });
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        className="bg-white rounded-lg shadow-xl w-full max-w-md p-6"
      >
        <h3
          id={titleId}
          className="text-lg font-semibold text-text-dark mb-4"
        >
          새 버전 업로드
        </h3>

        <div className="space-y-4">
          <div>
            <label
              htmlFor={fileInputId}
              className="block text-sm font-medium text-text-secondary mb-1"
            >
              파일 (최대 50MB)
            </label>
            <input
              id={fileInputId}
              ref={fileRef}
              type="file"
              accept=".docx,.doc,.pdf,.xlsx,.xls,.pptx,.ppt,.hwp,.hwpx,.txt,.csv"
              className="w-full text-sm"
            />
          </div>

          <Input
            label="변경 요약"
            value={changesSummary}
            onChange={(e) => setChangesSummary(e.target.value)}
            placeholder="주요 변경 사항을 간략히 기재"
          />
        </div>

        <div className="flex justify-end gap-3 mt-6">
          <Button
            variant="ghost"
            onClick={onClose}
            disabled={uploadRevision.isPending}
          >
            취소
          </Button>
          <Button
            icon={Upload}
            onClick={handleSubmit}
            disabled={uploadRevision.isPending}
            loading={uploadRevision.isPending}
          >
            업로드
          </Button>
        </div>
      </div>
    </div>
  );
}
