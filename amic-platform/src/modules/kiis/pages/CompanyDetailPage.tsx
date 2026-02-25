import { useParams, Link, useNavigate } from "react-router-dom";
import {
  ExternalLink,
  RefreshCw,
  Plus,
  Check,
  AlertTriangle,
  FileText,
  Wallet,
} from "lucide-react";
import { toast } from "sonner";
import {
  useCompanyDetail,
  useReputationScore,
} from "@/modules/kiis/hooks/useCompanies";
import {
  useDisclosures,
  useSyncDartDisclosures,
} from "@/modules/kiis/hooks/useDisclosures";
import { useDealsByCompany } from "@/modules/kiis/hooks/useDeals";
import { useClassifiedSanctions } from "@/modules/kiis/hooks/useSanctions";
import { useAddToWatchlist, useWatchlist } from "@/modules/kiis/hooks/useWatchlist";
import { useGPs } from "@/modules/kiis/hooks/useGPs";
import {
  Card,
  Button,
  DataTable,
  Badge,
  Spinner,
  EmptyState,
  KpiCard,
  PageHero,
} from "@/components/ui";
import type { Column } from "@/components/ui";
import CompanyFinancials from "@/modules/kiis/components/CompanyFinancials";
import ReputationBadge from "@/modules/kiis/components/ReputationBadge";
import type { DisclosureItem } from "@/modules/kiis/types/disclosure";
import type { DealItem } from "@/modules/kiis/types/deal";
import type { ClassifiedSanctionListItem } from "@/modules/kiis/types/sanction";
import { formatDate } from "@/lib/format";
import { SEVERITY_VARIANT } from "@/modules/kiis/constants/variants";
import heroImg from "@/assets/images/heroes/forestgp-forest.jpg";

const disclosureColumns: Column<DisclosureItem>[] = [
  {
    key: "report_nm",
    header: "Report",
    render: (row) => (
      <span className="font-medium text-text-dark">{row.report_nm}</span>
    ),
  },
  {
    key: "rcept_dt",
    header: "Filed",
    align: "center",
    width: "120px",
    render: (row) => (row.rcept_dt ? formatDate(row.rcept_dt, "short") : "-"),
  },
  {
    key: "disclosure_type",
    header: "Type",
    render: (row) => row.disclosure_type ?? "-",
  },
  {
    key: "source",
    header: "Source",
    align: "center",
    width: "80px",
    render: (row) => <Badge variant="info">{row.source}</Badge>,
  },
  {
    key: "dart_viewer_url",
    header: "Link",
    align: "center",
    width: "80px",
    render: (row) =>
      row.dart_viewer_url ? (
        <a
          href={row.dart_viewer_url}
          target="_blank"
          rel="noopener noreferrer"
          className="text-accent hover:underline inline-flex items-center gap-1"
          onClick={(e) => e.stopPropagation()}
        >
          <ExternalLink className="h-3.5 w-3.5" />
        </a>
      ) : (
        "-"
      ),
  },
];

const dealColumns: Column<DealItem>[] = [
  {
    key: "investor_name",
    header: "Investor",
    render: (row) => (
      <span className="font-medium text-text-dark">{row.investor_name}</span>
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
    render: (row) => formatDate(row.deal_date, "short"),
  },
];

const sanctionColumns: Column<ClassifiedSanctionListItem>[] = [
  {
    key: "sanctions_type",
    header: "Type",
    render: (row) => (
      <span className="font-medium text-text-dark">{row.sanctions_type}</span>
    ),
  },
  {
    key: "category",
    header: "Category",
    render: (row) => row.category ?? "-",
  },
  {
    key: "severity",
    header: "Severity",
    align: "center",
    width: "100px",
    render: (row) => (
      <Badge variant={SEVERITY_VARIANT[row.severity] ?? "neutral"}>
        {row.severity}
      </Badge>
    ),
  },
  {
    key: "sanctions_date",
    header: "Date",
    align: "center",
    width: "120px",
    render: (row) =>
      row.sanctions_date ? formatDate(row.sanctions_date, "short") : "-",
  },
];

export default function CompanyDetailPage() {
  const navigate = useNavigate();
  const { corpCode } = useParams<{ corpCode: string }>();
  const code = corpCode ?? "";
  const { data: company, isLoading, isError } = useCompanyDetail(code);
  const { data: reputation, isLoading: reputationLoading } = useReputationScore(code);
  const { data: disclosureData } = useDisclosures(code, { size: 5 });
  const disclosures = disclosureData?.items;
  const { data: deals } = useDealsByCompany(code, { size: 5 });
  const { data: sanctionsData } = useClassifiedSanctions(code, { size: 5 });
  const sanctions = sanctionsData?.items;
  const syncDisclosures = useSyncDartDisclosures(code);
  const addToWatchlist = useAddToWatchlist();
  const { data: watchlistData, isLoading: watchlistLoading } = useWatchlist();
  const isWatched = watchlistData?.items.some((w) => w.company_id === company?.id);

  // KOFIA GP 매칭: 기업명으로 운용사 검색
  const { data: gpData } = useGPs(
    company ? { company_name: company.corp_name, size: 1 } : { size: 0 },
  );
  const matchedGP = gpData?.items?.[0];

  if (isLoading) return <Spinner />;
  if (isError || !company) {
    return (
      <EmptyState
        icon={AlertTriangle}
        title="Company not found"
        description="The requested company could not be found."
      />
    );
  }

  const handleAddWatchlist = () => {
    addToWatchlist.mutate(
      {
        company_id: company.id,
        alert_types: ["new_disclosure", "reputation_change"],
      },
      {
        onSuccess: () => toast.success("Added to watchlist"),
        onError: (err: Error) =>
          toast.error(`Failed to add to watchlist: ${err.message}`),
      },
    );
  };

  const handleSyncDisclosures = () => {
    syncDisclosures.mutate(undefined, {
      onSuccess: () => toast.success("Disclosures synced"),
      onError: () => toast.error("Failed to sync disclosures"),
    });
  };

  return (
    <div className="space-y-6">
      {/* Breadcrumb */}
      <div className="text-sm text-text-secondary">
        <Link to="/kiis/companies" className="hover:text-accent">
          Companies
        </Link>
        <span className="mx-2">/</span>
        <span className="text-text-dark">{company.corp_name}</span>
      </div>

      {/* Header */}
      <PageHero
        title={company.corp_name}
        subtitle={[
          company.stock_code && `Stock: ${company.stock_code}`,
          company.ceo_nm && `CEO: ${company.ceo_nm}`,
        ].filter(Boolean).join(" | ") || undefined}
        compact
        backgroundImage={heroImg}
        backgroundOpacity={0.18}
        actions={
          <>
            {matchedGP && (
              <Link
                to={`/kiis/funds/gp/${encodeURIComponent(matchedGP.company_code || matchedGP.company_name)}?name=${encodeURIComponent(matchedGP.company_name)}`}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-dr-sm text-sm font-medium text-accent border border-accent/30 hover:bg-accent/10 transition-colors"
              >
                <Wallet className="h-4 w-4" />
                KOFIA 펀드 ({matchedGP.fund_count})
              </Link>
            )}
            <Button
              variant="primary"
              icon={FileText}
              onClick={() => navigate(`/im/new?corpCode=${corpCode}`)}
            >
              IM 생성
            </Button>
            <Button
              variant={isWatched ? "ghost" : "secondary"}
              icon={isWatched ? Check : Plus}
              onClick={isWatched ? undefined : handleAddWatchlist}
              disabled={isWatched || watchlistLoading}
              loading={addToWatchlist.isPending}
            >
              {isWatched ? "Watched" : "Watchlist"}
            </Button>
          </>
        }
      />

      {/* Reputation */}
      {reputationLoading ? (
        <Card title="Reputation Score" headerBar>
          <Spinner />
        </Card>
      ) : reputation ? (
        <Card title="Reputation Score" headerBar>
          <div className="flex items-center gap-6">
            <ReputationBadge
              score={reputation.total_score}
              statusTag={reputation.status_tag}
              className="text-lg px-3 py-1"
            />
            <div className="grid grid-cols-3 gap-4">
              <KpiCard
                label="Trend"
                value={reputation.trend_score.toFixed(1)}
              />
              <KpiCard
                label="News"
                value={reputation.news_score.toFixed(1)}
              />
              <KpiCard
                label="Performance"
                value={reputation.performance_score.toFixed(1)}
              />
            </div>
          </div>
        </Card>
      ) : null}

      {/* Financials */}
      <CompanyFinancials corpCode={code} />

      {/* Disclosures */}
      <Card
        title="Disclosures"
        headerBar
        padding="none"
        actions={
          <div className="flex gap-2">
            <Button
              variant="ghost"
              size="sm"
              icon={RefreshCw}
              onClick={handleSyncDisclosures}
              loading={syncDisclosures.isPending}
            >
              Sync
            </Button>
            <Link
              to={`/kiis/disclosures?corpCode=${corpCode}`}
              className="text-sm text-accent hover:underline self-center"
            >
              View all
            </Link>
          </div>
        }
      >
        {!disclosures?.length ? (
          <EmptyState
            icon={FileText}
            title="No disclosures"
            description="Sync disclosures to see the latest filings."
          />
        ) : (
          <DataTable
            columns={disclosureColumns}
            data={disclosures}
            keyField="rcept_no"
            compact
            striped
          />
        )}
      </Card>

      {/* Related Deals */}
      <Card
        title="Related Deals"
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
            icon={AlertTriangle}
            title="No deal data"
            description="No deals found for this company."
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

      {/* Sanctions */}
      <Card
        title="Sanctions"
        headerBar
        padding="none"
        actions={
          <Link
            to={`/kiis/sanctions`}
            className="text-sm text-accent hover:underline"
          >
            View all
          </Link>
        }
      >
        {!sanctions?.length ? (
          <EmptyState
            icon={AlertTriangle}
            title="No sanctions"
            description="No classified sanctions for this company."
          />
        ) : (
          <DataTable
            columns={sanctionColumns}
            data={sanctions}
            keyField="id"
            compact
            striped
          />
        )}
      </Card>
    </div>
  );
}
