import { Download, Folder, Trash2 } from "lucide-react";

import type { DocumentExtraction } from "@/modules/ma/types/document_extraction";
import type { VdrDocument, VdrFolder } from "@/modules/ma/types/vdr";
import { formatFileSize } from "@/modules/ma/utils/format";
import { getVdrDownloadUrl } from "@/modules/ma/hooks/useVdr";

import {
  ExtractionBadge,
  getMimeIcon,
  getMimeLabel,
  getStatusColor,
} from "./vdrFileUtils";

// ── 타입 ─────────────────────────────────────────────────

interface FolderRowProps {
  type: "folder";
  folder: VdrFolder;
  onNavigate: (folderId: string) => void;
  onDelete?: (folderId: string) => void;
}

interface FileRowProps {
  type: "file";
  document: VdrDocument;
  txnId: string;
  extraction?: DocumentExtraction;
  onDelete: (docId: string) => void;
  onStartExtraction: (docId: string) => void;
  onRetryExtraction: (extractionId: string) => void;
}

export type FileListRowProps = FolderRowProps | FileRowProps;

// ── 날짜 포맷 ────────────────────────────────────────────

function formatDate(iso: string): string {
  const d = new Date(iso);
  const yyyy = d.getFullYear();
  const mm = String(d.getMonth() + 1).padStart(2, "0");
  const dd = String(d.getDate()).padStart(2, "0");
  const hh = String(d.getHours()).padStart(2, "0");
  const mi = String(d.getMinutes()).padStart(2, "0");
  return `${yyyy}-${mm}-${dd} ${hh}:${mi}`;
}

// ── 컴포넌트 ─────────────────────────────────────────────

export default function FileListRow(props: FileListRowProps) {
  if (props.type === "folder") return <FolderRow {...props} />;
  return <FileRow {...props} />;
}

function FolderRow({ folder, onNavigate, onDelete }: FolderRowProps) {
  return (
    <div
      className="group flex h-8 cursor-pointer items-center gap-2 rounded px-2 text-xs transition-colors hover:bg-accent/5"
      onClick={() => onNavigate(folder.id)}
      role="row"
      tabIndex={0}
      onKeyDown={(e) => {
        if (e.key === "Enter") onNavigate(folder.id);
      }}
    >
      {/* 이름 */}
      <div className="flex min-w-0 flex-1 items-center gap-1.5">
        <Folder className="h-4 w-4 shrink-0 text-amber-400 fill-amber-100" />
        <span className="truncate font-medium text-slate-700">
          {folder.name}
        </span>
        {folder.is_required && (
          <span className="text-[10px] font-bold text-negative">*</span>
        )}
      </div>

      {/* 상태 — 폴더는 빈 칸 */}
      <div className="w-10 shrink-0" />

      {/* 수정일 */}
      <div className="w-40 shrink-0 text-slate-500">
        {formatDate(folder.updated_at)}
      </div>

      {/* 유형 */}
      <div className="w-[140px] shrink-0 text-slate-500">파일 폴더</div>

      {/* 크기 */}
      <div className="w-20 shrink-0 text-right text-slate-400">—</div>

      {/* 액션 — 호버 시 삭제 */}
      <div className="flex w-16 shrink-0 items-center justify-end gap-0.5 opacity-0 group-hover:opacity-100">
        {!folder.is_required && onDelete && (
          <button
            type="button"
            className="rounded p-0.5 text-slate-400 hover:bg-red-50 hover:text-negative"
            title="폴더 삭제"
            onClick={(e) => {
              e.stopPropagation();
              if (window.confirm(`${folder.name} 폴더를 삭제하시겠습니까?`))
                onDelete(folder.id);
            }}
          >
            <Trash2 className="h-3.5 w-3.5" />
          </button>
        )}
      </div>
    </div>
  );
}

function FileRow({
  document: doc,
  txnId,
  extraction,
  onDelete,
  onStartExtraction,
  onRetryExtraction,
}: FileRowProps) {
  return (
    <div
      className="group flex h-8 items-center gap-2 rounded px-2 text-xs transition-colors hover:bg-accent/5"
      role="row"
    >
      {/* 이름 */}
      <div className="flex min-w-0 flex-1 items-center gap-1.5">
        {getMimeIcon(doc.mime_type, "sm")}
        <span className="truncate text-slate-700" title={doc.original_name}>
          {doc.original_name}
        </span>
      </div>

      {/* 상태 인디케이터 */}
      <div className="flex w-10 shrink-0 items-center justify-center">
        <span
          className={`inline-block h-2 w-2 rounded-full ${getStatusColor(doc.status)}`}
          title={doc.status}
        />
      </div>

      {/* 수정일 */}
      <div className="w-40 shrink-0 text-slate-500">
        {formatDate(doc.updated_at)}
      </div>

      {/* 유형 */}
      <div className="w-[140px] shrink-0 text-slate-500">
        {getMimeLabel(doc.mime_type)}
      </div>

      {/* 크기 */}
      <div className="w-20 shrink-0 text-right text-slate-500">
        {formatFileSize(doc.file_size_bytes)}
      </div>

      {/* 액션 — 호버 시 표시 */}
      <div className="flex w-16 shrink-0 items-center justify-end gap-0.5 opacity-0 group-hover:opacity-100">
        <ExtractionBadge
          extraction={extraction}
          docId={doc.id}
          onStartExtraction={onStartExtraction}
          onRetryExtraction={onRetryExtraction}
        />
        <a
          href={getVdrDownloadUrl(txnId, doc.id)}
          className="rounded p-0.5 text-slate-500 hover:bg-slate-100 hover:text-info"
          title="다운로드"
          onClick={(e) => e.stopPropagation()}
        >
          <Download className="h-3.5 w-3.5" />
        </a>
        <button
          type="button"
          className="rounded p-0.5 text-slate-400 hover:bg-red-50 hover:text-negative"
          title="삭제"
          onClick={(e) => {
            e.stopPropagation();
            if (window.confirm("이 문서를 삭제하시겠습니까?")) onDelete(doc.id);
          }}
        >
          <Trash2 className="h-3.5 w-3.5" />
        </button>
      </div>
    </div>
  );
}
