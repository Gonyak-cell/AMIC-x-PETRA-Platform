import { useState, useMemo } from "react";
import { useParams, useSearchParams, useNavigate, Link } from "react-router-dom";
import {
  Landmark,
  TrendingUp,
  PieChart,
  Newspaper,
  Wallet,
  BarChart3,
  Info,
  AlertCircle,
} from "lucide-react";
import { useFunds } from "@/modules/kiis/hooks/useFunds";
import { useCompanies } from "@/modules/kiis/hooks/useCompanies";
import { useQualitativeReputation } from "@/modules/kiis/hooks/useCompanies";
import {
  useDealsByCompany,
  useDealTrends,
  useDealStats,
  useTendencySummary,
} from "@/modules/kiis/hooks/useDeals";
import { useNewsList } from "@/modules/kiis/hooks/useNews";
import {
  Card,
  KpiCard,
  DataTable,
  Badge,
  Spinner,
  EmptyState,
  PageHero,
  Tabs,
  Pagination,
} from "@/components/ui";
import type { Column, TabItem } from "@/components/ui";
import ReputationSummary from "@/modules/kiis/components/ReputationSummary";
import TendencySummary from "@/modules/kiis/components/TendencySummary";
import DealTrendChart from "@/modules/kiis/components/DealTrendChart";
import { FinancialBarChart } from "@/components/charts/FinancialBarChart";
import type { BarChartDataPoint } from "@/components/charts/FinancialBarChart";
import type { FundListItem } from "@/modules/kiis/types/fund";
import type { DealItem } from "@/modules/kiis/types/deal";
import { formatAmount, formatDate } from "@/lib/format";
import {
  ASSET_CLASS_BADGE_VARIANT,
  ASSET_CLASS_LABELS,
  FUND_STATUS_BADGE_VARIANT,
  FUND_STATUS_LABELS,
} from "@/modules/kiis/constants/fundFilters";

/* ───────── Column definitions ───────── */

const fundColumns: Column<FundListItem>[] = [
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
  {
    key: "asset_class",
    header: "Class",
    align: "center",
    width: "90px",
    render: (row) => (
      <Badge variant={ASSET_CLASS_BADGE_VARIANT[row.asset_class] ?? "neutral"}>
        {ASSET_CLASS_LABELS[row.asset_class] ?? row.asset_class}
      </Badge>
    ),
  },
  {
    key: "fund_status",
    header: "Status",
    align: "center",
    width: "90px",
    render: (row) => (
      <Badge variant={FUND_STATUS_BADGE_VARIANT[row.fund_status] ?? "neutral"}>
        {FUND_STATUS_LABELS[row.fund_status] ?? row.fund_status}
      </Badge>
    ),
  },
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
  { id: "funds", label: "Funds", icon: Wallet },
  { id: "deals", label: "Deal History", icon: TrendingUp },
  { id: "tendency", label: "Investment Tendency", icon: PieChart },
  { id: "news", label: "News", icon: Newspaper },
];

/* ───────── Page ───────── */

export default function GPDetailPage() {
  const { companyCode } = useParams<{ companyCode: string }>();
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState("overview");
  const [fundPage, setFundPage] = useState(1);

  // company_name: 쿼리 파라미터 > URL 디코드
  const gpName = searchParams.get("name") ?? decodeURIComponent(companyCode ?? "");

  // 1. 이 GP의 펀드 목록
  const { data: fundsData, isLoading: fundsLoading } = useFunds({
    company_name: gpName,
    page: fundPage,
    size: 20,
  });

  // 2. DART 회사 검색 → corp_code 확보
  const { data: companyData } = useCompanies({ search: gpName, size: 1 });
  const corpCode = useMemo(() => {
    const match = companyData?.items?.[0];
    if (match && match.corp_name.includes(gpName.slice(0, 3))) {
      return match.corp_code;
    }
    return "";
  }, [companyData, gpName]);

  const hasCorpCode = /^\d{8}$/.test(corpCode);
  const companyId = companyData?.items?.[0]?.id;

  // 3. 분석 데이터 (corp_code 기반)
  const { data: qualitativeReputation, isLoading: qualRepLoading } =
    useQualitativeReputation(corpCode, {}, { enabled: hasCorpCode });
  const { data: deals } = useDealsByCompany(corpCode, { size: 50 });
  const { data: trends } = useDealTrends(
    { corp_code: corpCode },
    { enabled: hasCorpCode },
  );
  const { data: dealStats } = useDealStats(corpCode, 5, {
    enabled: hasCorpCode,
  });
  const { data: tendencySummary, isLoading: tendencyLoading } =
    useTendencySummary(corpCode, 3, { enabled: hasCorpCode });

  // 4. 뉴스 (company_id 기반)
  const { data: newsData } = useNewsList(
    companyId ? { company_id: companyId, size: 10 } : {},
  );

  // GP 메트릭 집계 (펀드 데이터에서)
  const gpMetrics = useMemo(() => {
    const items = fundsData?.items ?? [];
    const totalAum = items.reduce((sum, f) => {
      const amount = f.total_amount ? parseFloat(f.total_amount) : 0;
      return sum + amount;
    }, 0);
    const activeCount = items.filter((f) => f.fund_status === "active").length;
    return {
      fundCount: fundsData?.total ?? 0,
      activeCount,
      totalAum,
      dealCount: deals?.length ?? 0,
    };
  }, [fundsData, deals]);

  if (fundsLoading) return <Spinner />;

  return (
    <div className="space-y-6">
      {/* Breadcrumb */}
      <div className="text-sm text-text-secondary">
        <Link to="/kiis/funds" className="hover:text-accent">
          GPs & Funds
        </Link>
        <span className="mx-2">/</span>
        <span className="text-text-dark">{gpName}</span>
        {hasCorpCode && (
          <>
            <span className="mx-2">·</span>
            <Link to={`/kiis/companies/${corpCode}`} className="hover:text-accent">
              DART Profile →
            </Link>
          </>
        )}
      </div>

      {/* Header */}
      <PageHero
        title={gpName}
        subtitle="운용사 프로필"
        compact
        actions={
          hasCorpCode ? (
            <Link
              to={`/kiis/companies/${corpCode}`}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-dr-sm text-sm font-medium text-accent border border-accent/30 hover:bg-accent/10 transition-colors"
            >
              <Landmark className="h-4 w-4" />
              DART 기업 정보
            </Link>
          ) : undefined
        }
      />

      {/* KPI Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <KpiCard
          label="운용 펀드 수"
          value={String(gpMetrics.fundCount)}
          icon={Wallet}
        />
        <KpiCard
          label="총 AUM"
          value={formatAmount(gpMetrics.totalAum, "KRW")}
          icon={Landmark}
        />
        <KpiCard
          label="Active 펀드"
          value={String(gpMetrics.activeCount)}
          icon={BarChart3}
        />
        <KpiCard
          label="총 딜 수"
          value={hasCorpCode ? String(gpMetrics.dealCount) : "-"}
          icon={TrendingUp}
        />
      </div>

      {/* Tabs */}
      <Tabs tabs={TABS} activeTab={activeTab} onTabChange={setActiveTab} />

      {/* ─── Overview Tab ─── */}
      {activeTab === "overview" && (
        <div className="space-y-6" role="tabpanel" id="tabpanel-overview" aria-labelledby="tab-overview">
          {!hasCorpCode && (
            <Card>
              <div className="flex items-center gap-3 text-text-secondary">
                <Info className="h-5 w-5 shrink-0" />
                <p className="text-sm">
                  이 운용사가 DART 엔티티에 매칭되지 않아 업계 평판, 딜 히스토리,
                  투자 성향 데이터를 표시할 수 없습니다. Entity Match 메뉴에서
                  매칭을 수행해 주세요.
                </p>
              </div>
            </Card>
          )}

          {hasCorpCode && (
            <ReputationSummary
              data={qualitativeReputation}
              isLoading={qualRepLoading}
            />
          )}

          {hasCorpCode && trends && trends.length > 0 && (
            <Card title="Deal Trends" headerBar>
              <DealTrendChart data={trends} height={280} />
            </Card>
          )}

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
                  value={formatAmount(dealStats.avg_amount, "KRW")}
                />
                <KpiCard
                  label="Median Amount"
                  value={formatAmount(dealStats.median_amount, "KRW")}
                />
                <KpiCard
                  label="Max Amount"
                  value={formatAmount(dealStats.max_amount, "KRW")}
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

      {/* ─── Funds Tab ─── */}
      {activeTab === "funds" && (
        <div className="space-y-4" role="tabpanel" id="tabpanel-funds" aria-labelledby="tab-funds">
          <Card padding="none">
            {!fundsData?.items.length ? (
              <EmptyState
                icon={Wallet}
                title="펀드 없음"
                description="이 운용사의 펀드 정보가 없습니다."
              />
            ) : (
              <DataTable
                columns={fundColumns}
                data={fundsData.items}
                keyField="fund_code"
                loading={fundsLoading}
                onRowClick={(row) => navigate(`/kiis/funds/${row.fund_code}`)}
                striped
              />
            )}
          </Card>

          <Pagination
            page={fundPage}
            totalPages={fundsData ? Math.ceil(fundsData.total / 20) : 0}
            onPageChange={setFundPage}
          />
        </div>
      )}

      {/* ─── Deals Tab ─── */}
      {activeTab === "deals" && (
        <div role="tabpanel" id="tabpanel-deals" aria-labelledby="tab-deals">
          {!hasCorpCode ? (
            <Card>
              <EmptyState
                icon={TrendingUp}
                title="딜 데이터 없음"
                description="DART 엔티티 매칭이 필요합니다."
              />
            </Card>
          ) : !deals?.length ? (
            <Card>
              <EmptyState
                icon={TrendingUp}
                title="딜 없음"
                description="이 운용사의 딜 히스토리가 없습니다."
              />
            </Card>
          ) : (
            <Card title="Deal History" headerBar padding="none">
              <DataTable
                columns={dealColumns}
                data={deals}
                keyField="id"
                compact
                striped
              />
            </Card>
          )}
        </div>
      )}

      {/* ─── Tendency Tab ─── */}
      {activeTab === "tendency" && (
        <div role="tabpanel" id="tabpanel-tendency" aria-labelledby="tab-tendency">
          {!hasCorpCode ? (
            <Card>
              <EmptyState
                icon={PieChart}
                title="투자 성향 데이터 없음"
                description="DART 엔티티 매칭이 필요합니다."
              />
            </Card>
          ) : (
            <TendencySummary
              data={tendencySummary}
              isLoading={tendencyLoading}
            />
          )}
        </div>
      )}

      {/* ─── News Tab ─── */}
      {activeTab === "news" && (
        <div role="tabpanel" id="tabpanel-news" aria-labelledby="tab-news">
          {!companyId ? (
            <Card>
              <EmptyState
                icon={Newspaper}
                title="뉴스 데이터 없음"
                description="DART 엔티티 매칭이 필요합니다."
              />
            </Card>
          ) : !newsData?.items.length ? (
            <Card>
              <EmptyState
                icon={Newspaper}
                title="뉴스 없음"
                description="이 운용사 관련 뉴스가 없습니다."
              />
            </Card>
          ) : (
            <Card title="Related News" headerBar>
              <div className="divide-y divide-border">
                {newsData.items.map((article) => (
                  <Link
                    key={article.id}
                    to={`/kiis/news/${article.id}`}
                    className="block px-4 py-3 hover:bg-surface-alt transition-colors"
                  >
                    <p className="text-sm font-medium text-text-dark line-clamp-1">
                      {article.title}
                    </p>
                    <div className="flex items-center gap-2 mt-1 text-xs text-text-secondary">
                      <span>{article.source}</span>
                      <span>·</span>
                      <span>
                        {article.published_at
                          ? formatDate(article.published_at, "short")
                          : "-"}
                      </span>
                    </div>
                  </Link>
                ))}
              </div>
            </Card>
          )}
        </div>
      )}
    </div>
  );
}
