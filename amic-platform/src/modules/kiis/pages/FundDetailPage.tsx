import { useState } from "react";
import { useParams, Link } from "react-router-dom";
import {
  Landmark,
  Users,
  TrendingUp,
  BarChart3,
  Info,
  PieChart,
} from "lucide-react";
import { useFundDetail } from "@/modules/kiis/hooks/useFunds";
import { useQualitativeReputation } from "@/modules/kiis/hooks/useCompanies";
import {
  useDealsByCompany,
  useDealsByFund,
  useDealTrends,
  useDealStats,
  useTendencySummary,
} from "@/modules/kiis/hooks/useDeals";
import {
  Card,
  KpiCard,
  DataTable,
  Badge,
  Spinner,
  EmptyState,
  PageHero,
  Tabs,
} from "@/components/ui";
import type { Column, TabItem } from "@/components/ui";
import ReputationSummary from "@/modules/kiis/components/ReputationSummary";
import TendencySummary from "@/modules/kiis/components/TendencySummary";
import DealTrendChart from "@/modules/kiis/components/DealTrendChart";
import { FinancialBarChart } from "@/components/charts/FinancialBarChart";
import type { BarChartDataPoint } from "@/components/charts/FinancialBarChart";
import type { FundManagerItem } from "@/modules/kiis/types/fund";
import type { DealItem } from "@/modules/kiis/types/deal";
import { formatAmountKRW, formatPercent, formatDate } from "@/lib/format";
import heroImg from "@/assets/images/heroes/forestgp-news.jpg";

/* ───────── Column definitions ───────── */

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

const dealColumns: Column<DealItem>[] = [
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
  { key: "round_stage", header: "Round", align: "center", width: "100px" },
  {
    key: "deal_date",
    header: "Date",
    align: "center",
    width: "120px",
    render: (row) =>
      row.deal_date ? formatDate(row.deal_date, "short") : "-",
  },
];

/* ───────── Tabs ───────── */

const TABS: TabItem[] = [
  { id: "overview", label: "Overview", icon: Landmark },
  { id: "deals", label: "Deal History", icon: TrendingUp },
  { id: "tendency", label: "Investment Tendency", icon: PieChart },
  { id: "managers", label: "Managers", icon: Users },
];

/* ───────── Page ───────── */

export default function FundDetailPage() {
  const { fundCode } = useParams<{ fundCode: string }>();
  const [activeTab, setActiveTab] = useState("overview");
  const { data, isLoading, isError } = useFundDetail(fundCode ?? "");

  const fund = data?.fund;
  const managers = data?.managers ?? [];
  const corpCode = fund?.corp_code ?? "";

  const hasCorpCode = /^\d{8}$/.test(corpCode);
  const { data: deals } = useDealsByCompany(corpCode, { size: 20 });
  const { data: fundDeals } = useDealsByFund(fundCode ?? "", { size: 20 });
  const { data: trends } = useDealTrends(
    { corp_code: corpCode },
    { enabled: hasCorpCode },
  );
  const { data: dealStats } = useDealStats(corpCode, 5, {
    enabled: hasCorpCode,
  });
  const { data: qualitativeReputation, isLoading: qualitativeReputationLoading } =
    useQualitativeReputation(corpCode, {}, { enabled: hasCorpCode });
  const { data: tendencySummary, isLoading: tendencySummaryLoading } =
    useTendencySummary(corpCode, 3, { enabled: hasCorpCode });

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
          GPs & Funds
        </Link>
        <span className="mx-2">/</span>
        {fund.company_code ? (
          <Link
            to={`/kiis/funds/gp/${encodeURIComponent(fund.company_code)}?name=${encodeURIComponent(fund.company_name)}`}
            className="hover:text-accent"
          >
            {fund.company_name}
          </Link>
        ) : (
          <span>{fund.company_name}</span>
        )}
        <span className="mx-2">/</span>
        <span className="text-text-dark">{fund.fund_name}</span>
      </div>

      {/* Header */}
      <PageHero title={fund.fund_name} subtitle={fund.company_name} compact backgroundImage={heroImg} backgroundOpacity={0.18} />

      {/* KPI Cards (always visible) */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <KpiCard
          label="Total Amount"
          value={formatAmountKRW(fund.total_amount)}
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

      {/* Tabs */}
      <Tabs tabs={TABS} activeTab={activeTab} onTabChange={setActiveTab} />

      {/* Tab panels */}
      {activeTab === "overview" && (
        <div className="space-y-6" role="tabpanel" id="tabpanel-overview" aria-labelledby="tab-overview">
          {/* No corp_code notice */}
          {!hasCorpCode && (
            <Card>
              <div className="flex items-center gap-3 text-text-secondary">
                <Info className="h-5 w-5 shrink-0" />
                <p className="text-sm">
                  Reputation, deal history, and investment tendency data are
                  unavailable because this fund&apos;s management company could
                  not be matched to a DART entity.
                </p>
              </div>
            </Card>
          )}

          {/* Qualitative Reputation */}
          {hasCorpCode && (
            <ReputationSummary
              data={qualitativeReputation}
              isLoading={qualitativeReputationLoading}
            />
          )}

          {/* Deal Trend Chart */}
          {hasCorpCode && trends && trends.length > 0 && (
            <Card title="Deal Trends" headerBar>
              <DealTrendChart data={trends} height={280} />
            </Card>
          )}

          {/* Investment Stats */}
          {hasCorpCode && dealStats && dealStats.total_deals > 0 && (
            <>
              <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                <KpiCard
                  label="Total Deals"
                  value={String(dealStats.total_deals)}
                  icon={BarChart3}
                />
                <KpiCard
                  label="Avg Amount"
                  value={formatAmountKRW(dealStats.avg_amount)}
                />
                <KpiCard
                  label="Median Amount"
                  value={formatAmountKRW(dealStats.median_amount)}
                />
                <KpiCard
                  label="Max Amount"
                  value={formatAmountKRW(dealStats.max_amount)}
                />
              </div>

              {dealStats.distribution.length > 0 && (
                <Card title="Deal Size Distribution" headerBar>
                  <FinancialBarChart
                    data={dealStats.distribution.map(
                      (b): BarChartDataPoint => ({
                        name: b.bucket_label,
                        value: b.deal_count,
                      }),
                    )}
                    height={260}
                    colorScheme="categorical"
                    aria-label="Deal size distribution chart"
                  />
                </Card>
              )}
            </>
          )}
        </div>
      )}

      {activeTab === "deals" && (
        <div className="space-y-6" role="tabpanel" id="tabpanel-deals" aria-labelledby="tab-deals">
          {/* Fund-level Deals */}
          <Card title="Fund Deals" headerBar padding="none">
            {!fundDeals?.length ? (
              <EmptyState
                icon={TrendingUp}
                title="No fund deals"
                description="No deals linked to this fund yet. Deals extracted with a fund code will appear here."
              />
            ) : (
              <DataTable
                columns={dealColumns}
                data={fundDeals}
                keyField="id"
                compact
                striped
              />
            )}
          </Card>

          {/* Company-level Deals */}
          {hasCorpCode && (
            <Card
              title="Company Deals"
              headerBar
              padding="none"
              actions={
                <Link
                  to="/kiis/deals"
                  className="text-sm text-accent hover:underline"
                >
                  View all
                </Link>
              }
            >
              {!deals?.length ? (
                <EmptyState
                  icon={TrendingUp}
                  title="No company deals"
                  description="No deals found for this fund's management company."
                />
              ) : (
                <DataTable
                  columns={dealColumns}
                  data={deals}
                  keyField="id"
                  compact
                  striped
                />
              )}
            </Card>
          )}

          {!hasCorpCode && !fundDeals?.length && (
            <Card>
              <div className="flex items-center gap-3 text-text-secondary">
                <Info className="h-5 w-5 shrink-0" />
                <p className="text-sm">
                  Company-level deal data requires DART entity matching.
                </p>
              </div>
            </Card>
          )}
        </div>
      )}

      {activeTab === "tendency" && (
        <div className="space-y-6" role="tabpanel" id="tabpanel-tendency" aria-labelledby="tab-tendency">
          {!hasCorpCode ? (
            <Card>
              <EmptyState
                icon={BarChart3}
                title="No investment data"
                description="DART entity matching required to view investment tendency."
              />
            </Card>
          ) : (
            <TendencySummary
              data={tendencySummary}
              isLoading={tendencySummaryLoading}
            />
          )}
        </div>
      )}

      {activeTab === "managers" && (
        <div role="tabpanel" id="tabpanel-managers" aria-labelledby="tab-managers">
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
                data={managers.map((m) => ({
                  ...m,
                  _id: `${m.manager_name}-${m.position ?? ""}-${m.appointed_date ?? ""}`,
                }))}
                keyField="_id"
                compact
                striped
              />
            )}
          </Card>
        </div>
      )}
    </div>
  );
}
