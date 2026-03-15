import {
  CheckCircle2,
  Download,
  File,
  FileArchive,
  FileImage,
  FileSpreadsheet,
  FileText,
  Loader2,
  RefreshCw,
  Sparkles,
  Trash2,
} from 'lucide-react';

import type { VdrDocument } from '@/modules/ma/types/vdr';
import type { DocumentExtraction } from '@/modules/ma/types/document_extraction';
import { IN_PROGRESS_STATUSES } from '@/modules/ma/types/document_extraction';
import { formatFileSize } from '@/modules/ma/utils/format';

interface FileCardProps {
  document: VdrDocument;
  extraction?: DocumentExtraction;
  onDelete: (docId: string) => void;
  onStartExtraction: (docId: string) => void;
  onRetryExtraction: (extractionId: string) => void;
  downloadUrl: string;
}

function getMimeIcon(mimeType: string) {
  if (mimeType === 'application/pdf')
    return <FileText className='h-8 w-8 text-red-400' />;
  if (
    mimeType === 'application/vnd.ms-excel' ||
    mimeType.includes('spreadsheetml')
  )
    return <FileSpreadsheet className='h-8 w-8 text-green-500' />;
  if (
    mimeType === 'application/msword' ||
    mimeType.includes('wordprocessingml')
  )
    return <FileText className='h-8 w-8 text-blue-400' />;
  if (
    mimeType === 'application/vnd.ms-powerpoint' ||
    mimeType.includes('presentationml')
  )
    return <FileText className='h-8 w-8 text-orange-400' />;
  if (mimeType.startsWith('image/'))
    return <FileImage className='h-8 w-8 text-purple-400' />;
  if (mimeType === 'application/zip' || mimeType === 'application/x-zip-compressed')
    return <FileArchive className='h-8 w-8 text-slate-400' />;
  return <File className='h-8 w-8 text-slate-400' />;
}

function ExtractionBadge({
  extraction,
  docId,
  onStartExtraction,
  onRetryExtraction,
}: {
  extraction?: DocumentExtraction;
  docId: string;
  onStartExtraction: (docId: string) => void;
  onRetryExtraction: (extractionId: string) => void;
}) {
  if (!extraction) {
    return (
      <button
        type='button'
        className='rounded p-0.5 text-slate-400 hover:bg-amber-50 hover:text-amber-600'
        title='AI 분석'
        onClick={(e) => {
          e.stopPropagation();
          onStartExtraction(docId);
        }}
      >
        <Sparkles className='h-3.5 w-3.5' />
      </button>
    );
  }
  if (IN_PROGRESS_STATUSES.includes(extraction.status)) {
    return (
      <span className='text-amber-500' title='분석 진행중'>
        <Loader2 className='h-3.5 w-3.5 animate-spin' />
      </span>
    );
  }
  if (extraction.status === 'FAILED') {
    return (
      <button
        type='button'
        className='text-negative hover:text-red-700'
        title={extraction.error_message ?? '분석 실패 — 클릭하여 재시도'}
        onClick={(e) => {
          e.stopPropagation();
          onRetryExtraction(extraction.id);
        }}
      >
        <RefreshCw className='h-3.5 w-3.5' />
      </button>
    );
  }
  return (
    <span className='text-positive' title='분석 완료'>
      <CheckCircle2 className='h-3.5 w-3.5' />
    </span>
  );
}

export default function FileCard({
  document: doc,
  extraction,
  onDelete,
  onStartExtraction,
  onRetryExtraction,
  downloadUrl,
}: FileCardProps) {
  return (
    <div className='group relative flex flex-col items-center gap-1.5 rounded-lg border border-slate-200 bg-white p-3 transition-all hover:border-slate-300 hover:shadow-sm'>
      {/* MIME 아이콘 */}
      <div className='relative mt-1 flex-shrink-0'>
        {getMimeIcon(doc.mime_type)}
      </div>

      {/* 파일명 */}
      <p
        className='line-clamp-2 w-full text-center text-xs font-medium text-slate-700 leading-tight'
        title={doc.original_name}
      >
        {doc.original_name}
      </p>

      {/* 파일 크기 */}
      <p className='text-[10px] text-slate-400'>
        {formatFileSize(doc.file_size_bytes)}
      </p>

      {/* 호버 액션 오버레이 */}
      <div className='absolute inset-0 flex items-end justify-center gap-1 rounded-lg bg-white/90 pb-2 opacity-0 transition-opacity group-hover:opacity-100'>
        <ExtractionBadge
          extraction={extraction}
          docId={doc.id}
          onStartExtraction={onStartExtraction}
          onRetryExtraction={onRetryExtraction}
        />
        <a
          href={downloadUrl}
          className='rounded p-0.5 text-slate-500 hover:bg-slate-100 hover:text-info'
          title='다운로드'
          onClick={(e) => e.stopPropagation()}
        >
          <Download className='h-3.5 w-3.5' />
        </a>
        <button
          type='button'
          className='rounded p-0.5 text-slate-400 hover:bg-red-50 hover:text-negative'
          title='삭제'
          onClick={(e) => {
            e.stopPropagation();
            if (window.confirm('이 문서를 삭제하시겠습니까?'))
              onDelete(doc.id);
          }}
        >
          <Trash2 className='h-3.5 w-3.5' />
        </button>
      </div>
    </div>
  );
}
