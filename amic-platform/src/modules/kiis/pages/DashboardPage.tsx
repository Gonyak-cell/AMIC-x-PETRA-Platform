import {
  Building2,
  Landmark,
  Newspaper,
  TrendingUp,
  Clock,
} from "lucide-react";
import { useNavigate } from "react-router-dom";
import { useDashboardSummary } from "@/modules/kiis/hooks/useDashboard";
import {
  Card,
  KpiCard,
  DataTable,
  Spinner,
  EmptyState,
  PageHero,
} from "@/components/ui";
import type { Column } from "@/components/ui";
import type {
  RecentDeal,
  RiskCompany,
  DataCount,
} from "@/modules/kiis/types/dashboard";
import SearchBar from "@/modules/kiis/components/SearchBar";
import ReputationBadge from "@/modules/kiis/components/ReputationBadge";
import { formatDate } from "@/lib/format";
import heroImg from "@/assets/images/heroes/forestgp-forest.jpg";

/** 백엔드 DashboardSummary.counts 라벨 (변경 시 여기만 수정) */
const LABEL_COMPANIES = "기업";
const LABEL_FUNDS = "펀드";
const LABEL_DEALS = "딜";

function getCount(counts: DataCount[] | undefined, label: string): number {
  return counts?.find((c) => c.label === label)?.count ?? 0;
}

const dealColumns: Column<RecentDeal>[] = [
  {
    key: "target_company",
    header: "Target",
    render: (row) => (
      <span className="font-medium text-text-dark">{row.target_company}</span>
    ),
  },
  {
    key: "amount_display",
    header: "Amount",
    align: "right",
    mono: true,
    render: (row) => row.amount_display ?? "-",
  },
  { key: "sector", header: "Sector", render: (row) => row.sector ?? "-" },
  {
    key: "deal_date",
    header: "Date",
    align: "center",
    width: "120px",
    render: (row) => (row.deal_date ? formatDate(row.deal_date, "short") : "-"),
  },
];

const riskColumns: Column<RiskCompany>[] = [
  {
    key: "corp_name",
    header: "Company",
    render: (row) => (
      <span className="font-medium text-text-dark">{row.corp_name}</span>
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
  const { data: summary, isLoading, isError } = useDashboardSummary();

  if (isLoading) return <Spinner />;
  if (isError) {
    return (
      <EmptyState
        icon={Building2}
        title="Failed to load dashboard"
        description="Could not load dashboard data. Please try again later."
      />
    );
  }

  return (
    <div className="space-y-6">
      <PageHero
        title="KIIS Dashboard"
        subtitle="Korea Investment Intelligence System"
        compact
        backgroundImage={heroImg}
        backgroundOpacity={0.18}
        actions={<SearchBar />}
      />

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <KpiCard
          label="Companies"
          value={String(getCount(summary?.counts, LABEL_COMPANIES))}
          icon={Building2}
        />
        <KpiCard
          label="Funds"
          value={String(getCount(summary?.counts, LABEL_FUNDS))}
          icon={Landmark}
        />
        <KpiCard
          label="News (Recent)"
          value={String(summary?.recent_news_count ?? 0)}
          icon={Newspaper}
          variant="positive"
        />
        <KpiCard
          label="Total Deals"
          value={String(getCount(summary?.counts, LABEL_DEALS))}
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
            data={summary.recent_deals.map((d, i) => ({
              ...d,
              _key: `${d.target_company}-${d.deal_date ?? "no-date"}-${i}`,
            }))}
            keyField="_key"
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
            data={summary.risk_companies.map((r, i) => ({
              ...r,
              _key: r.corp_code ?? `risk-${i}`,
            }))}
            keyField="_key"
            onRowClick={(row) =>
              row.corp_code
                ? navigate(`/kiis/companies/${row.corp_code}`)
                : undefined
            }
            striped
            compact
          />
        )}
      </Card>

      {/* Data Freshness */}
      {summary?.data_freshness && summary.data_freshness.length > 0 && (
        <Card title="Data Freshness" headerBar>
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
            {summary.data_freshness.map((item) => (
              <div
                key={item.entity}
                className="flex items-center gap-2 p-2 rounded border border-gray-border"
              >
                <Clock className="h-4 w-4 text-text-secondary shrink-0" />
                <div className="min-w-0">
                  <div className="text-sm font-medium text-text-dark truncate">
                    {item.entity}
                  </div>
                  <div className="text-xs text-text-secondary">
                    {item.count} items
                    {item.latest_at && (
                      <> &middot; {formatDate(item.latest_at, "short")}</>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </Card>
      )}
    </div>
  );
}
