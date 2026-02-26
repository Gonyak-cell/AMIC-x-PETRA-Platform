import { useParams, Link, useNavigate } from "react-router-dom";
import {
  Building2,
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
  useCorpBasicInfo,
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
import type { AffiliateItem, SubsidiaryItem } from "@/modules/kiis/types/company";
import { formatDate } from "@/lib/format";
import { SEVERITY_VARIANT, LISTING_STATUS_VARIANT } from "@/modules/kiis/constants/variants";
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

const affiliateColumns: Column<AffiliateItem>[] = [
  {
    key: "afil_cmpy_nm",
    header: "회사명",
    render: (row) => (
      <span className="font-medium text-text-dark">{row.afil_cmpy_nm}</span>
    ),
  },
  {
    key: "afil_cmpy_crno",
    header: "법인등록번호",
    width: "160px",
    render: (row) => row.afil_cmpy_crno || "-",
  },
  {
    key: "lstg_yn",
    header: "상장여부",
    align: "center",
    width: "100px",
    render: (row) => (
      <Badge variant={LISTING_STATUS_VARIANT[row.lstg_yn] ?? "neutral"}>
        {row.lstg_yn || "-"}
      </Badge>
    ),
  },
];

const subsidiaryColumns: Column<SubsidiaryItem>[] = [
  {
    key: "sbrd_enp_nm",
    header: "기업명",
    render: (row) => (
      <span className="font-medium text-text-dark">{row.sbrd_enp_nm}</span>
    ),
  },
  {
    key: "sbrd_enp_main_biz",
    header: "주요사업",
    render: (row) => row.sbrd_enp_main_biz || "-",
  },
  {
    key: "sbrd_enp_tast_amt",
    header: "총자산",
    align: "right",
    width: "120px",
    mono: true,
    render: (row) => row.sbrd_enp_tast_amt || "-",
  },
  {
    key: "dnt_rlt_bsis",
    header: "지배근거",
    width: "140px",
    render: (row) => row.dnt_rlt_bsis || "-",
  },
  {
    key: "main_sbrd_enp_yn",
    header: "주요여부",
    align: "center",
    width: "100px",
    render: (row) => row.main_sbrd_enp_yn || "-",
  },
];

export default function CompanyDetailPage() {
  const navigate = useNavigate();
  const { corpCode } = useParams<{ corpCode: string }>();
  const code = corpCode ?? "";
  const { data: company, isLoading, isError } = useCompanyDetail(code);
  const { data: basicInfo, isLoading: basicInfoLoading, isError: basicInfoError } = useCorpBasicInfo(code);
  const { data: reputation, isLoading: reputationLoading, isError: reputationError } = useReputationScore(code);
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
      <Card title="Reputation Score" headerBar>
        {reputationLoading ? (
          <Spinner />
        ) : reputationError ? (
          <EmptyState
            icon={AlertTriangle}
            title="평판 점수 조회 실패"
            description="평판 분석 데이터를 불러오는 중 오류가 발생했습니다."
          />
        ) : reputation ? (
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
        ) : (
          <EmptyState
            icon={AlertTriangle}
            title="평판 점수 없음"
            description="해당 기업의 평판 분석 데이터가 아직 없습니다."
          />
        )}
      </Card>

      {/* Company Overview (공공데이터포털) */}
      <Card
        title="Company Overview"
        headerBar
        actions={<Badge variant="warning">공공데이터</Badge>}
      >
        {basicInfoLoading ? (
          <Spinner />
        ) : basicInfoError ? (
          <EmptyState
            icon={AlertTriangle}
            title="기업 기본정보 조회 실패"
            description="공공데이터포털에서 데이터를 불러오는 중 오류가 발생했습니다."
          />
        ) : basicInfo?.outline ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-x-8 gap-y-3 text-sm">
            {basicInfo.outline.rep_nm && (
              <div>
                <span className="text-text-secondary">대표자</span>
                <p className="font-medium text-text-dark">{basicInfo.outline.rep_nm}</p>
              </div>
            )}
            {basicInfo.outline.sic_nm && (
              <div>
                <span className="text-text-secondary">업종</span>
                <p className="font-medium text-text-dark">{basicInfo.outline.sic_nm}</p>
              </div>
            )}
            {basicInfo.outline.emp_cnt && basicInfo.outline.emp_cnt !== "0" && (
              <div>
                <span className="text-text-secondary">종업원수</span>
                <p className="font-medium text-text-dark">
                  {Number(basicInfo.outline.emp_cnt).toLocaleString("ko-KR")}명
                </p>
              </div>
            )}
            {basicInfo.outline.est_dt && (
              <div>
                <span className="text-text-secondary">설립일</span>
                <p className="font-medium text-text-dark">
                  {formatDate(basicInfo.outline.est_dt, "short")}
                </p>
              </div>
            )}
            {basicInfo.outline.stac_mm && (
              <div>
                <span className="text-text-secondary">결산월</span>
                <p className="font-medium text-text-dark">{basicInfo.outline.stac_mm}월</p>
              </div>
            )}
            {basicInfo.outline.mkt_dcd_nm && (
              <div>
                <span className="text-text-secondary">시장구분</span>
                <p className="font-medium text-text-dark">{basicInfo.outline.mkt_dcd_nm}</p>
              </div>
            )}
            {basicInfo.outline.audpn_nm && (
              <div>
                <span className="text-text-secondary">회계감사인</span>
                <p className="font-medium text-text-dark">{basicInfo.outline.audpn_nm}</p>
              </div>
            )}
            {basicInfo.outline.audt_opnn && (
              <div>
                <span className="text-text-secondary">감사의견</span>
                <p className="font-medium text-text-dark">{basicInfo.outline.audt_opnn}</p>
              </div>
            )}
            {basicInfo.outline.mntr_bnk_nm && (
              <div>
                <span className="text-text-secondary">주거래은행</span>
                <p className="font-medium text-text-dark">{basicInfo.outline.mntr_bnk_nm}</p>
              </div>
            )}
            {basicInfo.outline.avg_cnwk_term && (
              <div>
                <span className="text-text-secondary">평균근속연수</span>
                <p className="font-medium text-text-dark">{basicInfo.outline.avg_cnwk_term}년</p>
              </div>
            )}
            {basicInfo.outline.avg_slry_amt && basicInfo.outline.avg_slry_amt !== "0" && (
              <div>
                <span className="text-text-secondary">1인 평균급여</span>
                <p className="font-medium text-text-dark">
                  {(Number(basicInfo.outline.avg_slry_amt) / 10000).toLocaleString("ko-KR", { maximumFractionDigits: 0 })}만원
                </p>
              </div>
            )}
            {basicInfo.outline.bsadr && (
              <div className="md:col-span-2 lg:col-span-3">
                <span className="text-text-secondary">주소</span>
                <p className="font-medium text-text-dark">{basicInfo.outline.bsadr}</p>
              </div>
            )}
            {basicInfo.outline.main_biz_nm && (
              <div className="md:col-span-2 lg:col-span-3">
                <span className="text-text-secondary">주요사업</span>
                <p className="font-medium text-text-dark">{basicInfo.outline.main_biz_nm}</p>
              </div>
            )}
          </div>
        ) : (
          <EmptyState
            icon={Building2}
            title="기업 기본정보 없음"
            description="공공데이터포털에서 해당 기업의 기본정보를 조회할 수 없습니다."
          />
        )}
      </Card>

      {/* Affiliates (계열회사) */}
      <Card
        title="계열회사 (Affiliates)"
        headerBar
        padding="none"
        actions={<Badge variant="warning">공공데이터</Badge>}
      >
        {basicInfoLoading ? (
          <Spinner />
        ) : basicInfoError ? (
          <EmptyState
            icon={AlertTriangle}
            title="계열회사 조회 실패"
            description="공공데이터포털에서 데이터를 불러오는 중 오류가 발생했습니다."
          />
        ) : basicInfo?.affiliates?.length ? (
          <DataTable
            columns={affiliateColumns}
            data={basicInfo.affiliates}
            keyField="afil_cmpy_crno"
            compact
            striped
          />
        ) : (
          <EmptyState
            icon={Building2}
            title="계열회사 정보 없음"
            description="해당 기업의 계열회사 데이터가 없습니다."
          />
        )}
      </Card>

      {/* Subsidiaries (종속기업) */}
      <Card
        title="종속기업 (Subsidiaries)"
        headerBar
        padding="none"
        actions={<Badge variant="warning">공공데이터</Badge>}
      >
        {basicInfoLoading ? (
          <Spinner />
        ) : basicInfoError ? (
          <EmptyState
            icon={AlertTriangle}
            title="종속기업 조회 실패"
            description="공공데이터포털에서 데이터를 불러오는 중 오류가 발생했습니다."
          />
        ) : basicInfo?.subsidiaries?.length ? (
          <DataTable
            columns={subsidiaryColumns}
            data={basicInfo.subsidiaries}
            keyField="sbrd_enp_nm"
            compact
            striped
          />
        ) : (
          <EmptyState
            icon={Building2}
            title="종속기업 정보 없음"
            description="해당 기업의 종속기업 데이터가 없습니다."
          />
        )}
      </Card>

      {/* Financials */}
      <CompanyFinancials corpCode={code} />

      {/* Disclosures */}
      <Card
        title="Disclosures"
        headerBar
        padding="none"
        actions={
          <div className="flex items-center gap-2">
            <Badge variant="info">DART</Badge>
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
          <div className="flex items-center gap-2">
            <Badge variant="info">DART</Badge>
            <Link
              to={`/kiis/sanctions`}
              className="text-sm text-accent hover:underline"
            >
              View all
            </Link>
          </div>
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
