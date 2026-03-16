/**
 * VDR 파일/문서 공유 유틸리티
 *
 * FileCard(그리드 뷰)와 FileListRow(리스트 뷰) 모두에서 사용하는
 * 아이콘, 레이블, 상태 인디케이터, AI 분석 배지를 제공한다.
 */

import {
  CheckCircle2,
  File,
  FileArchive,
  FileImage,
  FileSpreadsheet,
  FileText,
  Loader2,
  RefreshCw,
  Sparkles,
} from "lucide-react";
import type { ReactNode } from "react";

import type { DocumentExtraction } from "@/modules/ma/types/document_extraction";
import { IN_PROGRESS_STATUSES } from "@/modules/ma/types/document_extraction";
import type { VdrDocumentStatus } from "@/modules/ma/types/vdr";

// ── MIME 아이콘 ──────────────────────────────────────────

const ICON_SIZE = { sm: "h-4 w-4", md: "h-8 w-8" } as const;

export function getMimeIcon(
  mimeType: string,
  size: "sm" | "md" = "md",
): ReactNode {
  const cls = ICON_SIZE[size];
  if (mimeType === "application/pdf")
    return <FileText className={`${cls} text-red-400`} />;
  if (
    mimeType === "application/vnd.ms-excel" ||
    mimeType.includes("spreadsheetml")
  )
    return <FileSpreadsheet className={`${cls} text-green-500`} />;
  if (
    mimeType === "application/msword" ||
    mimeType.includes("wordprocessingml")
  )
    return <FileText className={`${cls} text-blue-400`} />;
  if (
    mimeType === "application/vnd.ms-powerpoint" ||
    mimeType.includes("presentationml")
  )
    return <FileText className={`${cls} text-orange-400`} />;
  if (mimeType.startsWith("image/"))
    return <FileImage className={`${cls} text-purple-400`} />;
  if (
    mimeType === "application/zip" ||
    mimeType === "application/x-zip-compressed"
  )
    return <FileArchive className={`${cls} text-slate-400`} />;
  return <File className={`${cls} text-slate-400`} />;
}

// ── MIME 레이블 ──────────────────────────────────────────

const MIME_LABELS: Record<string, string> = {
  "application/pdf": "PDF 문서",
  "application/vnd.ms-excel": "Excel 스프레드시트",
  "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet":
    "Excel 스프레드시트",
  "application/msword": "Word 문서",
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
    "Word 문서",
  "application/vnd.ms-powerpoint": "PowerPoint 프레젠테이션",
  "application/vnd.openxmlformats-officedocument.presentationml.presentation":
    "PowerPoint 프레젠테이션",
  "application/zip": "ZIP 압축파일",
  "application/x-zip-compressed": "ZIP 압축파일",
  "text/plain": "텍스트 파일",
  "text/csv": "CSV 파일",
  "application/json": "JSON 파일",
  "application/x-hwp": "한글 문서",
};

export function getMimeLabel(mimeType: string): string {
  if (MIME_LABELS[mimeType]) return MIME_LABELS[mimeType];
  if (mimeType.startsWith("image/")) return "이미지 파일";
  return "파일";
}

// ── 문서 상태 색상 ──────────────────────────────────────

export function getStatusColor(status: VdrDocumentStatus): string {
  switch (status) {
    case "ACTIVE":
      return "bg-emerald-500";
    case "ARCHIVED":
      return "bg-amber-400";
    case "DELETED":
      return "bg-red-400";
    default:
      return "bg-slate-300";
  }
}

// ── AI 분석 배지 ─────────────────────────────────────────

interface ExtractionBadgeProps {
  extraction?: DocumentExtraction;
  docId: string;
  onStartExtraction: (docId: string) => void;
  onRetryExtraction: (extractionId: string) => void;
}

export function ExtractionBadge({
  extraction,
  docId,
  onStartExtraction,
  onRetryExtraction,
}: ExtractionBadgeProps) {
  if (!extraction) {
    return (
      <button
        type="button"
        className="rounded p-0.5 text-slate-400 hover:bg-amber-50 hover:text-amber-600"
        title="AI 분석"
        onClick={(e) => {
          e.stopPropagation();
          onStartExtraction(docId);
        }}
      >
        <Sparkles className="h-3.5 w-3.5" />
      </button>
    );
  }
  if (IN_PROGRESS_STATUSES.includes(extraction.status)) {
    return (
      <span className="text-amber-500" title="분석 진행중">
        <Loader2 className="h-3.5 w-3.5 animate-spin" />
      </span>
    );
  }
  if (extraction.status === "FAILED") {
    return (
      <button
        type="button"
        className="text-negative hover:text-red-700"
        title={extraction.error_message ?? "분석 실패 — 클릭하여 재시도"}
        onClick={(e) => {
          e.stopPropagation();
          onRetryExtraction(extraction.id);
        }}
      >
        <RefreshCw className="h-3.5 w-3.5" />
      </button>
    );
  }
  return (
    <span className="text-positive" title="분석 완료">
      <CheckCircle2 className="h-3.5 w-3.5" />
    </span>
  );
}
