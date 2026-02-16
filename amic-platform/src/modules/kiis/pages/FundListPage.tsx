import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Landmark, AlertCircle } from "lucide-react";
import { useFunds } from "@/modules/kiis/hooks/useFunds";
import { Card, DataTable, Input, Select, Badge, EmptyState, Pagination, PageHero } from "@/components/ui";
import type { Column } from "@/components/ui";
import type { FundListItem, FundType } from "@/modules/kiis/types/fund";
import { formatAmount } from "@/lib/format";

const FUND_TYPE_OPTIONS = [
  { value: "", label: "All" },
  { value: "blind", label: "Blind" },
  { value: "project", label: "Project" },
];

const columns: Column<FundListItem>[] = [
  {
    key: "fund_name",
    header: "Fund Name",
    render: (row) => (
      <span className="font-medium text-text-dark">{row.fund_name}</span>
    ),
  },
  {
    key: "fund_type",
    header: "Type",
    align: "center",
    width: "90px",
    render: (row) => (
      <Badge variant={row.fund_type === "blind" ? "info" : "neutral"}>
        {row.fund_type}
      </Badge>
    ),
  },
  { key: "company_name", header: "Manager" },
  {
    key: "total_amount",
    header: "Total Amount",
    align: "right",
    mono: true,
    render: (row) => formatAmount(row.total_amount, "KRW"),
  },
  {
    key: "vintage_year",
    header: "Vintage",
    align: "center",
    width: "80px",
    render: (row) => row.vintage_year ?? "-",
  },
  {
    key: "is_maturity_alert",
    header: "Alert",
    align: "center",
    width: "70px",
    render: (row) =>
      row.is_maturity_alert ? (
        <AlertCircle className="h-4 w-4 text-caution mx-auto" />
      ) : null,
  },
];

export default function FundListPage() {
  const navigate = useNavigate();
  const [companyName, setCompanyName] = useState("");
  const [fundType, setFundType] = useState("");
  const [page, setPage] = useState(1);

  const { data, isLoading } = useFunds({
    company_name: companyName || undefined,
    fund_type: (fundType as FundType) || undefined,
    page,
    size: 20,
  });

  return (
    <div className="space-y-6">
      <PageHero
        title="Funds"
        subtitle="PE & VC fund registry"
        compact
      />

      <div className="flex gap-3 items-end">
        <div className="flex-1 max-w-sm">
          <Input
            label="Manager Company"
            placeholder="Search by manager name..."
            value={companyName}
            onChange={(e) => {
              setCompanyName(e.target.value);
              setPage(1);
            }}
          />
        </div>
        <Select
          label="Fund Type"
          options={FUND_TYPE_OPTIONS}
          value={fundType}
          onChange={(e) => {
            setFundType(e.target.value);
            setPage(1);
          }}
        />
      </div>

      <Card padding="none">
        {!isLoading && (!data?.items || data.items.length === 0) ? (
          <EmptyState
            icon={Landmark}
            title="No funds found"
            description="Try adjusting your search or filters."
          />
        ) : (
          <DataTable
            columns={columns}
            data={data?.items ?? []}
            keyField="fund_code"
            loading={isLoading}
            onRowClick={(row) => navigate(`/kiis/funds/${row.fund_code}`)}
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
