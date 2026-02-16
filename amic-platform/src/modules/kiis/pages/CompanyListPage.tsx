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
  Pagination,
  PageHero,
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
    render: (row) =>
      row.corp_cls ? (
        <Badge variant="info">{CORP_CLS_LABELS[row.corp_cls]}</Badge>
      ) : (
        "-"
      ),
  },
  {
    key: "stock_name",
    header: "Stock Name",
    render: (row) => row.stock_name ?? "-",
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
      <PageHero
        title="Companies"
        subtitle="Search and browse listed companies"
        compact
      />

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

      <Pagination
        page={page}
        totalPages={data ? Math.ceil(data.total / 20) : 0}
        onPageChange={setPage}
      />
    </div>
  );
}
