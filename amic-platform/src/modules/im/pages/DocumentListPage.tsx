import { useMemo, useState, useRef } from "react";
import { useNavigate } from "react-router-dom";
import {
  FileText,
  Plus,
  CheckCircle,
  Loader2,
  AlertTriangle,
  ShieldAlert,
  ChevronLeft,
  ChevronRight,
  FolderOpen,
} from "lucide-react";
import { useDocuments } from "@/modules/im/hooks/useDocuments";
import { DocumentStatusBadge } from "@/modules/im/components/DocumentStatusBadge";
import {
  Button,
  Card,
  DataTable,
  KpiCard,
  EmptyState,
  PageHero,
} from "@/components/ui";
import type { Column } from "@/components/ui";
import type { Document, DocumentStatus } from "@/modules/im/types/document";
import { DATA_SOURCE_BADGE } from "@/modules/im/types/document";
import { IN_PROGRESS_STATUSES } from "@/modules/im/types/document";
import { useScrollReveal } from "@/hooks/useScrollReveal";
import heroImg from "@/assets/images/heroes/hero-arch-wave.jpg";

type StatusFilter = "ALL" | "IN_PROGRESS" | DocumentStatus;

const columns: Column<Document>[] = [
  {
    key: "project_name",
    header: "Project",
    render: (row) => (
      <span className="font-medium text-text-dark">
        {row.project_name || row.company_name}
      </span>
    ),
  },
  {
    key: "company_name",
    header: "Company",
    render: (row) => row.company_name,
  },
  {
    key: "data_source",
    header: "Source",
    align: "center",
    width: "100px",
    render: (row) => {
      const b = DATA_SOURCE_BADGE[row.data_source] ?? DATA_SOURCE_BADGE.MANUAL;
      return (
        <span
          className={`inline-block px-2 py-0.5 text-xs font-medium rounded ${b.cls}`}
        >
          {b.label}
        </span>
      );
    },
  },
  {
    key: "im_style",
    header: "Style",
    align: "center",
    width: "100px",
    render: (row) => row.im_style,
  },
  {
    key: "status",
    header: "Status",
    align: "center",
    width: "120px",
    render: (row) => <DocumentStatusBadge status={row.status} />,
  },
  {
    key: "progress_pct",
    header: "Progress",
    align: "center",
    width: "100px",
    render: (row) => (
      <span className="text-sm text-text-secondary">{row.progress_pct}%</span>
    ),
  },
  {
    key: "created_at",
    header: "Created",
    width: "140px",
    render: (row) => new Date(row.created_at).toLocaleDateString(),
  },
];

const PAGE_SIZE = 20;

export default function DocumentListPage() {
  const navigate = useNavigate();
  const [page, setPage] = useState(0);
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("ALL");
  const kpiRef = useRef<HTMLDivElement>(null);
  useScrollReveal(kpiRef, { stagger: 0.06, y: 20 });
  const { data, isLoading, isError } = useDocuments({
    offset: page * PAGE_SIZE,
    limit: PAGE_SIZE,
  });

  const total = data?.total ?? 0;
  const totalPages = Math.ceil(total / PAGE_SIZE);
  const items = useMemo(() => data?.items ?? [], [data?.items]);

  const filteredItems = useMemo(() => {
    if (statusFilter === "ALL") return items;
    if (statusFilter === "IN_PROGRESS")
      return items.filter((d) => IN_PROGRESS_STATUSES.includes(d.status));
    if (statusFilter === "COMPLETED")
      return items.filter(
        (d) => d.status === "COMPLETED" || d.status === "QUALITY_CONDITIONAL",
      );
    return items.filter((d) => d.status === statusFilter);
  }, [items, statusFilter]);

  const kpis = useMemo(
    () => ({
      total: data?.total ?? 0,
      inProgress: items.filter((d) => IN_PROGRESS_STATUSES.includes(d.status))
        .length,
      completed: items.filter(
        (d) => d.status === "COMPLETED" || d.status === "QUALITY_CONDITIONAL",
      ).length,
      qualityFailed: items.filter((d) => d.status === "QUALITY_FAILED").length,
      failed: items.filter((d) => d.status === "FAILED").length,
    }),
    [data?.total, items],
  );

  return (
    <div className="space-y-6">
      {/* Header */}
      <PageHero
        title="IM Projects"
        subtitle="Investment Memorandum generation and management"
        backgroundImage={heroImg}
        backgroundOpacity={0.18}
        compact
        actions={
          <div className="flex gap-2">
            <Button
              variant="secondary"
              icon={FolderOpen}
              onClick={() => navigate("/im/new/vdr")}
            >
              From VDR
            </Button>
            <Button
              variant="accent"
              icon={Plus}
              onClick={() => navigate("/im/new")}
            >
              New IM
            </Button>
          </div>
        }
      />

      {/* KPI Cards */}
      <div
        ref={kpiRef}
        className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4"
      >
        <KpiCard label="Total" value={String(kpis.total)} icon={FileText} />
        <KpiCard
          label="In Progress"
          value={String(kpis.inProgress)}
          icon={Loader2}
          variant="caution"
        />
        <KpiCard
          label="Completed"
          value={String(kpis.completed)}
          icon={CheckCircle}
          variant="positive"
        />
        <KpiCard
          label="Quality Failed"
          value={String(kpis.qualityFailed)}
          icon={ShieldAlert}
          variant="warning"
        />
        <KpiCard
          label="Failed"
          value={String(kpis.failed)}
          icon={AlertTriangle}
          variant="negative"
        />
      </div>

      {/* Status Filters */}
      <div className="flex gap-2">
        {(
          [
            "ALL",
            "IN_PROGRESS",
            "COMPLETED",
            "QUALITY_FAILED",
            "FAILED",
          ] as const
        ).map((s) => (
          <Button
            key={s}
            variant={statusFilter === s ? "accent" : "ghost"}
            size="sm"
            onClick={() => {
              setStatusFilter(s);
              setPage(0);
            }}
          >
            {s === "ALL"
              ? "All"
              : s === "IN_PROGRESS"
                ? "In Progress"
                : s === "QUALITY_FAILED"
                  ? "품질 미통과"
                  : s.charAt(0) + s.slice(1).toLowerCase()}
          </Button>
        ))}
      </div>

      {/* Table */}
      <Card title="All Projects" headerBar padding="none">
        {isError ? (
          <EmptyState
            icon={AlertTriangle}
            title="Failed to load projects"
            description="Could not fetch IM projects. Please try again later."
          />
        ) : !isLoading && filteredItems.length === 0 ? (
          <EmptyState
            icon={FileText}
            title={
              statusFilter === "ALL"
                ? "No IM projects yet"
                : "No matching projects"
            }
            description={
              statusFilter === "ALL"
                ? "Create your first Investment Memorandum to get started."
                : "No projects match the selected status filter."
            }
            actionLabel={statusFilter === "ALL" ? "Create IM" : undefined}
            onAction={
              statusFilter === "ALL" ? () => navigate("/im/new") : undefined
            }
          />
        ) : (
          <>
            <DataTable
              columns={columns}
              data={filteredItems}
              keyField="id"
              loading={isLoading}
              onRowClick={(row) => navigate(`/im/documents/${row.id}`)}
              striped
            />
            {totalPages > 1 && (
              <div className="flex items-center justify-between px-4 py-3 border-t border-gray-border">
                <span className="text-sm text-text-secondary">
                  {statusFilter === "ALL"
                    ? `Showing ${page * PAGE_SIZE + 1}–${Math.min((page + 1) * PAGE_SIZE, total)} of ${total}`
                    : `${filteredItems.length} matching on this page (${total} total)`}
                </span>
                <div className="flex gap-2">
                  <Button
                    variant="ghost"
                    size="sm"
                    icon={ChevronLeft}
                    onClick={() => setPage((p) => p - 1)}
                    disabled={page === 0}
                    aria-label="Previous page"
                  >
                    Previous
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    icon={ChevronRight}
                    onClick={() => setPage((p) => p + 1)}
                    disabled={page + 1 >= totalPages}
                    aria-label="Next page"
                  >
                    Next
                  </Button>
                </div>
              </div>
            )}
          </>
        )}
      </Card>
    </div>
  );
}
