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
} from "@/components/ui";
import type { Column } from "@/components/ui";
import type { Document } from "@/modules/im/types/document";

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
    key: "corp_code",
    header: "Corp Code",
    align: "center",
    width: "120px",
    mono: true,
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
  const { data, isLoading } = useDocuments({ offset: page * PAGE_SIZE, limit: PAGE_SIZE });

  const total = data?.total ?? 0;
  const totalPages = Math.ceil(total / PAGE_SIZE);

  const kpis = useMemo(() => {
    const items = data?.items ?? [];
    return {
      total,
      inProgress: items.filter((d) =>
        ["PENDING", "COLLECTING", "ANALYZING", "GENERATING", "RENDERING"].includes(d.status),
      ).length,
      completed: items.filter((d) => d.status === "COMPLETED").length,
      failed: items.filter((d) => d.status === "FAILED").length,
    };
  }, [data, total]);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-heading font-bold text-text-dark">
          IM Projects
        </h1>
        <Button
          variant="accent"
          icon={Plus}
          onClick={() => navigate("/im/new")}
        >
          New IM
        </Button>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <KpiCard label="Total Projects" value={String(kpis.total)} icon={FileText} />
        <KpiCard label="In Progress" value={String(kpis.inProgress)} icon={Loader2} />
        <KpiCard label="Completed" value={String(kpis.completed)} icon={CheckCircle} />
        <KpiCard label="Failed" value={String(kpis.failed)} icon={AlertTriangle} />
      </div>

      {/* Table */}
      <Card title="All Projects" headerBar padding="none">
        {!isLoading && (!data?.items || data.items.length === 0) ? (
          <EmptyState
            icon={FileText}
            title="No IM projects yet"
            description="Create your first Investment Memorandum to get started."
            actionLabel="Create IM"
            onAction={() => navigate("/im/new")}
          />
        ) : (
          <>
            <DataTable
              columns={columns}
              data={data?.items ?? []}
              keyField="id"
              loading={isLoading}
              onRowClick={(row) => navigate(`/im/documents/${row.id}`)}
              striped
            />
            {totalPages > 1 && (
              <div className="flex items-center justify-between px-4 py-3 border-t border-gray-border">
                <span className="text-sm text-text-secondary">
                  Showing {page * PAGE_SIZE + 1}–{Math.min((page + 1) * PAGE_SIZE, total)} of {total}
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
