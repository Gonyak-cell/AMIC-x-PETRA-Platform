import { ArrowDown, ArrowUp, Upload } from "lucide-react";
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
  currentFolderId: string | null;
  subFolders: VdrFolder[];
  documents: VdrDocument[];
  docsLoading: boolean;
  onNavigate: (folderId: string | null) => void;
  onDeleteFolder: (id: string) => void;
  onDeleteDoc: (docId: string) => void;
  onStartExtraction: (docId: string) => void;
  onRetryExtraction: (extractionId: string) => void;
  extractionByDocId: Map<string, DocumentExtraction>;
  txnId: string;
  onDrop: (e: React.DragEvent) => void;
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
  currentFolderId,
  subFolders: _subFolders,
  documents,
  docsLoading,
  onNavigate: _onNavigate,
  onDeleteFolder: _onDeleteFolder,
  onDeleteDoc,
  onStartExtraction,
  onRetryExtraction,
  extractionByDocId,
  txnId,
  onDrop,
}: VdrFileListPanelProps) {
  // 폴더는 좌측 트리에서만 탐색 — 우측 패널은 파일만 표시
  void _subFolders;
  void _onNavigate;
  void _onDeleteFolder;

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

  const isEmpty = documents.length === 0;

  return (
    <div
      className="flex flex-1 flex-col min-w-0"
      onDragOver={currentFolderId ? (e) => e.preventDefault() : undefined}
      onDrop={currentFolderId ? onDrop : undefined}
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
          <div className="flex h-full flex-col items-center justify-center gap-2 text-slate-400">
            <Upload className="h-8 w-8 text-slate-200" />
            <p className="text-sm">
              {currentFolderId
                ? "파일을 드래그하거나 업로드 버튼을 클릭하세요"
                : "폴더를 선택하세요"}
            </p>
          </div>
        ) : (
          <div className="py-0.5">
            {/* 폴더는 좌측 트리에서만 탐색 — 우측 패널은 파일만 표시 */}
            {/* 파일 */}
            {sortedDocs.map((doc) => (
              <FileListRow
                key={doc.id}
                type="file"
                document={doc}
                txnId={txnId}
                extraction={extractionByDocId.get(doc.id)}
                onDelete={onDeleteDoc}
                onStartExtraction={onStartExtraction}
                onRetryExtraction={onRetryExtraction}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
