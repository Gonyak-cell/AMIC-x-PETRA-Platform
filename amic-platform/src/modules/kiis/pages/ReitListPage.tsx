import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Home, AlertTriangle } from "lucide-react";
import { useReits } from "@/modules/kiis/hooks/useReits";
import { Card, DataTable, Select, Badge, EmptyState } from "@/components/ui";
import type { Column } from "@/components/ui";
import type { REITsListItem, ReitType, ReitStatus } from "@/modules/kiis/types/reit";
import { formatAmount, formatPercent } from "@/lib/format";

const TYPE_OPTIONS = [
  { value: "", label: "All Types" },
  { value: "self_managed", label: "Self-Managed" },
  { value: "entrusted", label: "Entrusted" },
];

const STATUS_OPTIONS = [
  { value: "", label: "All Status" },
  { value: "authorized", label: "Authorized" },
  { value: "operating", label: "Operating" },
  { value: "dissolved", label: "Dissolved" },
];

const statusVariant: Record<ReitStatus, "info" | "success" | "neutral"> = {
  authorized: "info",
  operating: "success",
  dissolved: "neutral",
};

const columns: Column<REITsListItem>[] = [
  {
    key: "reits_name",
    header: "REITs Name",
    render: (row) => (
      <span className="font-medium text-text-dark">{row.reits_name}</span>
    ),
  },
  {
    key: "reits_type",
    header: "Type",
    align: "center",
    width: "120px",
    render: (row) => (
      <Badge variant="info">
        {row.reits_type === "self_managed" ? "Self-Managed" : "Entrusted"}
      </Badge>
    ),
  },
  {
    key: "status",
    header: "Status",
    align: "center",
    width: "110px",
    render: (row) => (
      <Badge variant={statusVariant[row.status as ReitStatus]}>{row.status}</Badge>
    ),
  },
  {
    key: "management_company",
    header: "Manager",
    render: (row) => row.management_company ?? "-",
  },
  {
    key: "total_assets",
    header: "Total Assets",
    align: "right",
    mono: true,
    render: (row) => formatAmount(row.total_assets, "KRW"),
  },
  {
    key: "real_estate_ratio",
    header: "RE Ratio",
    align: "right",
    width: "120px",
    mono: true,
    render: (row) => (
      <span className="inline-flex items-center gap-1">
        {formatPercent(row.real_estate_ratio)}
        {row.has_asset_ratio_warning && (
          <AlertTriangle className="h-3.5 w-3.5 text-caution" />
        )}
      </span>
    ),
  },
];

export default function ReitListPage() {
  const navigate = useNavigate();
  const [type, setType] = useState("");
  const [status, setStatus] = useState("");
  const [page, setPage] = useState(1);

  const { data, isLoading } = useReits({
    type: (type as ReitType) || undefined,
    status: (status as ReitStatus) || undefined,
    page,
    size: 20,
  });

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-heading font-bold text-text-dark">REITs</h1>

      <div className="flex gap-3 items-end">
        <Select
          label="Type"
          options={TYPE_OPTIONS}
          value={type}
          onChange={(e) => {
            setType(e.target.value);
            setPage(1);
          }}
        />
        <Select
          label="Status"
          options={STATUS_OPTIONS}
          value={status}
          onChange={(e) => {
            setStatus(e.target.value);
            setPage(1);
          }}
        />
      </div>

      <Card padding="none">
        {!isLoading && (!data?.items || data.items.length === 0) ? (
          <EmptyState
            icon={Home}
            title="No REITs found"
            description="Try adjusting your filters."
          />
        ) : (
          <DataTable
            columns={columns}
            data={data?.items ?? []}
            keyField="reits_code"
            loading={isLoading}
            onRowClick={(row) => navigate(`/kiis/reits/${row.reits_code}`)}
            striped
          />
        )}
      </Card>

      {data && data.total > 20 && (
        <div className="flex items-center justify-center gap-2">
          <button
            className="px-3 py-1 text-sm rounded border border-gray-border disabled:opacity-40"
            disabled={page <= 1}
            onClick={() => setPage((p) => p - 1)}
          >
            Previous
          </button>
          <span className="text-sm text-text-secondary">
            Page {page} of {Math.ceil(data.total / 20)}
          </span>
          <button
            className="px-3 py-1 text-sm rounded border border-gray-border disabled:opacity-40"
            disabled={page >= Math.ceil(data.total / 20)}
            onClick={() => setPage((p) => p + 1)}
          >
            Next
          </button>
        </div>
      )}
    </div>
  );
}
