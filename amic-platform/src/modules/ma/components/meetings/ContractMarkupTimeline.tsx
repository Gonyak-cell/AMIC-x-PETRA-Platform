import { useState, useRef } from "react";
import { Upload, Download, Trash2, FileText, Clock } from "lucide-react";
import { Badge, Button, Card, EmptyState, Input } from "@/components/ui";
import type { ContractMarkup } from "@/modules/ma/types/contract_markup";
import { getMarkupDownloadUrl } from "@/modules/ma/hooks/useContractMarkups";
import { formatFileSize } from "@/modules/ma/utils/format";

interface ContractMarkupTimelineProps {
  txnId: string;
  contractId: string;
  markups: ContractMarkup[];
  canWrite: boolean;
  onUpload: (formData: FormData) => void;
  onDelete: (markupId: string) => void;
  isUploading?: boolean;
}

export default function ContractMarkupTimeline({
  txnId,
  contractId,
  markups,
  canWrite,
  onUpload,
  onDelete,
  isUploading,
}: ContractMarkupTimelineProps) {
  const fileRef = useRef<HTMLInputElement>(null);
  const [versionLabel, setVersionLabel] = useState("");
  const [sourceParty, setSourceParty] = useState("");

  const handleFileUpload = () => {
    const file = fileRef.current?.files?.[0];
    if (!file) return;
    const fd = new FormData();
    fd.append("file", file);
    fd.append("version_label", versionLabel.trim() || `v${markups.length + 1}`);
    if (sourceParty.trim()) fd.append("source_party", sourceParty.trim());
    onUpload(fd);
    setVersionLabel("");
    setSourceParty("");
    if (fileRef.current) fileRef.current.value = "";
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-heading font-semibold text-text-dark flex items-center gap-2">
          <FileText className="h-4 w-4" /> 마크업 버전 ({markups.length})
        </h3>
      </div>

      {markups.length === 0 && (
        <EmptyState
          title="마크업 버전이 없습니다"
          description="계약 파일을 업로드하여 버전 관리를 시작하세요."
        />
      )}

      {/* 타임라인 */}
      <div className="relative">
        {markups.length > 1 && (
          <div className="absolute left-4 top-6 bottom-6 w-0.5 bg-gray-200" />
        )}
        <div className="space-y-3">
          {markups.map((markup) => (
            <div
              key={markup.id}
              className="relative flex items-start gap-3 pl-2"
            >
              <div className="relative z-10 flex h-8 w-8 shrink-0 items-center justify-center rounded-full border-2 border-primary-300 bg-white text-xs font-semibold text-primary-600">
                {markup.version_number}
              </div>
              <Card className="flex-1 p-3">
                <div className="flex items-center justify-between">
                  <div>
                    <span className="text-sm font-semibold text-text-dark">
                      {markup.version_label}
                    </span>
                    {markup.source_party && (
                      <Badge variant="neutral" className="ml-2">
                        {markup.source_party}
                      </Badge>
                    )}
                  </div>
                  <div className="flex items-center gap-1.5">
                    {markup.file_name && (
                      <a
                        href={getMarkupDownloadUrl(
                          txnId,
                          contractId,
                          markup.id,
                        )}
                        className="text-primary-600 hover:text-primary-700"
                        title="다운로드"
                      >
                        <Download className="h-4 w-4" />
                      </a>
                    )}
                    {canWrite && (
                      <button
                        type="button"
                        className="text-red-400 hover:text-red-600"
                        onClick={() => onDelete(markup.id)}
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    )}
                  </div>
                </div>
                <div className="flex items-center gap-3 mt-1 text-xs text-text-muted">
                  {markup.file_name && <span>{markup.file_name}</span>}
                  {markup.file_size_bytes && (
                    <span>{formatFileSize(markup.file_size_bytes)}</span>
                  )}
                  <span className="flex items-center gap-0.5">
                    <Clock className="h-3 w-3" />
                    {new Date(markup.created_at).toLocaleDateString("ko-KR")}
                  </span>
                </div>
                {markup.changes_summary && (
                  <p className="text-xs text-text-secondary mt-1.5">
                    {markup.changes_summary}
                  </p>
                )}
                {markup.key_changes && markup.key_changes.length > 0 && (
                  <div className="flex flex-wrap gap-1 mt-1.5">
                    {markup.key_changes.map((kc, i) => (
                      <Badge key={i} variant="neutral">
                        {kc}
                      </Badge>
                    ))}
                  </div>
                )}
              </Card>
            </div>
          ))}
        </div>
      </div>

      {/* 업로드 */}
      {canWrite && (
        <Card className="p-4 border-dashed">
          <p className="text-sm font-medium text-text-dark mb-3">
            새 버전 업로드
          </p>
          <div className="flex flex-wrap items-end gap-3">
            <div className="flex-1 min-w-[160px]">
              <Input
                label="버전 라벨"
                value={versionLabel}
                onChange={(e) => setVersionLabel(e.target.value)}
                placeholder={`v${markups.length + 1}`}
              />
            </div>
            <div className="flex-1 min-w-[160px]">
              <Input
                label="작성 측"
                value={sourceParty}
                onChange={(e) => setSourceParty(e.target.value)}
                placeholder="매도측 / 매수측"
              />
            </div>
            <div className="flex-1 min-w-[200px]">
              <label className="block text-xs text-text-secondary mb-1">
                파일
              </label>
              <input
                ref={fileRef}
                type="file"
                accept=".docx,.doc,.pdf"
                className="w-full text-sm"
              />
            </div>
            <Button
              icon={Upload}
              onClick={handleFileUpload}
              disabled={isUploading}
            >
              업로드
            </Button>
          </div>
        </Card>
      )}
    </div>
  );
}
