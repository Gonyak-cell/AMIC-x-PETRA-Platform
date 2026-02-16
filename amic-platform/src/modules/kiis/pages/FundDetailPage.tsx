import { useParams, Link } from "react-router-dom";
import { Landmark, Users } from "lucide-react";
import { useFundDetail } from "@/modules/kiis/hooks/useFunds";
import { Card, KpiCard, DataTable, Badge, Spinner, EmptyState, PageHero } from "@/components/ui";
import type { Column } from "@/components/ui";
import type { FundManagerItem } from "@/modules/kiis/types/fund";
import { formatAmount, formatPercent } from "@/lib/format";

const managerColumns: Column<FundManagerItem>[] = [
  {
    key: "manager_name",
    header: "Name",
    render: (row) => (
      <span className="font-medium text-text-dark">{row.manager_name}</span>
    ),
  },
  { key: "position", header: "Position", render: (row) => row.position ?? "-" },
  { key: "role", header: "Role", render: (row) => row.role ?? "-" },
  {
    key: "career_years",
    header: "Experience",
    align: "center",
    width: "100px",
    render: (row) => (row.career_years != null ? `${row.career_years}y` : "-"),
  },
  {
    key: "education",
    header: "Education",
    render: (row) => row.education ?? "-",
  },
  {
    key: "certifications",
    header: "Certifications",
    render: (row) => row.certifications || "-",
  },
  {
    key: "is_active",
    header: "Status",
    align: "center",
    width: "80px",
    render: (row) => (
      <Badge variant={row.is_active ? "success" : "neutral"}>
        {row.is_active ? "Active" : "Inactive"}
      </Badge>
    ),
  },
];

export default function FundDetailPage() {
  const { fundCode } = useParams<{ fundCode: string }>();
  const { data, isLoading, isError } = useFundDetail(fundCode ?? "");

  const fund = data?.fund;
  const managers = data?.managers ?? [];

  if (isLoading) return <Spinner />;
  if (isError || !fund) {
    return (
      <EmptyState
        icon={Landmark}
        title="Fund not found"
        description="The requested fund could not be found."
      />
    );
  }

  return (
    <div className="space-y-6">
      {/* Breadcrumb */}
      <div className="text-sm text-text-secondary">
        <Link to="/kiis/funds" className="hover:text-accent">
          Funds
        </Link>
        <span className="mx-2">/</span>
        <span className="text-text-dark">{fund.fund_name}</span>
      </div>

      {/* Header */}
      <PageHero
        title={fund.fund_name}
        subtitle={fund.company_name}
        compact
      />

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <KpiCard
          label="Total Amount"
          value={formatAmount(fund.total_amount, "KRW")}
          icon={Landmark}
        />
        <KpiCard
          label="Mgmt Fee"
          value={formatPercent(fund.management_fee_rate)}
        />
        <KpiCard
          label="Performance Fee"
          value={formatPercent(fund.performance_fee_rate)}
        />
        <KpiCard
          label="Vintage Year"
          value={fund.vintage_year != null ? String(fund.vintage_year) : "-"}
        />
      </div>

      {/* Managers */}
      <Card title="Fund Managers" headerBar padding="none">
        {!managers.length ? (
          <EmptyState
            icon={Users}
            title="No managers"
            description="Manager information is not available."
          />
        ) : (
          <DataTable
            columns={managerColumns}
            data={managers.map((m) => ({ ...m, _id: `${m.manager_name}-${m.position ?? ""}-${m.appointed_date ?? ""}` }))}
            keyField="_id"
            compact
            striped
          />
        )}
      </Card>
    </div>
  );
}
