import {
  CheckCircle2,
  Download,
  Files,
  FileText,
  FolderInput,
  Loader2,
  RefreshCw,
  Sparkles,
  Trash2,
  Upload,
  X,
} from "lucide-react";
import { useCallback, useMemo, useRef, useState } from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";
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
import {
  useCreateExtraction,
  useRetryExtraction,
} from "@/modules/ma/hooks/useDocumentExtraction";
import {
  IN_PROGRESS_STATUSES,
  CATEGORY_LABELS,
  EXTRACTABLE_CATEGORIES,
} from "@/modules/ma/types/document_extraction";
import type {
  DocumentExtraction,
  DocExtractionCategory,
} from "@/modules/ma/types/document_extraction";
import { formatFileSize, formatISODate } from "@/modules/ma/utils/format";

interface Props {
  txnId: string;
  folder: VdrFolder | null;
  documents: VdrDocument[];
  extractions: DocumentExtraction[];
  isLoading: boolean;
  isUploading?: boolean;
  onUpload: (file: File) => void;
  onDelete: (docId: string) => void;
  onNavigateToFolder?: (category: string) => void;
  folderMap?: Map<string, string>;
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
  extractions,
  isLoading,
  isUploading,
  onUpload,
  onDelete,
  onNavigateToFolder,
  folderMap,
}: Props) {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const createExtraction = useCreateExtraction(txnId);
  const retryExtraction = useRetryExtraction(txnId);
  const suggestCategory = useSuggestVdrCategory(txnId);
  const [suggestion, setSuggestion] = useState<CategorySuggestion | null>(null);
  // AI 분석 시작 전 카테고리 선택 대상 문서
  const [pendingDocId, setPendingDocId] = useState<string | null>(null);

  const isAllFilesMode = !folder && folderMap !== undefined;

  // vdr_document_id → extraction 매핑 (가장 최근 것 우선)
  const extractionByDocId = useMemo(() => {
    const map = new Map<string, DocumentExtraction>();
    for (const ext of extractions) {
      const existing = map.get(ext.vdr_document_id);
      if (!existing || ext.created_at > existing.created_at) {
        map.set(ext.vdr_document_id, ext);
      }
    }
    return map;
  }, [extractions]);

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

  if (!folder && !isAllFilesMode) {
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
            {isAllFilesMode ? "전체 파일" : folder?.name}
          </h3>
          <p className="text-xs text-slate-400">{documents.length}개 파일</p>
        </div>
        {!isAllFilesMode && (
          <>
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
          </>
        )}
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
        onDragOver={isAllFilesMode ? undefined : (e) => e.preventDefault()}
        onDrop={isAllFilesMode ? undefined : handleDrop}
      >
        {isLoading ? (
          <div className="flex h-32 items-center justify-center text-sm text-slate-400">
            불러오는 중...
          </div>
        ) : documents.length === 0 ? (
          <div className="flex h-full flex-col items-center justify-center gap-1.5 px-6 py-8 text-xs text-slate-400">
            {isAllFilesMode ? (
              <>
                <Files className="h-10 w-10 text-slate-200" />
                <p className="text-base font-medium text-slate-400">
                  파일을 업로드하세요
                </p>
                <p className="text-xs text-slate-300">
                  좌측에서 폴더를 선택한 후 파일을 업로드하거나, 빠른 업로드를
                  이용하세요
                </p>
              </>
            ) : (
              <>
                <Upload className="h-5 w-5 text-slate-300" />
                <p>파일을 드래그하거나 업로드 버튼을 클릭하세요</p>
              </>
            )}
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead className="border-b border-slate-100 text-left text-xs text-slate-500">
              <tr>
                <th className="px-4 py-2 font-medium">파일명</th>
                {isAllFilesMode && (
                  <th className="px-4 py-2 font-medium">폴더</th>
                )}
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
                  {isAllFilesMode && (
                    <td className="px-4 py-2 text-xs text-slate-500">
                      {folderMap?.get(doc.folder_id) ?? "-"}
                    </td>
                  )}
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
                      {(() => {
                        const ext = extractionByDocId.get(doc.id);
                        if (!ext) {
                          // 추출 없음 → 카테고리 선택 후 시작
                          return (
                            <button
                              type="button"
                              className="rounded p-1 text-slate-400 hover:bg-amber-50 hover:text-amber-600"
                              title="AI 분석"
                              onClick={() => setPendingDocId(doc.id)}
                            >
                              <Sparkles className="h-4 w-4" />
                            </button>
                          );
                        }
                        if (IN_PROGRESS_STATUSES.includes(ext.status)) {
                          // 진행중
                          return (
                            <span
                              className="flex items-center gap-1 rounded p-1 text-xs text-amber-600"
                              title="분석 진행중"
                            >
                              <Loader2 className="h-4 w-4 animate-spin" />
                            </span>
                          );
                        }
                        if (ext.status === "FAILED") {
                          // 실패 → 재시도
                          return (
                            <button
                              type="button"
                              className="rounded p-1 text-negative hover:bg-red-50"
                              title={
                                ext.error_message ??
                                "분석 실패 — 클릭하여 재시도"
                              }
                              onClick={() => retryExtraction.mutate(ext.id)}
                            >
                              <RefreshCw className="h-4 w-4" />
                            </button>
                          );
                        }
                        // COMPLETED / CONFIRMED
                        return (
                          <span
                            className="flex items-center rounded p-1 text-positive"
                            title="분석 완료"
                          >
                            <CheckCircle2 className="h-4 w-4" />
                          </span>
                        );
                      })()}
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

      {/* AI 분석 카테고리 선택 모달 */}
      <Modal
        open={pendingDocId !== null}
        onClose={() => setPendingDocId(null)}
        title="문서 종류 선택"
        size="sm"
      >
        <p className="mb-4 text-sm text-slate-500">
          이 문서의 종류를 선택하세요. AI가 해당 형식에 맞게 데이터를
          추출합니다.
        </p>
        <div className="flex flex-col gap-1.5">
          {(
            Object.entries(CATEGORY_LABELS) as [DocExtractionCategory, string][]
          ).map(([category, label]) => (
            <button
              key={category}
              type="button"
              className="flex items-center justify-between rounded-lg border border-slate-200 px-3 py-2.5 text-left text-sm transition-colors hover:border-slate-400 hover:bg-slate-50"
              onClick={() => {
                if (pendingDocId) {
                  createExtraction.mutate({
                    vdrDocumentId: pendingDocId,
                    docCategoryHint: category,
                  });
                  setPendingDocId(null);
                }
              }}
            >
              <span className="font-medium text-slate-700">{label}</span>
              {EXTRACTABLE_CATEGORIES.has(category) ? (
                <span className="text-xs text-emerald-600">데이터 추출</span>
              ) : (
                <span className="text-xs text-slate-400">분류만</span>
              )}
            </button>
          ))}
        </div>
      </Modal>
    </div>
  );
}
