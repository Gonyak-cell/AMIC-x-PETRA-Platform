import {
  Building2,
  Landmark,
  Newspaper,
  TrendingUp,
} from "lucide-react";
import { useNavigate } from "react-router-dom";
import { useDashboardSummary } from "@/modules/kiis/hooks/useDashboard";
import { Card, KpiCard, DataTable, Spinner, EmptyState } from "@/components/ui";
import type { Column } from "@/components/ui";
import type { DealItem } from "@/modules/kiis/types/deal";
import type { ReputationScore } from "@/modules/kiis/types/analysis";
import SearchBar from "@/modules/kiis/components/SearchBar";
import ReputationBadge from "@/modules/kiis/components/ReputationBadge";
import { formatAmount, formatDate } from "@/lib/format";

const dealColumns: Column<DealItem>[] = [
  {
    key: "investor_name",
    header: "Investor",
    render: (row) => (
      <span className="font-medium text-text-dark">{row.investor_name}</span>
    ),
  },
  { key: "target_company", header: "Target" },
  {
    key: "amount",
    header: "Amount",
    align: "right",
    mono: true,
    render: (row) => formatAmount(row.amount, "KRW"),
  },
  { key: "round_stage", header: "Round", align: "center", width: "100px" },
  {
    key: "deal_date",
    header: "Date",
    align: "center",
    width: "120px",
    render: (row) => formatDate(row.deal_date, "short"),
  },
];

const riskColumns: Column<ReputationScore>[] = [
  {
    key: "corp_name",
    header: "Company",
    render: (row) => (
      <span className="font-medium text-text-dark">
        {row.corp_name ?? row.corp_code}
      </span>
    ),
  },
  {
    key: "total_score",
    header: "Score",
    align: "center",
    width: "120px",
    render: (row) => (
      <ReputationBadge score={row.total_score} statusTag={row.status_tag} />
    ),
  },
  {
    key: "status_tag",
    header: "Status",
    align: "center",
    width: "80px",
    render: (row) => (
      <span className="capitalize text-sm">{row.status_tag}</span>
    ),
  },
];

export default function DashboardPage() {
  const navigate = useNavigate();
  const { data: summary, isLoading } = useDashboardSummary();

  if (isLoading) return <Spinner />;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-heading font-bold text-text-dark">
          KIIS Dashboard
        </h1>
        <SearchBar />
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <KpiCard
          label="Companies"
          value={String(summary?.total_companies ?? 0)}
          icon={Building2}
        />
        <KpiCard
          label="Funds"
          value={String(summary?.total_funds ?? 0)}
          icon={Landmark}
        />
        <KpiCard
          label="News (7 Days)"
          value={String(summary?.news_last_7days ?? 0)}
          icon={Newspaper}
          variant="positive"
        />
        <KpiCard
          label="Total Deals"
          value={String(summary?.total_deals ?? 0)}
          icon={TrendingUp}
        />
      </div>

      {/* Recent Deals */}
      <Card title="Recent Deals" headerBar padding="none">
        {!summary?.recent_deals?.length ? (
          <EmptyState
            icon={TrendingUp}
            title="No recent deals"
            description="Deal data will appear once the KIIS backend is connected."
          />
        ) : (
          <DataTable
            columns={dealColumns}
            data={summary.recent_deals}
            keyField="investor_name"
            striped
            compact
          />
        )}
      </Card>

      {/* Risk Companies */}
      <Card title="Risk Companies" headerBar padding="none">
        {!summary?.risk_companies?.length ? (
          <EmptyState
            icon={Building2}
            title="No risk companies"
            description="Risk analysis data will appear once reputation scores are calculated."
          />
        ) : (
          <DataTable
            columns={riskColumns}
            data={summary.risk_companies}
            keyField="corp_code"
            onRowClick={(row) => navigate(`/kiis/companies/${row.corp_code}`)}
            striped
            compact
          />
        )}
      </Card>
    </div>
  );
}
