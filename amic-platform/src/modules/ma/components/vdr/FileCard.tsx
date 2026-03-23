import { Download, Trash2 } from "lucide-react";

import type { VdrDocument } from "@/modules/ma/types/vdr";
import type { DocumentExtraction } from "@/modules/ma/types/document_extraction";
import { formatFileSize } from "@/modules/ma/utils/format";
import { ExtractionBadge, getMimeIcon } from "./vdrFileUtils";

interface FileCardProps {
  document: VdrDocument;
  readOnly?: boolean;
  extraction?: DocumentExtraction;
  onDelete?: (docId: string) => void;
  onStartExtraction?: (docId: string) => void;
  onRetryExtraction?: (extractionId: string) => void;
  downloadUrl: string;
}

export default function FileCard({
  document: doc,
  readOnly = false,
  extraction,
  onDelete,
  onStartExtraction,
  onRetryExtraction,
  downloadUrl,
}: FileCardProps) {
  return (
    <div className="group relative flex flex-col items-center gap-1.5 rounded-lg border border-slate-200 bg-white p-3 transition-all hover:border-slate-300 hover:shadow-sm">
      {/* MIME 아이콘 */}
      <div className="relative mt-1 flex-shrink-0">
        {getMimeIcon(doc.mime_type)}
      </div>

      {/* 파일명 */}
      <p
        className="line-clamp-2 w-full text-center text-xs font-medium text-slate-700 leading-tight"
        title={doc.original_name}
      >
        {doc.original_name}
      </p>

      {/* 파일 크기 */}
      <p className="text-[10px] text-slate-400">
        {formatFileSize(doc.file_size_bytes)}
      </p>

      {/* 호버 액션 오버레이 */}
      <div className="absolute inset-0 flex items-end justify-center gap-1 rounded-lg bg-white/90 pb-2 opacity-0 transition-opacity group-hover:opacity-100">
        {!readOnly && onStartExtraction && onRetryExtraction && (
          <ExtractionBadge
            extraction={extraction}
            docId={doc.id}
            onStartExtraction={onStartExtraction}
            onRetryExtraction={onRetryExtraction}
          />
        )}
        <a
          href={downloadUrl}
          className="rounded p-0.5 text-slate-500 hover:bg-slate-100 hover:text-info"
          title="다운로드"
          onClick={(e) => e.stopPropagation()}
        >
          <Download className="h-3.5 w-3.5" />
        </a>
        {onDelete && <button
          type="button"
          className="rounded p-0.5 text-slate-400 hover:bg-red-50 hover:text-negative"
          title="삭제"
          onClick={(e) => {
            e.stopPropagation();
            if (window.confirm("이 문서를 삭제하시겠습니까?")) onDelete(doc.id);
          }}
        >
          <Trash2 className="h-3.5 w-3.5" />
        </button>}
      </div>
    </div>
  );
}
