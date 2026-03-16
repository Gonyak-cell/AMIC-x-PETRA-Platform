import { FolderInput, FolderPlus, Upload, X } from "lucide-react";
import { useCallback, useMemo, useRef, useState } from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";
import type { VdrFolder } from "@/modules/ma/types/vdr";
import { VDR_CATEGORY_LABELS, VDR_CONSTRAINTS } from "@/modules/ma/types/vdr";
import type { VdrFolderCategory } from "@/modules/ma/types/vdr";
import {
  getVdrDownloadUrl,
  useSuggestVdrCategory,
  useUploadVdrDocument,
  useDeleteVdrDocument,
  useVdrDocuments,
} from "@/modules/ma/hooks/useVdr";
import {
  useCreateExtraction,
  useRetryExtraction,
} from "@/modules/ma/hooks/useDocumentExtraction";
import {
  CATEGORY_LABELS,
  EXTRACTABLE_CATEGORIES,
} from "@/modules/ma/types/document_extraction";
import type {
  DocumentExtraction,
  DocExtractionCategory,
} from "@/modules/ma/types/document_extraction";
import { formatFileSize } from "@/modules/ma/utils/format";
import ExplorerToolbar from "./ExplorerToolbar";
import type { ViewMode } from "./ExplorerToolbar";
import FileCard from "./FileCard";
import FolderCard from "./FolderCard";
import VdrFileListPanel from "./VdrFileListPanel";
import VdrFolderTreePanel from "./VdrFolderTreePanel";
import { buildBreadcrumbs, buildFolderIndex } from "./vdrTree";

interface VdrExplorerProps {
  txnId: string;
  folders: VdrFolder[];
  onCreateFolder: (name: string, parentId?: string) => void;
  onDeleteFolder: (id: string) => void;
  extractions: DocumentExtraction[];
}

interface CategorySuggestion {
  filename: string;
  category: string;
  folderName: string;
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

export default function VdrExplorer({
  txnId,
  folders,
  onCreateFolder,
  onDeleteFolder,
  extractions,
}: VdrExplorerProps) {
  const [currentFolderId, setCurrentFolderId] = useState<string | null>(null);
  const [pendingDocId, setPendingDocId] = useState<string | null>(null);
  const [showNewFolderModal, setShowNewFolderModal] = useState(false);
  const [newFolderName, setNewFolderName] = useState("");
  const [suggestion, setSuggestion] = useState<CategorySuggestion | null>(null);
  const [viewMode, setViewMode] = useState<ViewMode>("grid");
  const fileInputRef = useRef<HTMLInputElement>(null);

  const suggestCategory = useSuggestVdrCategory(txnId);
  const uploadDoc = useUploadVdrDocument(txnId, currentFolderId ?? "");
  const deleteDoc = useDeleteVdrDocument(txnId);
  const createExtraction = useCreateExtraction(txnId);
  const retryExtraction = useRetryExtraction(txnId);

  const { data: documents = [], isLoading: docsLoading } = useVdrDocuments(
    txnId,
    currentFolderId,
  );

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

  // 트리 인덱스: 단일 순회로 id→폴더 / parentId→자식목록 맵 구축
  const { folderById, childrenByParentId } = useMemo(
    () => buildFolderIndex(folders),
    [folders],
  );

  const breadcrumbs = useMemo(
    () => buildBreadcrumbs(folderById, currentFolderId),
    [folderById, currentFolderId],
  );

  // O(1) Map 조회로 filter 대체
  const rootFolders = childrenByParentId.get(null) ?? [];
  const currentSubFolders =
    currentFolderId !== null
      ? (childrenByParentId.get(currentFolderId) ?? [])
      : [];

  const handleDeleteFolder = useCallback(
    (folderId: string) => {
      if (currentFolderId === folderId) {
        setCurrentFolderId(null);
      }
      onDeleteFolder(folderId);
    },
    [currentFolderId, onDeleteFolder],
  );

  const handleUploadFile = useCallback(
    (file: File) => {
      if (!currentFolderId) return;
      uploadDoc.mutate(file);
      const currentFolder = folderById.get(currentFolderId);
      suggestCategory.mutate(file.name, {
        onSuccess: (result) => {
          if (
            result.category &&
            result.category !== currentFolder?.category &&
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
    },
    [currentFolderId, uploadDoc, suggestCategory, folderById],
  );

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      if (!currentFolderId) return;
      for (const file of Array.from(e.dataTransfer.files)) {
        const error = validateFile(file);
        if (error) {
          toast.error(error);
          continue;
        }
        handleUploadFile(file);
      }
    },
    [currentFolderId, handleUploadFile],
  );

  const handleCreateFolder = useCallback(() => {
    const name = newFolderName.trim();
    if (!name) return;
    onCreateFolder(name, currentFolderId ?? undefined);
    setNewFolderName("");
    setShowNewFolderModal(false);
  }, [newFolderName, currentFolderId, onCreateFolder]);

  const isUploading = uploadDoc.isPending;

  return (
    <div className="flex h-full flex-col">
      <ExplorerToolbar
        breadcrumbs={breadcrumbs}
        onNavigate={setCurrentFolderId}
        onCreateFolder={() => setShowNewFolderModal(true)}
        currentFolderId={currentFolderId}
        isUploading={isUploading}
        onUploadClick={() => fileInputRef.current?.click()}
        viewMode={viewMode}
        onViewModeChange={setViewMode}
      />

      {/* 숨긴 파일 입력 */}
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
            handleUploadFile(file);
          }
          e.target.value = "";
        }}
      />

      {/* AI 카테고리 추천 배너 */}
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
          <button
            type="button"
            className="ml-auto shrink-0 text-amber-400 hover:text-amber-600"
            onClick={() => setSuggestion(null)}
            aria-label="닫기"
          >
            <X className="h-3.5 w-3.5" />
          </button>
        </div>
      )}

      {viewMode === "grid" ? (
        /* ─── 기존 그리드 뷰 ─── */
        <div
          className="flex-1 overflow-y-auto"
          onDragOver={currentFolderId ? (e) => e.preventDefault() : undefined}
          onDrop={currentFolderId ? handleDrop : undefined}
        >
          {currentFolderId === null ? (
            rootFolders.length === 0 ? (
              <div className="flex h-full flex-col items-center justify-center gap-2 text-slate-400">
                <FolderPlus className="h-10 w-10 text-slate-200" />
                <p className="text-sm font-medium">
                  폴더를 생성하여 문서를 정리하세요
                </p>
              </div>
            ) : (
              <div
                className="grid gap-3 p-4"
                style={{
                  gridTemplateColumns: "repeat(auto-fill, minmax(120px, 1fr))",
                }}
              >
                {rootFolders.map((folder) => (
                  <FolderCard
                    key={folder.id}
                    folder={folder}
                    onOpen={setCurrentFolderId}
                    onDelete={
                      !folder.is_required ? handleDeleteFolder : undefined
                    }
                  />
                ))}
              </div>
            )
          ) : docsLoading ? (
            <div className="flex h-32 items-center justify-center text-sm text-slate-400">
              불러오는 중...
            </div>
          ) : currentSubFolders.length === 0 && documents.length === 0 ? (
            <div className="flex h-full flex-col items-center justify-center gap-2 text-slate-400">
              <Upload className="h-8 w-8 text-slate-200" />
              <p className="text-sm">
                파일을 드래그하거나 업로드 버튼을 클릭하세요
              </p>
            </div>
          ) : (
            <div
              className="grid gap-3 p-4"
              style={{
                gridTemplateColumns: "repeat(auto-fill, minmax(120px, 1fr))",
              }}
            >
              {currentSubFolders.map((folder) => (
                <FolderCard
                  key={folder.id}
                  folder={folder}
                  onOpen={setCurrentFolderId}
                  onDelete={
                    !folder.is_required ? handleDeleteFolder : undefined
                  }
                />
              ))}
              {documents.map((doc) => (
                <FileCard
                  key={doc.id}
                  document={doc}
                  extraction={extractionByDocId.get(doc.id)}
                  onDelete={(docId) =>
                    deleteDoc.mutate({ docId, folderId: currentFolderId! })
                  }
                  onStartExtraction={(docId) => setPendingDocId(docId)}
                  onRetryExtraction={(extractionId) =>
                    retryExtraction.mutate(extractionId)
                  }
                  downloadUrl={getVdrDownloadUrl(txnId, doc.id)}
                />
              ))}
            </div>
          )}
        </div>
      ) : (
        /* ─── 신규 탐색기 뷰 ─── */
        <div className="flex flex-1 min-h-0">
          <VdrFolderTreePanel
            childrenByParentId={childrenByParentId}
            folderById={folderById}
            currentFolderId={currentFolderId}
            onNavigate={setCurrentFolderId}
          />
          <VdrFileListPanel
            currentFolderId={currentFolderId}
            subFolders={
              currentFolderId !== null ? currentSubFolders : rootFolders
            }
            documents={currentFolderId !== null ? documents : []}
            docsLoading={docsLoading}
            onNavigate={setCurrentFolderId}
            onDeleteFolder={handleDeleteFolder}
            onDeleteDoc={(docId) =>
              deleteDoc.mutate({ docId, folderId: currentFolderId! })
            }
            onStartExtraction={(docId) => setPendingDocId(docId)}
            onRetryExtraction={(extractionId) =>
              retryExtraction.mutate(extractionId)
            }
            extractionByDocId={extractionByDocId}
            txnId={txnId}
            onDrop={handleDrop}
          />
        </div>
      )}

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

      {/* 새 폴더 생성 모달 */}
      <Modal
        open={showNewFolderModal}
        onClose={() => {
          setShowNewFolderModal(false);
          setNewFolderName("");
        }}
        title="새 폴더 만들기"
        size="sm"
      >
        <div className="flex flex-col gap-4">
          <input
            type="text"
            className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-slate-400"
            placeholder="폴더 이름"
            value={newFolderName}
            onChange={(e) => setNewFolderName(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") handleCreateFolder();
            }}
            autoFocus
          />
          <div className="flex justify-end gap-2">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => {
                setShowNewFolderModal(false);
                setNewFolderName("");
              }}
            >
              취소
            </Button>
            <Button
              variant="primary"
              size="sm"
              disabled={!newFolderName.trim()}
              onClick={handleCreateFolder}
            >
              만들기
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
