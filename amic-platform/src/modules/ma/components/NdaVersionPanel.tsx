import { useState, useRef, useId } from "react";
import {
  Upload,
  Download,
  Trash2,
  FileText,
  Clock,
  Sparkles,
  Loader2,
  AlertCircle,
} from "lucide-react";
import {
  Badge,
  Button,
  Card,
  EmptyState,
  Input,
  Select,
  SlidePanel,
} from "@/components/ui";
import type { NdaMarkup } from "@/modules/ma/types/nda_markup";
import {
  useNdaMarkups,
  useCreateNdaMarkup,
  useDeleteNdaMarkup,
  useGenerateNdaRedline,
  getNdaMarkupDownloadUrl,
} from "@/modules/ma/hooks/useNdaMarkups";
import { formatFileSize } from "@/modules/ma/utils/format";

const MARKUP_TYPE_OPTIONS = [
  { value: "draft", label: "초안" },
  { value: "1st", label: "1차 마크업" },
  { value: "2nd", label: "2차 마크업" },
  { value: "final", label: "최종본" },
];

const SOURCE_PARTY_OPTIONS = [
  { value: "매도인측", label: "매도인측" },
  { value: "매수인측", label: "매수인측" },
  { value: "법무법인", label: "법무법인" },
];

function getLocalDateString(): string {
  const now = new Date();
  const y = now.getFullYear();
  const m = String(now.getMonth() + 1).padStart(2, "0");
  const d = String(now.getDate()).padStart(2, "0");
  return `${y}-${m}-${d}`;
}

interface NdaVersionPanelProps {
  open: boolean;
  onClose: () => void;
  txnId: string;
  ndaId: string;
  ndaLabel: string;
  canWrite: boolean;
}

export default function NdaVersionPanel({
  open,
  onClose,
  txnId,
  ndaId,
  ndaLabel,
  canWrite,
}: NdaVersionPanelProps) {
  const { data, isLoading, isError } = useNdaMarkups(txnId, ndaId);
  const createMarkup = useCreateNdaMarkup(txnId, ndaId);
  const deleteMarkup = useDeleteNdaMarkup(txnId, ndaId);
  const generateRedline = useGenerateNdaRedline(txnId, ndaId);
  const markups = data?.items ?? [];

  return (
    <SlidePanel
      open={open}
      onClose={onClose}
      title="NDA 버전 관리"
      subtitle={ndaLabel}
      width="lg"
    >
      <div className="space-y-6">
        {/* 업로드 폼 */}
        {canWrite && (
          <UploadForm
            markupsCount={markups.length}
            onUpload={(fd, onSuccess) =>
              createMarkup.mutate(fd, { onSuccess })
            }
            isUploading={createMarkup.isPending}
          />
        )}

        {/* 버전 타임라인 */}
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
        ) : markups.length === 0 ? (
          <EmptyState
            icon={FileText}
            title="마크업 버전이 없습니다"
            description="NDA 파일을 업로드하여 버전 관리를 시작하세요."
          />
        ) : (
          <VersionTimeline
            txnId={txnId}
            ndaId={ndaId}
            markups={markups}
            canWrite={canWrite}
            onDelete={(id) => {
              if (confirm("이 버전을 삭제하시겠습니까?")) {
                deleteMarkup.mutate(id);
              }
            }}
            onGenerateRedline={(markupId) =>
              generateRedline.mutate({ markupId })
            }
            isGenerating={generateRedline.isPending}
          />
        )}
      </div>
    </SlidePanel>
  );
}

/* ── 업로드 폼 ─────────────────────────────────── */

function UploadForm({
  markupsCount,
  onUpload,
  isUploading,
}: {
  markupsCount: number;
  onUpload: (fd: FormData, onSuccess: () => void) => void;
  isUploading: boolean;
}) {
  const fileRef = useRef<HTMLInputElement>(null);
  const fileInputId = useId();
  const [versionLabel, setVersionLabel] = useState("");
  const [versionDate, setVersionDate] = useState(getLocalDateString);
  const [sourceParty, setSourceParty] = useState("");
  const [markupType, setMarkupType] = useState("");
  const [changesSummary, setChangesSummary] = useState("");

  const resetForm = () => {
    setVersionLabel("");
    setChangesSummary("");
    if (fileRef.current) fileRef.current.value = "";
  };

  const handleSubmit = () => {
    const file = fileRef.current?.files?.[0];
    if (!file) return;
    const fd = new FormData();
    fd.append("file", file);
    fd.append("version_label", versionLabel.trim() || `v${markupsCount + 1}`);
    fd.append("version_date", versionDate);
    if (sourceParty) fd.append("source_party", sourceParty);
    if (markupType) fd.append("markup_type", markupType);
    if (changesSummary.trim())
      fd.append("changes_summary", changesSummary.trim());

    onUpload(fd, resetForm);
  };

  return (
    <Card className="p-4 border-dashed">
      <p className="text-sm font-medium text-text-dark mb-3">새 버전 업로드</p>
      <div className="grid grid-cols-2 gap-3">
        <Input
          label="버전 라벨"
          value={versionLabel}
          onChange={(e) => setVersionLabel(e.target.value)}
          placeholder={`v${markupsCount + 1}`}
        />
        <Input
          label="버전 일자"
          type="date"
          value={versionDate}
          onChange={(e) => setVersionDate(e.target.value)}
        />
        <Select
          label="작성 측"
          options={[{ value: "", label: "선택" }, ...SOURCE_PARTY_OPTIONS]}
          value={sourceParty}
          onChange={(e) => setSourceParty(e.target.value)}
        />
        <Select
          label="마크업 유형"
          options={[{ value: "", label: "선택" }, ...MARKUP_TYPE_OPTIONS]}
          value={markupType}
          onChange={(e) => setMarkupType(e.target.value)}
        />
      </div>
      <div className="mt-3">
        <Input
          label="변경 요약"
          value={changesSummary}
          onChange={(e) => setChangesSummary(e.target.value)}
          placeholder="주요 변경 사항을 간략히 기재"
        />
      </div>
      <div className="flex items-end gap-3 mt-3">
        <div className="flex-1">
          <label
            htmlFor={fileInputId}
            className="block text-xs text-text-secondary mb-1"
          >
            파일
          </label>
          <input
            id={fileInputId}
            ref={fileRef}
            type="file"
            accept=".docx,.doc,.pdf,.hwp,.hwpx,.xlsx,.xls,.pptx,.ppt,.txt"
            className="w-full text-sm"
          />
        </div>
        <Button
          icon={Upload}
          onClick={handleSubmit}
          disabled={isUploading}
          loading={isUploading}
        >
          업로드
        </Button>
      </div>
    </Card>
  );
}

/* ── 버전 타임라인 ─────────────────────────────── */

function VersionTimeline({
  txnId,
  ndaId,
  markups,
  canWrite,
  onDelete,
  onGenerateRedline,
  isGenerating,
}: {
  txnId: string;
  ndaId: string;
  markups: NdaMarkup[];
  canWrite: boolean;
  onDelete: (id: string) => void;
  onGenerateRedline: (id: string) => void;
  isGenerating: boolean;
}) {
  const sorted = [...markups].sort(
    (a, b) => b.version_number - a.version_number,
  );

  return (
    <div className="relative">
      {sorted.length > 1 && (
        <div className="absolute left-4 top-6 bottom-6 w-0.5 bg-gray-200" />
      )}
      <div className="space-y-3">
        {sorted.map((m) => (
          <div key={m.id} className="relative flex items-start gap-3 pl-2">
            <div className="relative z-10 flex h-8 w-8 shrink-0 items-center justify-center rounded-full border-2 border-primary-300 bg-white text-xs font-semibold text-primary-600">
              {m.version_number}
            </div>
            <Card className="flex-1 p-3">
              {/* 헤더 */}
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="text-sm font-semibold text-text-dark">
                    {m.version_label}
                  </span>
                  <Badge variant="neutral">{m.version_date}</Badge>
                  {m.source_party && (
                    <Badge variant="info">{m.source_party}</Badge>
                  )}
                  {m.markup_type && (
                    <Badge variant="neutral">
                      {MARKUP_TYPE_OPTIONS.find(
                        (o) => o.value === m.markup_type,
                      )?.label ?? m.markup_type}
                    </Badge>
                  )}
                </div>
                <div className="flex items-center gap-1.5 shrink-0">
                  {m.has_file && (
                    <a
                      href={getNdaMarkupDownloadUrl(txnId, ndaId, m.id)}
                      className="text-primary-600 hover:text-primary-700"
                      aria-label={`${m.version_label} 다운로드`}
                    >
                      <Download className="h-4 w-4" />
                    </a>
                  )}
                  {canWrite && m.version_number > 1 && (
                    <button
                      type="button"
                      className="text-accent hover:text-accent/80 disabled:opacity-50"
                      aria-label={`${m.version_label} Redline 생성`}
                      onClick={() => onGenerateRedline(m.id)}
                      disabled={isGenerating}
                    >
                      <Sparkles className="h-4 w-4" />
                    </button>
                  )}
                  {canWrite && (
                    <button
                      type="button"
                      className="text-red-400 hover:text-red-600"
                      aria-label={`${m.version_label} 삭제`}
                      onClick={() => onDelete(m.id)}
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  )}
                </div>
              </div>

              {/* 메타 */}
              <div className="flex items-center gap-3 mt-1 text-xs text-text-muted">
                {m.file_name && <span>{m.file_name}</span>}
                {m.file_size_bytes != null && (
                  <span>{formatFileSize(m.file_size_bytes)}</span>
                )}
                <span className="flex items-center gap-0.5">
                  <Clock className="h-3 w-3" />
                  {new Date(m.created_at).toLocaleDateString("ko-KR")}
                </span>
                {m.redline_issues_count != null && (
                  <Badge variant="warning">
                    Redline {m.redline_issues_count}건
                  </Badge>
                )}
              </div>

              {/* 변경 요약 */}
              {m.changes_summary && (
                <p className="text-xs text-text-secondary mt-1.5">
                  {m.changes_summary}
                </p>
              )}
            </Card>
          </div>
        ))}
      </div>
    </div>
  );
}
