import { useParams, Link, useNavigate } from "react-router-dom";
import {
  ExternalLink,
  RefreshCw,
  Plus,
  AlertTriangle,
  FileText,
} from "lucide-react";
import { toast } from "sonner";
import {
  useCompanyDetail,
  useCompanyDisclosures,
  useSyncDisclosures,
  useReputationScore,
} from "@/modules/kiis/hooks/useCompanies";
import { useDealsByCompany } from "@/modules/kiis/hooks/useDeals";
import { useClassifiedSanctions } from "@/modules/kiis/hooks/useSanctions";
import { useAddToWatchlist } from "@/modules/kiis/hooks/useWatchlist";
import {
  Card,
  Button,
  DataTable,
  Badge,
  Spinner,
  EmptyState,
  KpiCard,
} from "@/components/ui";
import type { Column } from "@/components/ui";
import CompanyFinancials from "@/modules/kiis/components/CompanyFinancials";
import ReputationBadge from "@/modules/kiis/components/ReputationBadge";
import type { Disclosure } from "@/modules/kiis/types/company";
import type { DealItem } from "@/modules/kiis/types/deal";
import type { ClassifiedSanctionItem } from "@/modules/kiis/types/sanction";
import { formatDate, formatAmount } from "@/lib/format";

const disclosureColumns: Column<Disclosure>[] = [
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
    render: (row) => formatDate(row.rcept_dt, "short"),
  },
  { key: "flr_nm", header: "Filer" },
  {
    key: "viewer_url",
    header: "Link",
    align: "center",
    width: "80px",
    render: (row) =>
      row.viewer_url ? (
        <a
          href={row.viewer_url}
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

const severityVariant: Record<string, "error" | "warning" | "info"> = {
  critical: "error",
  warning: "warning",
  caution: "info",
};

const sanctionColumns: Column<ClassifiedSanctionItem>[] = [
  {
    key: "sanctions_type",
    header: "Type",
    render: (row) => (
      <span className="font-medium text-text-dark">{row.sanctions_type}</span>
    ),
  },
  { key: "sanctions_agency", header: "Agency" },
  {
    key: "severity",
    header: "Severity",
    align: "center",
    width: "100px",
    render: (row) => (
      <Badge variant={severityVariant[row.severity] ?? "neutral"}>
        {row.severity}
      </Badge>
    ),
  },
  {
    key: "sanctions_date",
    header: "Date",
    align: "center",
    width: "120px",
    render: (row) => formatDate(row.sanctions_date, "short"),
  },
];

export default function CompanyDetailPage() {
  const navigate = useNavigate();
  const { corpCode } = useParams<{ corpCode: string }>();
  const { data: company, isLoading } = useCompanyDetail(corpCode!);
  const { data: reputation } = useReputationScore(corpCode!);
  const { data: disclosures } = useCompanyDisclosures(corpCode!);
  const { data: deals } = useDealsByCompany(corpCode!);
  const { data: sanctions } = useClassifiedSanctions(corpCode!);
  const syncDisclosures = useSyncDisclosures(corpCode!);
  const addToWatchlist = useAddToWatchlist();

  if (isLoading) return <Spinner />;
  if (!company) {
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
        company_id: company.corp_code,
        corp_code: company.corp_code,
        alert_types: ["sanction", "news", "disclosure"],
      },
      {
        onSuccess: () => toast.success("Added to watchlist"),
        onError: () => toast.error("Failed to add to watchlist"),
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
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-heading font-bold text-text-dark">
            {company.corp_name}
          </h1>
          <div className="mt-1 text-sm text-text-secondary space-x-4">
            {company.stock_code && <span>Stock: {company.stock_code}</span>}
            {company.ceo_nm && <span>CEO: {company.ceo_nm}</span>}
            {company.homepage && (
              <a
                href={company.homepage}
                target="_blank"
                rel="noopener noreferrer"
                className="text-accent hover:underline inline-flex items-center gap-1"
              >
                Website <ExternalLink className="h-3 w-3" />
              </a>
            )}
          </div>
        </div>
        <div className="flex gap-2">
          <Button
            variant="primary"
            icon={FileText}
            onClick={() => navigate(`/im/new?corpCode=${corpCode}`)}
          >
            IM 생성
          </Button>
          <Button
            variant="secondary"
            icon={Plus}
            onClick={handleAddWatchlist}
            loading={addToWatchlist.isPending}
          >
            Watchlist
          </Button>
        </div>
      </div>

      {/* Reputation */}
      {reputation && (
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
      )}

      {/* Financials */}
      <CompanyFinancials corpCode={corpCode!} />

      {/* Disclosures */}
      <Card
        title="Disclosures"
        headerBar
        padding="none"
        actions={
          <Button
            variant="ghost"
            size="sm"
            icon={RefreshCw}
            onClick={handleSyncDisclosures}
            loading={syncDisclosures.isPending}
          >
            Sync
          </Button>
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
      <Card title="Related Deals" headerBar padding="none">
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
      <Card title="Sanctions" headerBar padding="none">
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
