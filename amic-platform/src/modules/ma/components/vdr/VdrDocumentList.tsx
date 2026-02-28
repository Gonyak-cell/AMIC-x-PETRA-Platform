import {
  Download,
  FileText,
  FolderInput,
  Sparkles,
  Trash2,
  Upload,
  X,
} from "lucide-react";
import { useCallback, useRef, useState } from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/Button";
import type { VdrDocument, VdrFolder } from "@/modules/ma/types/vdr";
import {
  MIME_TYPE_LABELS,
  VDR_CATEGORY_LABELS,
  VDR_CONSTRAINTS,
} from "@/modules/ma/types/vdr";
import type { VdrFolderCategory } from "@/modules/ma/types/vdr";
import {
  getVdrDownloadUrl,
  useSuggestVdrCategory,
} from "@/modules/ma/hooks/useVdr";
import { useCreateExtraction } from "@/modules/ma/hooks/useDocumentExtraction";
import { formatFileSize, formatISODate } from "@/modules/ma/utils/format";

interface Props {
  txnId: string;
  folder: VdrFolder | null;
  documents: VdrDocument[];
  isLoading: boolean;
  isUploading?: boolean;
  onUpload: (file: File) => void;
  onDelete: (docId: string) => void;
  onNavigateToFolder?: (category: string) => void;
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

interface CategorySuggestion {
  filename: string;
  category: string;
  folderName: string;
}

export default function VdrDocumentList({
  txnId,
  folder,
  documents,
  isLoading,
  isUploading,
  onUpload,
  onDelete,
  onNavigateToFolder,
}: Props) {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const createExtraction = useCreateExtraction(txnId);
  const suggestCategory = useSuggestVdrCategory(txnId);
  const [suggestion, setSuggestion] = useState<CategorySuggestion | null>(null);

  const uploadWithSuggestion = useCallback(
    (file: File) => {
      onUpload(file);
      if (folder) {
        suggestCategory.mutate(file.name, {
          onSuccess: (result) => {
            if (
              result.category &&
              result.category !== folder.category &&
              result.folder_name
            ) {
              setSuggestion({
                filename: file.name,
                category: result.category,
                folderName: result.folder_name,
              });
            }
          },
        });
      }
    },
    [onUpload, folder, suggestCategory],
  );

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      for (const file of Array.from(e.dataTransfer.files)) {
        const error = validateFile(file);
        if (error) {
          toast.error(error);
          continue;
        }
        uploadWithSuggestion(file);
      }
    },
    [uploadWithSuggestion],
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
          <p className="text-xs text-slate-400">{documents.length}개 파일</p>
        </div>
        <Button
          variant="primary"
          size="sm"
          disabled={isUploading}
          onClick={() => fileInputRef.current?.click()}
        >
          <Upload className="mr-1 h-3.5 w-3.5" />
          {isUploading ? "업로드 중..." : "업로드"}
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
              uploadWithSuggestion(file);
            }
            e.target.value = "";
          }}
        />
      </div>

      {/* Category Suggestion Banner */}
      {suggestion && (
        <div className="flex items-center gap-2 border-b border-amber-200 bg-amber-50 px-4 py-2 text-xs">
          <FolderInput className="h-4 w-4 shrink-0 text-amber-600" />
          <span className="text-amber-800">
            <strong>{suggestion.filename}</strong>은{" "}
            <strong>
              {VDR_CATEGORY_LABELS[suggestion.category as VdrFolderCategory] ??
                suggestion.folderName}
            </strong>{" "}
            폴더에 더 적합할 수 있습니다.
          </span>
          {onNavigateToFolder && (
            <button
              type="button"
              className="ml-auto shrink-0 rounded bg-amber-100 px-2 py-0.5 text-amber-700 hover:bg-amber-200"
              onClick={() => {
                onNavigateToFolder(suggestion.category);
                setSuggestion(null);
              }}
            >
              이동
            </button>
          )}
          <button
            type="button"
            className="shrink-0 text-amber-400 hover:text-amber-600"
            onClick={() => setSuggestion(null)}
            aria-label="닫기"
          >
            <X className="h-3.5 w-3.5" />
          </button>
        </div>
      )}

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
                    {MIME_TYPE_LABELS[doc.mime_type] ??
                      doc.mime_type.split("/")[1]}
                  </td>
                  <td className="px-4 py-2 text-slate-500">
                    {formatFileSize(doc.file_size_bytes)}
                  </td>
                  <td className="px-4 py-2 text-slate-500">
                    {formatISODate(doc.created_at)}
                  </td>
                  <td className="px-4 py-2">
                    <div className="flex items-center gap-1">
                      <button
                        type="button"
                        className="rounded p-1 text-slate-400 hover:bg-amber-50 hover:text-amber-600"
                        title="AI 분석"
                        onClick={() =>
                          createExtraction.mutate({ vdrDocumentId: doc.id })
                        }
                      >
                        <Sparkles className="h-4 w-4" />
                      </button>
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
                        onClick={() => {
                          if (window.confirm("이 문서를 삭제하시겠습니까?"))
                            onDelete(doc.id);
                        }}
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
