import { useState, useRef, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { toast } from "sonner";
import {
  Download,
  RefreshCw,
  ArrowLeft,
  Calendar,
  Building2,
  ClipboardCheck,
  Sparkles,
  Clock,
  BarChart3,
  Upload,
  ShieldCheck,
  AlertTriangle,
} from "lucide-react";
import {
  useDocument,
  useCreateDocument,
  useUploadFinancials,
  useDownloadDocument,
} from "@/modules/im/hooks/useDocuments";
import { useIMRalphSessions } from "@/modules/im/hooks/useIMRalphLoop";
import { useDiagrams } from "@/modules/im/hooks/useDiagrams";
import { DiagramsCard } from "@/modules/im/components/DiagramsCard";
import { DocumentStatusBadge } from "@/modules/im/components/DocumentStatusBadge";
import { ProgressTracker } from "@/modules/im/components/ProgressTracker";
import {
  SECTION_LABEL_MAP,
  IN_PROGRESS_STATUSES,
  DATA_SOURCE_BADGE,
  IM_QUALITY_STATUS_LABELS,
} from "@/modules/im/types/document";
import type { QualityStatus } from "@/modules/im/types/document";
import { RALPH_ACTIVE_STATUSES } from "@/modules/im/types/ralph";
import type { IMRalphSession } from "@/modules/im/types/ralph";
import { formatBytes } from "@/lib/format";
import {
  Button,
  Card,
  Breadcrumbs,
  Skeleton,
  SkeletonCard,
  PageHero,
} from "@/components/ui";
import type { BreadcrumbItem } from "@/components/ui";
import heroImg from "@/assets/images/heroes/forestgp-vc.jpg";

export default function DocumentDetailPage() {
  const { documentId } = useParams<{ documentId: string }>();
  const navigate = useNavigate();
  const { data: doc, isLoading } = useDocument(documentId ?? "");
  const { data: ralphSessions } = useIMRalphSessions(documentId);
  const { data: diagrams, isLoading: diagramsLoading } = useDiagrams(
    documentId ?? "",
  );
  const downloadDocument = useDownloadDocument();
  const createDocument = useCreateDocument();
  const uploadFinancials = useUploadFinancials();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [downloadingFormat, setDownloadingFormat] = useState<
    "pptx" | "pdf" | null
  >(null);
  const mountedRef = useRef(true);
  useEffect(
    () => () => {
      mountedRef.current = false;
    },
    [],
  );

  if (isLoading) {
    return (
      <div
        className="space-y-6"
        role="status"
        aria-label="Loading document details"
      >
        <Skeleton className="h-4 w-48" />
        <div className="flex items-center gap-3">
          <Skeleton className="h-10 w-10 rounded" />
          <div>
            <Skeleton className="h-7 w-64 mb-2" />
            <Skeleton className="h-5 w-20" />
          </div>
        </div>
        <SkeletonCard />
        <SkeletonCard />
        <span className="sr-only">Loading document details...</span>
      </div>
    );
  }

  if (!doc) {
    return (
      <div className="text-center py-12">
        <p className="text-negative">Document not found</p>
        <Button
          variant="ghost"
          className="mt-4"
          onClick={() => navigate("/im")}
        >
          Back to Projects
        </Button>
      </div>
    );
  }

  const isInProgress = IN_PROGRESS_STATUSES.includes(doc.status);

  const breadcrumbs: BreadcrumbItem[] = [
    { label: "IM Projects", href: "/im" },
    { label: doc.project_name || doc.company_name },
  ];

  const handleDownload = async (format: "pptx" | "pdf") => {
    setDownloadingFormat(format);
    try {
      await downloadDocument.mutateAsync({ documentId: doc.id, format });
      if (mountedRef.current)
        toast.success(`${format.toUpperCase()} download started`);
    } catch {
      if (mountedRef.current)
        toast.error(`Failed to download ${format.toUpperCase()}`);
    } finally {
      if (mountedRef.current) setDownloadingFormat(null);
    }
  };

  const handleRegenerate = async () => {
    try {
      const result = await createDocument.mutateAsync({
        company_name: doc.company_name,
        project_name: doc.project_name || doc.company_name,
        corp_code: doc.corp_code ?? undefined,
        data_source: doc.data_source,
        im_style: doc.im_style,
        sections: doc.sections.length > 0 ? doc.sections : undefined,
        industry: doc.industry || undefined,
      });
      toast.success("Regeneration started");
      navigate(`/im/documents/${result.id}`);
    } catch {
      toast.error("Failed to regenerate document");
    }
  };

  const handleRetryUpload = async (file: File) => {
    try {
      await uploadFinancials.mutateAsync({ documentId: doc.id, file });
      toast.success("재무데이터 업로드 성공 — 생성이 시작됩니다");
    } catch {
      toast.error("재무데이터 업로드에 실패했습니다");
    }
  };
  return (
    <div className="space-y-6">
      {/* Breadcrumbs */}
      <Breadcrumbs items={breadcrumbs} />

      {/* Header */}
      <PageHero
        title={doc.project_name || doc.company_name}
        backgroundImage={heroImg}
        backgroundOpacity={0.18}
        compact
        actions={
          <Button
            variant="ghost"
            size="sm"
            icon={ArrowLeft}
            onClick={() => navigate("/im")}
          >
            Back
          </Button>
        }
      />

      <div className="flex items-center gap-3">
        <DocumentStatusBadge
          status={doc.status}
          qualityStatus={doc.quality_status}
        />
        {isInProgress && (
          <span className="text-xs text-text-secondary animate-pulse">
            Auto-refreshing...
          </span>
        )}
      </div>

      {/* Document Info */}
      <Card title="Document Info" headerBar>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-sm">
          <div className="flex items-start gap-2">
            <Building2 className="h-4 w-4 text-text-secondary mt-0.5 flex-shrink-0" />
            <div>
              <span className="text-text-secondary block">Company</span>
              <span className="text-text-dark font-medium">
                {doc.company_name}
              </span>
            </div>
          </div>
          <div>
            <span className="text-text-secondary block">Data Source</span>
            {(() => {
              const b =
                DATA_SOURCE_BADGE[
                  doc.data_source as keyof typeof DATA_SOURCE_BADGE
                ] ?? DATA_SOURCE_BADGE.MANUAL;
              return (
                <span
                  className={`inline-block px-2 py-0.5 text-xs font-medium rounded ${b.cls}`}
                >
                  {b.label}
                </span>
              );
            })()}
          </div>
          {doc.corp_code && (
            <div>
              <span className="text-text-secondary block">Corp Code</span>
              <span className="font-mono text-text-dark">{doc.corp_code}</span>
            </div>
          )}
          <div>
            <span className="text-text-secondary block">IM Style</span>
            <span className="text-text-dark">{doc.im_style}</span>
          </div>
          {doc.industry && (
            <div>
              <span className="text-text-secondary block">Industry</span>
              <span className="text-text-dark">{doc.industry}</span>
            </div>
          )}
          <div className="flex items-start gap-2">
            <Calendar className="h-4 w-4 text-text-secondary mt-0.5 flex-shrink-0" />
            <div>
              <span className="text-text-secondary block">Created</span>
              <span className="text-text-dark">
                {new Date(doc.created_at).toLocaleString()}
              </span>
            </div>
          </div>
        </div>
      </Card>

      {/* Progress Tracker */}
      <Card title="Generation Progress" headerBar>
        <ProgressTracker status={doc.status} progressPct={doc.progress_pct} />
      </Card>

      {/* Ralph Loop Design Quality */}
      {ralphSessions && ralphSessions.length > 0 && (
        <Card title="Design Quality (Ralph Loop)" headerBar>
          <div className="space-y-3">
            {ralphSessions.map((rs: IMRalphSession) => (
              <RalphSessionCard key={rs.id} session={rs} />
            ))}
          </div>
        </Card>
      )}

      {/* Checklist Review Link (VDR 소스만 표시) */}
      {doc.data_source === "VDR" && (
        <Card title="VDR Checklist" headerBar>
          <div className="flex flex-col sm:flex-row items-start sm:items-center gap-4">
            <div className="flex-1">
              <p className="text-sm text-text-dark">
                Review and confirm data extracted from VDR documents.
              </p>
              <p className="text-xs text-text-secondary mt-1">
                All checklist items must be confirmed before generating the
                final IM.
              </p>
            </div>
            <Button
              variant="primary"
              icon={ClipboardCheck}
              onClick={() => navigate(`/im/documents/${doc.id}/checklist`)}
            >
              Review Checklist
            </Button>
          </div>
        </Card>
      )}

      {/* Download Section (Completed) */}
      {(doc.status === "COMPLETED" ||
        doc.status === "QUALITY_CONDITIONAL" ||
        doc.status === "QUALITY_FAILED") && (
        <Card title="Download" headerBar>
          <div className="flex flex-col sm:flex-row items-start sm:items-center gap-4">
            <div className="flex-1">
              <p className="text-sm text-text-dark">
                Your Investment Memorandum is ready for download.
              </p>
              {doc.file_size_bytes && (
                <p className="text-xs text-text-secondary mt-1">
                  File size: {formatBytes(doc.file_size_bytes)}
                </p>
              )}
              {doc.completed_at && (
                <p className="text-xs text-text-secondary">
                  Completed: {new Date(doc.completed_at).toLocaleString()}
                </p>
              )}
              {doc.status === "QUALITY_CONDITIONAL" && (
                <p className="text-xs text-caution mt-1">
                  품질 조건부 통과 문서입니다. 일부 항목을 확인해 주세요.
                </p>
              )}
              {doc.status === "QUALITY_FAILED" && (
                <p className="text-xs text-negative mt-1">
                  품질 검증 미통과 문서입니다. 다운로드는 가능합니다.
                </p>
              )}
            </div>
            <div className="flex gap-3">
              {doc.pptx_path && (
                <Button
                  variant="primary"
                  icon={Download}
                  onClick={() => handleDownload("pptx")}
                  loading={downloadingFormat === "pptx"}
                  disabled={downloadingFormat !== null}
                >
                  PPTX
                </Button>
              )}
              {doc.supported_formats?.includes("pdf") && doc.pdf_path && (
                <Button
                  variant="accent"
                  icon={Download}
                  onClick={() => handleDownload("pdf")}
                  loading={downloadingFormat === "pdf"}
                  disabled={downloadingFormat !== null}
                >
                  PDF
                </Button>
              )}
            </div>
          </div>
        </Card>
      )}

      {/* Quality Gate Results */}
      {(doc.status === "COMPLETED" ||
        doc.status === "QUALITY_CONDITIONAL" ||
        doc.status === "QUALITY_FAILED") &&
        doc.quality_status && (
          <Card title="품질 검증" headerBar>
            <div className="space-y-4">
              <div className="flex items-center gap-4">
                <ShieldCheck className="h-5 w-5 text-text-secondary flex-shrink-0" />
                <div className="flex items-center gap-3">
                  <span className="text-sm text-text-secondary">품질 점수</span>
                  {doc.quality_score != null && (
                    <span
                      className={`text-lg font-bold ${
                        doc.quality_score >= 3.5
                          ? "text-accent"
                          : doc.quality_score >= 2.5
                            ? "text-caution"
                            : "text-negative"
                      }`}
                    >
                      {doc.quality_score.toFixed(1)}/5.0
                    </span>
                  )}
                  <span className="text-sm text-text-secondary">
                    {IM_QUALITY_STATUS_LABELS[
                      doc.quality_status as QualityStatus
                    ] ?? doc.quality_status}
                  </span>
                </div>
              </div>
              {doc.quality_issues && doc.quality_issues.length > 0 && (
                <div className="space-y-1.5">
                  <div className="flex items-center gap-1.5 text-xs text-text-secondary">
                    <AlertTriangle className="h-3.5 w-3.5" />
                    <span>검출 이슈 ({doc.quality_issues.length}건)</span>
                  </div>
                  <ul className="space-y-1 text-xs text-text-secondary pl-5 list-disc">
                    {doc.quality_issues.slice(0, 10).map((issue, i) => (
                      <li key={i}>{issue}</li>
                    ))}
                    {doc.quality_issues.length > 10 && (
                      <li className="text-text-muted">
                        외 {doc.quality_issues.length - 10}건
                      </li>
                    )}
                  </ul>
                </div>
              )}
            </div>
          </Card>
        )}

      {/* Generation Metrics */}
      {(doc.status === "COMPLETED" ||
        doc.status === "QUALITY_CONDITIONAL" ||
        doc.status === "QUALITY_FAILED") &&
        doc.stage_details && (
          <Card title="Generation Metrics" headerBar>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-sm">
              {(doc.stage_details.render_ms ??
                doc.stage_details.generation_ms) != null && (
                <div className="flex items-start gap-2">
                  <Clock className="h-4 w-4 text-text-secondary mt-0.5 flex-shrink-0" />
                  <div>
                    <span className="text-text-secondary block">렌더링</span>
                    <span className="text-text-dark font-medium">
                      {(() => {
                        const ms =
                          doc.stage_details!.render_ms ??
                          doc.stage_details!.generation_ms;
                        return ms >= 1000
                          ? `${(ms / 1000).toFixed(1)}s`
                          : `${ms}ms`;
                      })()}
                    </span>
                  </div>
                </div>
              )}
              {doc.stage_details.gate_ms != null && (
                <div className="flex items-start gap-2">
                  <ShieldCheck className="h-4 w-4 text-text-secondary mt-0.5 flex-shrink-0" />
                  <div>
                    <span className="text-text-secondary block">
                      품질 게이트
                    </span>
                    <span className="text-text-dark font-medium">
                      {doc.stage_details.gate_ms >= 1000
                        ? `${(doc.stage_details.gate_ms / 1000).toFixed(1)}s`
                        : `${doc.stage_details.gate_ms}ms`}
                    </span>
                  </div>
                </div>
              )}
              {doc.stage_details.total_ms != null && (
                <div className="flex items-start gap-2">
                  <Clock className="h-4 w-4 text-text-secondary mt-0.5 flex-shrink-0" />
                  <div>
                    <span className="text-text-secondary block">전체 소요</span>
                    <span className="text-text-dark font-medium">
                      {doc.stage_details.total_ms >= 1000
                        ? `${(doc.stage_details.total_ms / 1000).toFixed(1)}s`
                        : `${doc.stage_details.total_ms}ms`}
                    </span>
                  </div>
                </div>
              )}
              {doc.stage_details.slide_count != null && (
                <div className="flex items-start gap-2">
                  <BarChart3 className="h-4 w-4 text-text-secondary mt-0.5 flex-shrink-0" />
                  <div>
                    <span className="text-text-secondary block">슬라이드</span>
                    <span className="text-text-dark font-medium">
                      {doc.stage_details.slide_count}장
                    </span>
                  </div>
                </div>
              )}
              {doc.stage_details.file_size_bytes != null && (
                <div>
                  <span className="text-text-secondary block">파일 크기</span>
                  <span className="text-text-dark font-medium">
                    {formatBytes(doc.stage_details.file_size_bytes)}
                  </span>
                </div>
              )}
              {doc.stage_details.sections_rendered != null && (
                <div>
                  <span className="text-text-secondary block">렌더링 섹션</span>
                  <span className="text-text-dark font-medium">
                    {doc.stage_details.sections_rendered}
                    {doc.stage_details.sections_failed > 0 && (
                      <span className="text-negative ml-1">
                        ({doc.stage_details.sections_failed} 실패)
                      </span>
                    )}
                  </span>
                </div>
              )}
            </div>
          </Card>
        )}

      {/* Awaiting Upload (Excel 재업로드) */}
      {doc.status === "AWAITING_UPLOAD" && (
        <Card title="재무데이터 업로드" headerBar>
          <div className="flex flex-col sm:flex-row items-start sm:items-center gap-4">
            <div className="flex-1">
              <p className="text-sm text-caution font-medium">
                재무데이터 업로드가 필요합니다.
              </p>
              <p className="text-xs text-text-secondary mt-1">
                Excel 파일을 업로드하면 IM 생성이 자동으로 시작됩니다.
              </p>
            </div>
            <div>
              <input
                ref={fileInputRef}
                type="file"
                accept=".xlsx,.xls"
                className="hidden"
                onChange={(e) => {
                  const file = e.target.files?.[0];
                  if (file) handleRetryUpload(file);
                }}
              />
              <Button
                variant="primary"
                icon={Upload}
                onClick={() => fileInputRef.current?.click()}
                loading={uploadFinancials.isPending}
              >
                Excel 업로드
              </Button>
            </div>
          </div>
        </Card>
      )}

      {/* Error Section (Failed) */}
      {doc.status === "FAILED" && (
        <Card title="Error" headerBar>
          <div className="flex flex-col sm:flex-row items-start sm:items-center gap-4">
            <div className="flex-1">
              <p className="text-sm text-negative font-medium">
                Document generation failed.
              </p>
              <p className="text-xs text-text-secondary mt-1">
                You can try regenerating the document with the same settings.
              </p>
            </div>
            <Button
              variant="primary"
              icon={RefreshCw}
              onClick={handleRegenerate}
              loading={createDocument.isPending}
            >
              Regenerate
            </Button>
          </div>
        </Card>
      )}

      {/* Sections */}
      {doc.sections.length > 0 && (
        <Card title="Sections" headerBar>
          <div className="flex flex-wrap gap-2">
            {doc.sections.map((section) => (
              <span
                key={section}
                className="px-3 py-1 text-sm rounded-lg bg-bg-cool text-text-secondary"
              >
                {SECTION_LABEL_MAP[section] ?? section}
              </span>
            ))}
          </div>
        </Card>
      )}

      {/* Diagrams (Excalidraw) */}
      {(doc.status === "COMPLETED" ||
        doc.status === "QUALITY_CONDITIONAL" ||
        doc.status === "QUALITY_FAILED") && (
        <DiagramsCard
          documentId={doc.id}
          diagrams={diagrams ?? []}
          isLoading={diagramsLoading}
        />
      )}
    </div>
  );
}

function RalphSessionCard({ session }: { session: IMRalphSession }) {
  const isActive = RALPH_ACTIVE_STATUSES.includes(session.status);
  const passLabel = session.pass_number === 1 ? "Draft" : "Final";

  const scoreColor =
    session.final_score >= 4.0
      ? "text-accent"
      : session.final_score >= 3.0
        ? "text-caution"
        : "text-negative";

  return (
    <div className="flex items-center gap-4 p-3 rounded-lg bg-bg-cool">
      <div className="flex items-center gap-2 flex-shrink-0">
        <Sparkles className="h-4 w-4 text-accent" />
        <span className="text-sm font-medium text-text-dark">
          Pass {session.pass_number} ({passLabel})
        </span>
      </div>

      <div className="flex-1 flex items-center gap-4">
        {isActive ? (
          <span className="text-xs text-accent animate-pulse">
            Improving design quality...
          </span>
        ) : session.status === "COMPLETED" ? (
          <>
            <span className={`text-sm font-bold ${scoreColor}`}>
              {session.final_score.toFixed(1)}/5.0
            </span>
            <span className="text-xs text-text-secondary">
              {session.total_iterations} iteration
              {session.total_iterations !== 1 ? "s" : ""}
              {" · "}${session.total_cost_usd.toFixed(3)}
            </span>
          </>
        ) : session.status === "FAILED" ? (
          <span className="text-xs text-negative">
            Quality check failed
            {session.error_message
              ? `: ${session.error_message.slice(0, 60)}`
              : ""}
          </span>
        ) : (
          <span className="text-xs text-text-secondary">{session.status}</span>
        )}
      </div>

      {session.critical_flags && session.critical_flags.length > 0 && (
        <span className="text-xs text-negative font-medium">
          {session.critical_flags.length} flag
          {session.critical_flags.length !== 1 ? "s" : ""}
        </span>
      )}
    </div>
  );
}
