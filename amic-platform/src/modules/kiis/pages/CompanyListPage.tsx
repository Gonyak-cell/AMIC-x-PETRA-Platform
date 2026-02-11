import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Building2 } from "lucide-react";
import { useCompanies } from "@/modules/kiis/hooks/useCompanies";
import {
  Card,
  DataTable,
  Input,
  Select,
  Badge,
  EmptyState,
} from "@/components/ui";
import type { Column } from "@/components/ui";
import type { Company, CorpCls } from "@/modules/kiis/types/company";

const CORP_CLS_OPTIONS = [
  { value: "", label: "All" },
  { value: "Y", label: "KOSPI" },
  { value: "K", label: "KOSDAQ" },
  { value: "N", label: "KONEX" },
  { value: "E", label: "Other" },
];

const CORP_CLS_LABELS: Record<CorpCls, string> = {
  Y: "KOSPI",
  K: "KOSDAQ",
  N: "KONEX",
  E: "Other",
};

const columns: Column<Company>[] = [
  {
    key: "corp_name",
    header: "Company",
    render: (row) => (
      <span className="font-medium text-text-dark">{row.corp_name}</span>
    ),
  },
  {
    key: "stock_code",
    header: "Stock Code",
    align: "center",
    width: "120px",
    mono: true,
    render: (row) => row.stock_code ?? "-",
  },
  {
    key: "corp_cls",
    header: "Market",
    align: "center",
    width: "100px",
    render: (row) => (
      <Badge variant="info">{CORP_CLS_LABELS[row.corp_cls]}</Badge>
    ),
  },
  { key: "ceo_nm", header: "CEO", render: (row) => row.ceo_nm ?? "-" },
  {
    key: "address",
    header: "Industry",
    render: (row) => row.address ?? "-",
  },
];

export default function CompanyListPage() {
  const navigate = useNavigate();
  const [search, setSearch] = useState("");
  const [corpCls, setCorpCls] = useState("");
  const [page, setPage] = useState(1);

  const { data, isLoading } = useCompanies({
    search: search || undefined,
    corp_cls: (corpCls as CorpCls) || undefined,
    page,
    size: 20,
  });

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-heading font-bold text-text-dark">
        Companies
      </h1>

      {/* Filters */}
      <div className="flex gap-3 items-end">
        <div className="flex-1 max-w-sm">
          <Input
            label="Search"
            placeholder="Search by company name..."
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              setPage(1);
            }}
          />
        </div>
        <Select
          label="Market"
          options={CORP_CLS_OPTIONS}
          value={corpCls}
          onChange={(e) => {
            setCorpCls(e.target.value);
            setPage(1);
          }}
        />
      </div>

      {/* Table */}
      <Card padding="none">
        {!isLoading && (!data?.items || data.items.length === 0) ? (
          <EmptyState
            icon={Building2}
            title="No companies found"
            description="Try adjusting your search or filters."
          />
        ) : (
          <DataTable
            columns={columns}
            data={data?.items ?? []}
            keyField="corp_code"
            loading={isLoading}
            onRowClick={(row) => navigate(`/kiis/companies/${row.corp_code}`)}
            striped
          />
        )}
      </Card>

      {/* Pagination */}
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
