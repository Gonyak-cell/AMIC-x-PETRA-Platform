import { useState, useEffect, useId } from "react";
import { Plus } from "lucide-react";
import { Button, Input, Select } from "@/components/ui";
import type { DocumentType } from "@/modules/ma/types/document_version";
import { useCreateDocument } from "@/modules/ma/hooks/useDocumentVersions";

const DOC_TYPE_OPTIONS: { value: DocumentType; label: string }[] = [
  { value: "CONTRACT_SPA", label: "SPA (주식매매계약)" },
  { value: "CONTRACT_AMENDMENT", label: "계약 수정 (Amendment)" },
  { value: "CONTRACT_SIDE_LETTER", label: "Side Letter" },
  { value: "CONTRACT_SHA", label: "주주간계약 (SHA)" },
  { value: "CONTRACT_ESCROW", label: "에스크로 계약" },
  { value: "CONTRACT_BTA", label: "영업양수도계약 (BTA)" },
  { value: "CONTRACT_SSA", label: "주식인수계약 (SSA)" },
  { value: "CONTRACT_OTHER", label: "기타 계약" },
  { value: "NDA", label: "NDA" },
  { value: "RFI_EXCEL", label: "RFI 엑셀" },
  { value: "MEETING_MINUTES", label: "회의록" },
  { value: "DD_REPORT", label: "DD 보고서" },
  { value: "OTHER", label: "기타" },
];

interface DocumentCreateDialogProps {
  open: boolean;
  onClose: () => void;
  txnId: string;
}

export default function DocumentCreateDialog({
  open,
  onClose,
  txnId,
}: DocumentCreateDialogProps) {
  const createDocument = useCreateDocument(txnId);
  const [docType, setDocType] = useState<DocumentType>("CONTRACT_SPA");
  const [docName, setDocName] = useState("");
  const [description, setDescription] = useState("");
  const titleId = useId();
  const descId = useId();

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
    if (!docName.trim()) return;
    createDocument.mutate(
      {
        doc_type: docType,
        doc_name: docName.trim(),
        description: description.trim() || null,
      },
      {
        onSuccess: () => {
          onClose();
        },
      },
    );
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
          새 문서 원장 생성
        </h3>

        <div className="space-y-4">
          <Select
            label="문서 유형"
            options={DOC_TYPE_OPTIONS.map((o) => ({
              value: o.value,
              label: o.label,
            }))}
            value={docType}
            onChange={(e) => setDocType(e.target.value as DocumentType)}
          />

          <Input
            label="문서 이름"
            value={docName}
            onChange={(e) => setDocName(e.target.value)}
            placeholder="예: OO기업 SPA 최종본"
          />

          <div>
            <label
              htmlFor={descId}
              className="block text-sm font-medium text-text-secondary mb-1"
            >
              설명 (선택)
            </label>
            <textarea
              id={descId}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="문서에 대한 간략한 설명"
              rows={3}
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
            />
          </div>
        </div>

        <div className="flex justify-end gap-3 mt-6">
          <Button
            variant="ghost"
            onClick={onClose}
            disabled={createDocument.isPending}
          >
            취소
          </Button>
          <Button
            icon={Plus}
            onClick={handleSubmit}
            disabled={!docName.trim() || createDocument.isPending}
            loading={createDocument.isPending}
          >
            생성
          </Button>
        </div>
      </div>
    </div>
  );
}
