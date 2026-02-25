import {
  Download,
  FileText,
  Trash2,
  Upload,
} from "lucide-react";
import { useCallback, useRef } from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/Button";
import type { VdrDocument, VdrFolder } from "@/modules/ma/types/vdr";
import { MIME_TYPE_LABELS, VDR_CONSTRAINTS } from "@/modules/ma/types/vdr";
import { getVdrDownloadUrl } from "@/modules/ma/hooks/useVdr";

interface Props {
  txnId: string;
  folder: VdrFolder | null;
  documents: VdrDocument[];
  isLoading: boolean;
  onUpload: (file: File) => void;
  onDelete: (docId: string) => void;
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
  if (file.size > VDR_CONSTRAINTS.MAX_FILE_SIZE) {
    return `파일 크기(${formatFileSize(file.size)})가 최대 허용량(${VDR_CONSTRAINTS.MAX_FILE_SIZE_LABEL})을 초과합니다.`;
  }
  if (file.type && !VDR_CONSTRAINTS.ALLOWED_MIME_TYPES.has(file.type)) {
    return `허용되지 않는 파일 형식입니다: ${file.type}`;
  }
  return null;
}

export default function VdrDocumentList({
  txnId,
  folder,
  documents,
  isLoading,
  onUpload,
  onDelete,
}: Props) {
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      for (const file of Array.from(e.dataTransfer.files)) {
        const error = validateFile(file);
        if (error) {
          toast.error(error);
          continue;
        }
        onUpload(file);
      }
    },
    [onUpload],
  );

  if (!folder) {
    return (
      <div className="flex h-full items-center justify-center text-sm text-slate-400">
        좌측에서 폴더를 선택하세요
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-slate-200 px-4 py-2">
        <div>
          <h3 className="text-sm font-semibold text-slate-700">
            {folder.name}
          </h3>
          <p className="text-xs text-slate-400">
            {documents.length}개 파일
          </p>
        </div>
        <Button
          variant="primary"
          size="sm"
          onClick={() => fileInputRef.current?.click()}
        >
          <Upload className="mr-1 h-3.5 w-3.5" />
          업로드
        </Button>
        <input
          ref={fileInputRef}
          type="file"
          className="hidden"
          multiple
          accept={VDR_CONSTRAINTS.ACCEPT_EXTENSIONS}
          onChange={(e) => {
            for (const file of Array.from(e.target.files ?? [])) {
              const error = validateFile(file);
              if (error) {
                toast.error(error);
                continue;
              }
              onUpload(file);
            }
            e.target.value = "";
          }}
        />
      </div>

      {/* Drop zone + list */}
      <div
        className="flex-1 overflow-y-auto"
        onDragOver={(e) => e.preventDefault()}
        onDrop={handleDrop}
      >
        {isLoading ? (
          <div className="flex h-32 items-center justify-center text-sm text-slate-400">
            불러오는 중...
          </div>
        ) : documents.length === 0 ? (
          <div className="flex h-32 flex-col items-center justify-center gap-2 text-sm text-slate-400">
            <Upload className="h-8 w-8 text-slate-300" />
            <p>파일을 여기에 드래그하거나 업로드 버튼을 클릭하세요</p>
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
              {documents.map((doc) => (
                <tr
                  key={doc.id}
                  className="border-b border-slate-50 hover:bg-slate-50"
                >
                  <td className="px-4 py-2">
                    <div className="flex items-center gap-2">
                      <FileText className="h-4 w-4 shrink-0 text-slate-400" />
                      <span className="truncate" title={doc.original_name}>
                        {doc.original_name}
                      </span>
                    </div>
                  </td>
                  <td className="px-4 py-2 text-slate-500">
                    {MIME_TYPE_LABELS[doc.mime_type] ?? doc.mime_type.split("/")[1]}
                  </td>
                  <td className="px-4 py-2 text-slate-500">
                    {formatFileSize(doc.file_size_bytes)}
                  </td>
                  <td className="px-4 py-2 text-slate-500">
                    {formatDate(doc.created_at)}
                  </td>
                  <td className="px-4 py-2">
                    <div className="flex items-center gap-1">
                      <a
                        href={getVdrDownloadUrl(txnId, doc.id)}
                        className="rounded p-1 text-slate-400 hover:bg-slate-100 hover:text-info"
                        title="다운로드"
                      >
                        <Download className="h-4 w-4" />
                      </a>
                      <button
                        type="button"
                        className="rounded p-1 text-slate-400 hover:bg-slate-100 hover:text-negative"
                        title="삭제"
                        onClick={() => onDelete(doc.id)}
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
