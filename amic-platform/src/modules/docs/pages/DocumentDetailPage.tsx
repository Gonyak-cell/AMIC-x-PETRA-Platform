import { useState, useRef, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { toast } from "sonner";
import {
  Download,
  RefreshCw,
  ArrowLeft,
  Calendar,
  Building2,
  Trash2,
} from "lucide-react";
import { useDocument, useCreateDocument, useDownloadDocument, useDeleteDocument } from "@/modules/docs/hooks/useDocuments";
import { DocumentStatusBadge } from "@/modules/docs/components/DocumentStatusBadge";
import { ProgressTracker } from "@/modules/docs/components/ProgressTracker";
import { SECTION_LABEL_MAP, IN_PROGRESS_STATUSES, getDocumentType } from "@/modules/docs/types/document";
import { formatBytes } from "@/lib/format";
import { Button, Card, Breadcrumbs, Skeleton, SkeletonCard, PageHero } from "@/components/ui";
import type { BreadcrumbItem } from "@/components/ui";
import heroImg from "@/assets/images/heroes/forestgp-forest.jpg";

export default function DocumentDetailPage() {
  const { documentId } = useParams<{ documentId: string }>();
  const navigate = useNavigate();
  const { data: doc, isLoading } = useDocument(documentId ?? "");
  const downloadDocument = useDownloadDocument();
  const createDocument = useCreateDocument();
  const deleteDocument = useDeleteDocument();
  const [downloadingFormat, setDownloadingFormat] = useState<"pptx" | "pdf" | null>(null);
  const mountedRef = useRef(true);
  useEffect(() => () => { mountedRef.current = false; }, []);

  if (isLoading) {
    return (
      <div className="space-y-6" role="status" aria-label="Loading document details">
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
        <Button variant="ghost" className="mt-4" onClick={() => navigate("/docs")}>
          Back to Documents
        </Button>
      </div>
    );
  }

  const isInProgress = IN_PROGRESS_STATUSES.includes(doc.status);
  const docType = getDocumentType(doc.im_style);
  const typeLabel = docType === "teaser" ? "TM" : "IM";

  const breadcrumbs: BreadcrumbItem[] = [
    { label: "Deal Document Studio", href: "/docs" },
    { label: doc.project_name || doc.company_name },
  ];

  const handleDownload = async (format: "pptx" | "pdf") => {
    setDownloadingFormat(format);
    try {
      await downloadDocument.mutateAsync({ documentId: doc.id, format });
      if (mountedRef.current) toast.success(`${format.toUpperCase()} download started`);
    } catch {
      if (mountedRef.current) toast.error(`Failed to download ${format.toUpperCase()}`);
    } finally {
      if (mountedRef.current) setDownloadingFormat(null);
    }
  };

  const handleDelete = async () => {
    if (!doc) return;
    if (!window.confirm(`"${doc.project_name || doc.company_name}" 문서를 삭제하시겠습니까?`)) return;
    try {
      await deleteDocument.mutateAsync(doc.id);
      navigate("/docs");
    } catch {
      // toast is shown by the hook
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
      navigate(`/docs/documents/${result.id}`);
    } catch {
      toast.error("Failed to regenerate document");
    }
  };

  return (
    <div className="space-y-6">
      <Breadcrumbs items={breadcrumbs} />

      <PageHero
        title={doc.project_name || doc.company_name}
        backgroundImage={heroImg}
        backgroundOpacity={0.18}
        compact
        actions={
          <div className="flex gap-2">
            <Button
              variant="ghost"
              size="sm"
              icon={ArrowLeft}
              onClick={() => navigate("/docs")}
            >
              Back
            </Button>
            {!isInProgress && (
              <Button
                variant="ghost"
                size="sm"
                icon={Trash2}
                onClick={handleDelete}
                loading={deleteDocument.isPending}
                className="text-negative hover:text-negative"
              >
                Delete
              </Button>
            )}
          </div>
        }
      />

      <div className="flex items-center gap-3">
        <span
          className={`inline-block px-2 py-0.5 text-xs font-medium rounded ${
            docType === "teaser"
              ? "bg-violet-100 text-violet-700"
              : "bg-info-light text-info"
          }`}
        >
          {typeLabel}
        </span>
        <DocumentStatusBadge status={doc.status} />
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
              <span className="text-text-dark font-medium">{doc.company_name}</span>
            </div>
          </div>
          <div>
            <span className="text-text-secondary block">Data Source</span>
            <span className="text-text-dark">{doc.data_source}</span>
          </div>
          {doc.corp_code && (
            <div>
              <span className="text-text-secondary block">Corp Code</span>
              <span className="font-mono text-text-dark">{doc.corp_code}</span>
            </div>
          )}
          <div>
            <span className="text-text-secondary block">Style</span>
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

      {/* Download Section */}
      {doc.status === "COMPLETED" && (
        <Card title="Download" headerBar>
          <div className="flex flex-col sm:flex-row items-start sm:items-center gap-4">
            <div className="flex-1">
              <p className="text-sm text-text-dark">
                Your {typeLabel} is ready for download.
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
              {doc.pdf_path && (
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

      {/* Error Section */}
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
    </div>
  );
}
