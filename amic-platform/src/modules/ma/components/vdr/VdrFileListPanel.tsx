import { ArrowDown, ArrowUp, FolderOpen, Upload } from "lucide-react";
import { useMemo, useState } from "react";

import type { DocumentExtraction } from "@/modules/ma/types/document_extraction";
import type { VdrDocument, VdrFolder } from "@/modules/ma/types/vdr";

import FileListRow from "./FileListRow";
import { getMimeLabel } from "./vdrFileUtils";

// ── 정렬 타입 ────────────────────────────────────────────

type SortColumn = "name" | "modified" | "type" | "size";
type SortDir = "asc" | "desc";

interface SortState {
  column: SortColumn;
  direction: SortDir;
}

// ── Props ────────────────────────────────────────────────

interface VdrFileListPanelProps {
  readOnly?: boolean;
  currentFolderId: string | null;
  subFolders: VdrFolder[];
  documents: VdrDocument[];
  docsLoading: boolean;
  onNavigate: (folderId: string | null) => void;
  onDeleteFolder: (id: string) => void;
  onDeleteDoc: (docId: string) => void;
  onStartExtraction?: (docId: string) => void;
  onRetryExtraction?: (extractionId: string) => void;
  extractionByDocId: Map<string, DocumentExtraction>;
  txnId: string;
  onDrop: (e: React.DragEvent) => void;
  onDragOver: (e: React.DragEvent) => void;
  onDragLeave: (e: React.DragEvent) => void;
  isDragOver: boolean;
}

// ── 정렬 로직 ────────────────────────────────────────────

function sortDocuments(docs: VdrDocument[], sort: SortState): VdrDocument[] {
  const sorted = [...docs];
  const dir = sort.direction === "asc" ? 1 : -1;
  sorted.sort((a, b) => {
    switch (sort.column) {
      case "name":
        return dir * a.original_name.localeCompare(b.original_name, "ko");
      case "modified":
        return dir * a.updated_at.localeCompare(b.updated_at);
      case "type":
        return (
          dir *
          getMimeLabel(a.mime_type).localeCompare(
            getMimeLabel(b.mime_type),
            "ko",
          )
        );
      case "size":
        return dir * (a.file_size_bytes - b.file_size_bytes);
      default:
        return 0;
    }
  });
  return sorted;
}

// ── 컬럼 헤더 ────────────────────────────────────────────

const COLUMNS: { key: SortColumn; label: string; className: string }[] = [
  { key: "name", label: "이름", className: "flex-1 min-w-0" },
  { key: "modified", label: "수정한 날짜", className: "w-40 shrink-0" },
  { key: "type", label: "유형", className: "w-[140px] shrink-0" },
  { key: "size", label: "크기", className: "w-20 shrink-0 text-right" },
];

// ── 컴포넌트 ─────────────────────────────────────────────

export default function VdrFileListPanel({
  readOnly = false,
  currentFolderId,
  subFolders,
  documents,
  docsLoading,
  onNavigate,
  onDeleteFolder,
  onDeleteDoc,
  onStartExtraction,
  onRetryExtraction,
  extractionByDocId,
  txnId,
  onDrop,
  onDragOver,
  onDragLeave,
  isDragOver,
}: VdrFileListPanelProps) {
  const [sort, setSort] = useState<SortState>({
    column: "name",
    direction: "asc",
  });

  const sortedDocs = useMemo(
    () => sortDocuments(documents, sort),
    [documents, sort],
  );

  const toggleSort = (column: SortColumn) => {
    setSort((prev) =>
      prev.column === column
        ? { column, direction: prev.direction === "asc" ? "desc" : "asc" }
        : { column, direction: "asc" },
    );
  };

  const hasFolders = subFolders.length > 0;
  const isEmpty = !hasFolders && documents.length === 0;

  return (
    <div
      className={`flex flex-1 min-w-0 flex-col transition-colors ${
        isDragOver ? "bg-accent/5 ring-2 ring-inset ring-accent/30" : ""
      }`}
      onDragOver={!readOnly && currentFolderId ? onDragOver : undefined}
      onDragLeave={!readOnly && currentFolderId ? onDragLeave : undefined}
      onDrop={!readOnly && currentFolderId ? onDrop : undefined}
    >
      {/* 컬럼 헤더 */}
      <div className="flex h-7 items-center gap-2 border-b border-slate-200 bg-slate-50 px-2 text-[11px] font-medium text-slate-500">
        {COLUMNS.map((col) => (
          <button
            key={col.key}
            type="button"
            className={`flex items-center gap-0.5 hover:text-slate-700 ${col.className}`}
            onClick={() => toggleSort(col.key)}
          >
            {col.label}
            {sort.column === col.key &&
              (sort.direction === "asc" ? (
                <ArrowUp className="h-3 w-3" />
              ) : (
                <ArrowDown className="h-3 w-3" />
              ))}
          </button>
        ))}
        {/* 상태 + 액션 영역의 헤더 공간 */}
        <div className="w-10 shrink-0" />
        <div className="w-16 shrink-0" />
      </div>

      {/* 콘텐츠 영역 */}
      <div className="flex-1 overflow-y-auto">
        {docsLoading ? (
          <div className="flex h-32 items-center justify-center text-sm text-slate-400">
            불러오는 중...
          </div>
        ) : isEmpty ? (
          <div className="flex h-full items-center justify-center px-6 py-10">
            <div className="flex w-full max-w-sm flex-col items-center rounded-2xl border border-slate-200 bg-slate-50/80 px-6 py-7 text-center shadow-sm">
              {currentFolderId ? (
                <Upload className="h-7 w-7 text-accent/70" />
              ) : (
                <FolderOpen className="h-7 w-7 text-accent/70" />
              )}
              <p className="mt-3 text-sm font-semibold text-slate-700">
                {currentFolderId
                  ? "이 폴더는 아직 비어 있습니다"
                  : "둘러볼 폴더를 선택하세요"}
              </p>
              <p className="mt-1 text-xs leading-5 text-slate-500">
                {currentFolderId
                  ? "파일을 드래그하거나 우측 상단 업로드 버튼으로 문서를 추가할 수 있습니다."
                  : "왼쪽 트리나 아래 목록에서 폴더를 선택하면 문서를 바로 확인할 수 있습니다."}
              </p>
            </div>
          </div>
        ) : (
          <div className="py-0.5">
            {subFolders.map((folder) => (
              <FileListRow
                key={folder.id}
                type="folder"
                folder={folder}
                onNavigate={onNavigate}
                onDelete={
                  !readOnly && !folder.is_required ? onDeleteFolder : undefined
                }
              />
            ))}
            {sortedDocs.map((doc) => (
              <FileListRow
                key={doc.id}
                type="file"
                document={doc}
                readOnly={readOnly}
                txnId={txnId}
                extraction={extractionByDocId.get(doc.id)}
                onDelete={readOnly ? undefined : onDeleteDoc}
                onStartExtraction={readOnly ? undefined : onStartExtraction}
                onRetryExtraction={readOnly ? undefined : onRetryExtraction}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
