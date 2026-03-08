import { useState } from "react";
import {
  Download,
  Trash2,
  FileText,
  Clock,
  Loader2,
  AlertCircle,
  Plus,
} from "lucide-react";
import { Badge, Button, Card, EmptyState, SlidePanel } from "@/components/ui";
import type { DocumentRevision } from "@/modules/ma/types/document_version";
import {
  useDocumentRevisions,
  useDeleteRevision,
  getRevisionDownloadUrl,
} from "@/modules/ma/hooks/useDocumentVersions";
import { formatFileSize } from "@/modules/ma/utils/format";
import RevisionUploadDialog from "./RevisionUploadDialog";

const UPLOAD_SOURCE_LABELS: Record<string, string> = {
  MANUAL: "수동",
  CONTRACT_MARKUP: "계약 마크업",
  NDA_MARKUP: "NDA 마크업",
  RFI_IMPORT: "RFI 가져오기",
  SYSTEM: "시스템",
};

interface DocumentVersionPanelProps {
  open: boolean;
  onClose: () => void;
  txnId: string;
  docId: string;
  docName: string;
  canWrite: boolean;
}

export default function DocumentVersionPanel({
  open,
  onClose,
  txnId,
  docId,
  docName,
  canWrite,
}: DocumentVersionPanelProps) {
  const { data, isLoading, isError } = useDocumentRevisions(txnId, docId);
  const deleteRevision = useDeleteRevision(txnId, docId);
  const revisions = data?.items ?? [];

  const [uploadOpen, setUploadOpen] = useState(false);

  return (
    <SlidePanel
      open={open}
      onClose={onClose}
      title="문서 버전 이력"
      subtitle={docName}
      width="lg"
    >
      <div className="space-y-6">
        {/* 업로드 버튼 */}
        {canWrite && (
          <div className="flex justify-end">
            <Button icon={Plus} onClick={() => setUploadOpen(true)}>
              새 버전 업로드
            </Button>
          </div>
        )}

        {/* 리비전 타임라인 */}
        {isLoading ? (
          <div className="flex items-center justify-center py-12 text-text-muted">
            <Loader2 className="h-5 w-5 animate-spin mr-2" />
            버전 목록 불러오는 중…
          </div>
        ) : isError ? (
          <div className="flex items-center justify-center py-12 text-red-500">
            <AlertCircle className="h-5 w-5 mr-2" />
            버전 목록을 불러올 수 없습니다.
          </div>
        ) : revisions.length === 0 ? (
          <EmptyState
            icon={FileText}
            title="리비전이 없습니다"
            description="파일을 업로드하여 버전 관리를 시작하세요."
          />
        ) : (
          <RevisionTimeline
            txnId={txnId}
            docId={docId}
            revisions={revisions}
            canWrite={canWrite}
            onDelete={(id) => {
              if (confirm("이 리비전을 삭제하시겠습니까?")) {
                deleteRevision.mutate(id);
              }
            }}
          />
        )}

        {/* 업로드 다이얼로그 */}
        {uploadOpen && (
          <RevisionUploadDialog
            open={uploadOpen}
            onClose={() => setUploadOpen(false)}
            txnId={txnId}
            docId={docId}
          />
        )}
      </div>
    </SlidePanel>
  );
}

/* ── 리비전 타임라인 ──────────────────────────── */

function RevisionTimeline({
  txnId,
  docId,
  revisions,
  canWrite,
  onDelete,
}: {
  txnId: string;
  docId: string;
  revisions: DocumentRevision[];
  canWrite: boolean;
  onDelete: (id: string) => void;
}) {
  const sorted = [...revisions].sort(
    (a, b) => b.revision_number - a.revision_number,
  );

  return (
    <div className="relative">
      {sorted.length > 1 && (
        <div className="absolute left-4 top-6 bottom-6 w-0.5 bg-gray-200" />
      )}
      <div className="space-y-3">
        {sorted.map((r) => (
          <div key={r.id} className="relative flex items-start gap-3 pl-2">
            <div
              className={`relative z-10 flex h-8 w-8 shrink-0 items-center justify-center rounded-full border-2 bg-white text-xs font-semibold ${
                r.is_current
                  ? "border-primary-500 text-primary-600"
                  : "border-gray-300 text-gray-400"
              }`}
            >
              {r.revision_number}
            </div>
            <Card className="flex-1 p-3">
              {/* 헤더 */}
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="text-sm font-semibold text-text-dark">
                    v{r.revision_number}
                  </span>
                  {r.is_current && <Badge variant="success">현재</Badge>}
                  <Badge variant="neutral">
                    {UPLOAD_SOURCE_LABELS[r.upload_source] ?? r.upload_source}
                  </Badge>
                </div>
                <div className="flex items-center gap-1.5 shrink-0">
                  <a
                    href={getRevisionDownloadUrl(txnId, docId, r.id)}
                    className="text-primary-600 hover:text-primary-700"
                    aria-label={`v${r.revision_number} 다운로드`}
                  >
                    <Download className="h-4 w-4" />
                  </a>
                  {canWrite && (
                    <button
                      type="button"
                      className="text-red-400 hover:text-red-600"
                      aria-label={`v${r.revision_number} 삭제`}
                      onClick={() => onDelete(r.id)}
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  )}
                </div>
              </div>

              {/* 메타 */}
              <div className="flex items-center gap-3 mt-1 text-xs text-text-muted flex-wrap">
                <span>{r.file_name}</span>
                <span>{formatFileSize(r.file_size_bytes)}</span>
                <span className="flex items-center gap-0.5">
                  <Clock className="h-3 w-3" />
                  {new Date(r.created_at).toLocaleDateString("ko-KR")}
                </span>
                {r.uploaded_by_email && <span>{r.uploaded_by_email}</span>}
              </div>

              {/* 변경 요약 */}
              {r.changes_summary && (
                <p className="text-xs text-text-secondary mt-1.5">
                  {r.changes_summary}
                </p>
              )}
            </Card>
          </div>
        ))}
      </div>
    </div>
  );
}
