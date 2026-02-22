import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { FileText, Plus, CheckCircle, Loader2, AlertTriangle, ChevronLeft, ChevronRight } from "lucide-react";
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
import type { Document, DocumentStatus, DataSource } from "@/modules/im/types/document";
import { IN_PROGRESS_STATUSES } from "@/modules/im/types/document";

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
      const badge: Record<DataSource, { label: string; cls: string }> = {
        DART: { label: "DART", cls: "bg-blue-100 text-blue-700" },
        MANUAL: { label: "Manual", cls: "bg-gray-100 text-gray-600" },
        EXCEL: { label: "Excel", cls: "bg-emerald-100 text-emerald-700" },
      };
      const b = badge[row.data_source] ?? badge.MANUAL;
      return (
        <span className={`inline-block px-2 py-0.5 text-xs font-medium rounded ${b.cls}`}>
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
  const { data, isLoading, isError } = useDocuments({ offset: page * PAGE_SIZE, limit: PAGE_SIZE });

  const total = data?.total ?? 0;
  const totalPages = Math.ceil(total / PAGE_SIZE);
  const items = useMemo(() => data?.items ?? [], [data?.items]);

  const filteredItems = useMemo(() => {
    if (statusFilter === "ALL") return items;
    if (statusFilter === "IN_PROGRESS")
      return items.filter((d) => IN_PROGRESS_STATUSES.includes(d.status));
    return items.filter((d) => d.status === statusFilter);
  }, [items, statusFilter]);

  const kpis = useMemo(() => ({
    total: data?.total ?? 0,
    inProgress: items.filter((d) =>
      IN_PROGRESS_STATUSES.includes(d.status),
    ).length,
    completed: items.filter((d) => d.status === "COMPLETED").length,
    failed: items.filter((d) => d.status === "FAILED").length,
  }), [data?.total, items]);

  return (
    <div className="space-y-6">
      {/* Header */}
      <PageHero
        title="IM Projects"
        subtitle="Investment Memorandum generation and management"
        compact
        actions={
          <Button
            variant="accent"
            icon={Plus}
            onClick={() => navigate("/im/new")}
          >
            New IM
          </Button>
        }
      />

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <KpiCard label="Total" value={String(kpis.total)} icon={FileText} />
        <KpiCard label="In Progress" value={String(kpis.inProgress)} icon={Loader2} variant="caution" />
        <KpiCard label="Completed" value={String(kpis.completed)} icon={CheckCircle} variant="positive" />
        <KpiCard label="Failed" value={String(kpis.failed)} icon={AlertTriangle} variant="negative" />
      </div>

      {/* Status Filters */}
      <div className="flex gap-2">
        {(["ALL", "IN_PROGRESS", "COMPLETED", "FAILED"] as const).map((s) => (
          <Button
            key={s}
            variant={statusFilter === s ? "accent" : "ghost"}
            size="sm"
            onClick={() => { setStatusFilter(s); setPage(0); }}
          >
            {s === "ALL" ? "All" : s === "IN_PROGRESS" ? "In Progress" : s.charAt(0) + s.slice(1).toLowerCase()}
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
            title={statusFilter === "ALL" ? "No IM projects yet" : "No matching projects"}
            description={statusFilter === "ALL"
              ? "Create your first Investment Memorandum to get started."
              : "No projects match the selected status filter."}
            actionLabel={statusFilter === "ALL" ? "Create IM" : undefined}
            onAction={statusFilter === "ALL" ? () => navigate("/im/new") : undefined}
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
