import { useState } from "react";
import {
  FileText,
  CheckCircle,
  Loader2,
  AlertTriangle,
  Download,
  Eye,
} from "lucide-react";
import {
  Card,
  KpiCard,
  DataTable,
  Badge,
  Button,
  EmptyState,
} from "@/components/ui";
import type { Column } from "@/components/ui";

// ── Mock Data (백엔드 없이 확인용) ──

interface SampleDocument {
  id: string;
  project_name: string;
  company_name: string;
  corp_code: string;
  im_style: string;
  status: string;
  progress_pct: number;
  sections: string[];
  created_at: string;
  file_size_bytes: number | null;
}

const MOCK_DOCUMENTS: SampleDocument[] = [
  {
    id: "doc-1",
    project_name: "Samsung IM",
    company_name: "삼성전자",
    corp_code: "00126380",
    im_style: "TITAN",
    status: "COMPLETED",
    progress_pct: 100,
    sections: ["overview", "financials", "valuation", "appendix"],
    created_at: "2025-01-10T08:00:00Z",
    file_size_bytes: 2_048_000,
  },
  {
    id: "doc-2",
    project_name: "SK Hynix IM",
    company_name: "SK하이닉스",
    corp_code: "00164779",
    im_style: "FULL",
    status: "GENERATING",
    progress_pct: 65,
    sections: ["overview", "financials"],
    created_at: "2025-02-01T10:00:00Z",
    file_size_bytes: null,
  },
  {
    id: "doc-3",
    project_name: "LG Energy IM",
    company_name: "LG에너지솔루션",
    corp_code: "01234567",
    im_style: "TITAN",
    status: "PENDING",
    progress_pct: 0,
    sections: ["overview", "financials", "valuation"],
    created_at: "2025-02-05T14:00:00Z",
    file_size_bytes: null,
  },
  {
    id: "doc-4",
    project_name: "Kakao IM",
    company_name: "카카오",
    corp_code: "00234567",
    im_style: "COMPACT",
    status: "FAILED",
    progress_pct: 30,
    sections: ["overview"],
    created_at: "2025-01-20T11:00:00Z",
    file_size_bytes: null,
  },
  {
    id: "doc-5",
    project_name: "Naver IM",
    company_name: "네이버",
    corp_code: "00345678",
    im_style: "FULL",
    status: "COMPLETED",
    progress_pct: 100,
    sections: ["overview", "financials", "valuation"],
    created_at: "2025-01-15T09:00:00Z",
    file_size_bytes: 3_500_000,
  },
];

function statusBadge(status: string) {
  const variants: Record<string, "success" | "warning" | "error" | "info" | "neutral"> = {
    COMPLETED: "success",
    GENERATING: "info",
    PENDING: "neutral",
    FAILED: "error",
    COLLECTING: "info",
    ANALYZING: "warning",
  };
  return <Badge variant={variants[status] ?? "neutral"}>{status}</Badge>;
}

function formatBytes(bytes: number | null) {
  if (bytes === null) return "—";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

const columns: Column<SampleDocument>[] = [
  {
    key: "project_name",
    header: "Project",
    render: (row) => (
      <span className="font-medium text-text-dark">{row.project_name}</span>
    ),
  },
  {
    key: "company_name",
    header: "Company",
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
  },
  {
    key: "status",
    header: "Status",
    align: "center",
    width: "120px",
    render: (row) => statusBadge(row.status),
  },
  {
    key: "progress_pct",
    header: "Progress",
    align: "center",
    width: "120px",
    render: (row) => (
      <div className="flex items-center gap-2">
        <div className="flex-1 bg-gray-100 rounded-full h-1.5">
          <div
            className={`h-1.5 rounded-full ${
              row.status === "FAILED"
                ? "bg-red-400"
                : row.progress_pct === 100
                  ? "bg-green-400"
                  : "bg-accent"
            }`}
            style={{ width: `${row.progress_pct}%` }}
          />
        </div>
        <span className="text-xs text-text-secondary w-8 text-right">
          {row.progress_pct}%
        </span>
      </div>
    ),
  },
  {
    key: "file_size_bytes",
    header: "Size",
    align: "right",
    width: "100px",
    render: (row) => (
      <span className="text-sm text-text-secondary">
        {formatBytes(row.file_size_bytes)}
      </span>
    ),
  },
];

export default function SamplePage() {
  const [filter, setFilter] = useState<string>("ALL");

  const docs =
    filter === "ALL"
      ? MOCK_DOCUMENTS
      : MOCK_DOCUMENTS.filter((d) => d.status === filter);

  const kpis = {
    total: MOCK_DOCUMENTS.length,
    completed: MOCK_DOCUMENTS.filter((d) => d.status === "COMPLETED").length,
    inProgress: MOCK_DOCUMENTS.filter((d) =>
      ["PENDING", "COLLECTING", "ANALYZING", "GENERATING"].includes(d.status),
    ).length,
    failed: MOCK_DOCUMENTS.filter((d) => d.status === "FAILED").length,
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-heading font-bold text-text-dark">
            IM Sample Page
          </h1>
          <p className="text-sm text-text-secondary mt-1">
            Mock 데이터로 구성된 IM 샘플 페이지입니다 (백엔드 불필요)
          </p>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <KpiCard
          label="Total Projects"
          value={String(kpis.total)}
          icon={FileText}
        />
        <KpiCard
          label="Completed"
          value={String(kpis.completed)}
          icon={CheckCircle}
          variant="positive"
        />
        <KpiCard
          label="In Progress"
          value={String(kpis.inProgress)}
          icon={Loader2}
          variant="caution"
        />
        <KpiCard
          label="Failed"
          value={String(kpis.failed)}
          icon={AlertTriangle}
          variant="negative"
        />
      </div>

      {/* Filters */}
      <div className="flex gap-2">
        {["ALL", "COMPLETED", "GENERATING", "PENDING", "FAILED"].map((s) => (
          <Button
            key={s}
            variant={filter === s ? "accent" : "ghost"}
            size="sm"
            onClick={() => setFilter(s)}
          >
            {s === "ALL" ? "All" : s.charAt(0) + s.slice(1).toLowerCase()}
          </Button>
        ))}
      </div>

      {/* Document Table */}
      <Card title="IM Documents" headerBar padding="none">
        {docs.length === 0 ? (
          <EmptyState
            icon={FileText}
            title="No documents match filter"
            description="Try selecting a different status filter."
          />
        ) : (
          <DataTable
            columns={columns}
            data={docs}
            keyField="id"
            onRowClick={(row) =>
              alert(`Document: ${row.project_name}\nStatus: ${row.status}\nProgress: ${row.progress_pct}%`)
            }
            striped
          />
        )}
      </Card>

      {/* Detail Cards */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card title="IM Style Distribution">
          <div className="space-y-3">
            {["TITAN", "FULL", "COMPACT"].map((style) => {
              const count = MOCK_DOCUMENTS.filter(
                (d) => d.im_style === style,
              ).length;
              const pct = Math.round((count / MOCK_DOCUMENTS.length) * 100);
              return (
                <div key={style}>
                  <div className="flex items-center justify-between mb-1">
                    <Badge variant="neutral">{style}</Badge>
                    <span className="text-sm text-text-secondary">
                      {count} ({pct}%)
                    </span>
                  </div>
                  <div className="w-full bg-gray-100 rounded-full h-2">
                    <div
                      className="bg-accent h-2 rounded-full transition-all"
                      style={{ width: `${pct}%` }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        </Card>

        <Card title="Recent Completed">
          <div className="space-y-3">
            {MOCK_DOCUMENTS.filter((d) => d.status === "COMPLETED").map((doc) => (
              <div
                key={doc.id}
                className="flex items-center justify-between p-3 bg-gray-50 rounded-lg"
              >
                <div>
                  <p className="font-medium text-text-dark text-sm">
                    {doc.project_name}
                  </p>
                  <p className="text-xs text-text-secondary">
                    {doc.company_name} &middot; {formatBytes(doc.file_size_bytes)}
                  </p>
                </div>
                <div className="flex gap-1">
                  <Button
                    variant="ghost"
                    size="sm"
                    icon={Eye}
                    onClick={() => alert(`Preview: ${doc.project_name}`)}
                  >
                    View
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    icon={Download}
                    onClick={() => alert(`Download: ${doc.project_name}`)}
                  >
                    Download
                  </Button>
                </div>
              </div>
            ))}
          </div>
        </Card>
      </div>

      {/* Info */}
      <Card>
        <div className="flex items-start gap-3">
          <AlertTriangle className="h-5 w-5 text-amber-500 shrink-0 mt-0.5" />
          <div>
            <p className="font-medium text-text-dark">Sample Page Notice</p>
            <p className="text-sm text-text-secondary mt-1">
              이 페이지는 하드코딩된 목 데이터를 사용합니다.
              실제 API 연동 없이 UI 컴포넌트와 레이아웃을 확인할 수 있습니다.
            </p>
          </div>
        </div>
      </Card>
    </div>
  );
}
