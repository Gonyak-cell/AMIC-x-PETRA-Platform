import { useState } from "react";
import {
  Building2,
  Users,
  Calendar,
  Banknote,
  ExternalLink,
} from "lucide-react";

import { Badge, KpiCard, Tabs } from "@/components/ui";
import type { TabItem } from "@/components/ui";
import { SlidePanel } from "@/components/ui/SlidePanel";
import { useSIDeepDive } from "@/modules/ma/hooks/useSIMapping";
import type {
  FinancialSummary,
  SanctionItem,
} from "@/modules/ma/types/si_mapping";
import {
  formatDate,
  formatKRW,
  formatRevenue,
} from "@/modules/ma/utils/format";

interface SIDetailPanelProps {
  companyId: string | null;
  onClose: () => void;
}

const DETAIL_TABS: TabItem[] = [
  { id: "overview", label: "기업 개요", icon: Building2 },
  { id: "financials", label: "재무 정보", icon: Banknote },
  { id: "disclosures", label: "공시 & 제재", icon: ExternalLink },
];

// ── 시장구분 뱃지 ──────────────────────────────────────
const MARKET_VARIANT: Record<string, "success" | "info" | "warning"> = {
  P: "success",
  K: "info",
  N: "warning",
};

export default function SIDetailPanel({
  companyId,
  onClose,
}: SIDetailPanelProps) {
  const { data, isLoading, isError } = useSIDeepDive(companyId);
  const [activeTab, setActiveTab] = useState("overview");

  const company = data?.company;
  const overview = data?.overview;

  return (
    <SlidePanel
      open={!!companyId}
      onClose={onClose}
      title={company?.company_name ?? "로딩 중..."}
      subtitle={
        company
          ? [company.industry_name, company.market_type_name]
              .filter(Boolean)
              .join(" · ") || undefined
          : undefined
      }
      width="xl"
      headerActions={
        company?.market_type ? (
          <Badge variant={MARKET_VARIANT[company.market_type] ?? "info"} pill>
            {company.market_type_name || company.market_type}
          </Badge>
        ) : undefined
      }
    >
      {isLoading ? (
        <div className="flex items-center justify-center py-20" role="status">
          <div className="h-6 w-6 animate-spin rounded-full border-2 border-accent border-t-transparent" />
          <span className="ml-2 text-sm text-text-secondary">
            데이터 조회 중...
          </span>
        </div>
      ) : isError ? (
        <div className="rounded-dr border border-negative/20 bg-red-50/30 p-6 text-center text-sm text-negative">
          데이터를 불러오는 중 오류가 발생했습니다. 잠시 후 다시 시도해 주세요.
        </div>
      ) : !data ? (
        <div className="rounded-dr border border-gray-border bg-bg-secondary p-6 text-center text-sm text-text-secondary">
          기업 데이터를 불러올 수 없습니다.
        </div>
      ) : (
        <div className="space-y-6">
          {/* ── KPI 카드 ── */}
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
            <KpiCard
              title="매출액"
              icon={Banknote}
              value={formatRevenue(
                company?.revenue ?? null,
                company?.revenue_year,
              )}
            />
            <KpiCard
              title="종업원수"
              icon={Users}
              value={company?.employee_count || "-"}
            />
            <KpiCard
              title="설립연도"
              icon={Calendar}
              value={
                company?.founded_date
                  ? company.founded_date.slice(0, 4) + "년"
                  : "-"
              }
            />
            <KpiCard
              title="투자이력"
              icon={Building2}
              value={company?.has_investment_history ? "있음" : "없음"}
              variant={company?.has_investment_history ? "positive" : "default"}
            />
          </div>

          {/* ── 탭 ── */}
          <Tabs
            tabs={DETAIL_TABS}
            activeTab={activeTab}
            onTabChange={setActiveTab}
            variant="underline"
            size="sm"
          />

          {/* ── 탭 콘텐츠 ── */}
          <div
            role="tabpanel"
            id={`tabpanel-${activeTab}`}
            aria-labelledby={`tab-${activeTab}`}
          >
            {activeTab === "overview" && (
              <OverviewTab company={company!} overview={overview ?? null} />
            )}
            {activeTab === "financials" && (
              <FinancialsTab financials={data.financials} />
            )}
            {activeTab === "disclosures" && (
              <DisclosuresTab
                disclosures={data.disclosures}
                sanctions={data.sanctions}
              />
            )}
          </div>
        </div>
      )}
    </SlidePanel>
  );
}

// ── 기업 개요 탭 ──────────────────────────────────────────

function OverviewTab({
  company,
  overview,
}: {
  company: NonNullable<ReturnType<typeof useSIDeepDive>["data"]>["company"];
  overview: NonNullable<ReturnType<typeof useSIDeepDive>["data"]>["overview"];
}) {
  return (
    <div className="space-y-5">
      <InfoSection title="기업 정보">
        <InfoGrid>
          <InfoItem
            label="대표자"
            value={company.representative || overview?.ceo_nm}
          />
          <InfoItem
            label="설립일"
            value={formatDate(company.founded_date || overview?.est_dt || "")}
          />
          <InfoItem label="업종명" value={company.industry_name} />
          <InfoItem label="KSIC" value={company.ksic_codes?.join(", ")} />
          <InfoItem
            label="주소"
            value={company.address || overview?.adres}
            wide
          />
          <InfoItem label="주요사업" value={company.main_business} wide />
        </InfoGrid>
      </InfoSection>

      {/* 홈페이지 */}
      {(company.homepage || overview?.hm_url) && (
        <InfoSection title="홈페이지">
          <a
            href={
              (company.homepage || overview?.hm_url || "").startsWith("http")
                ? (company.homepage || overview?.hm_url)!
                : `https://${company.homepage || overview?.hm_url}`
            }
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1.5 text-sm text-accent hover:underline"
          >
            {company.homepage || overview?.hm_url}
            <ExternalLink className="h-3.5 w-3.5" />
          </a>
        </InfoSection>
      )}
    </div>
  );
}

// ── 재무 정보 탭 ──────────────────────────────────────────

function FinancialsTab({ financials }: { financials: FinancialSummary[] }) {
  if (financials.length === 0) {
    return (
      <div className="rounded-dr border border-gray-border bg-bg-secondary p-6 text-center text-sm text-text-secondary">
        재무 데이터가 없습니다. DART 연동을 확인하세요.
      </div>
    );
  }

  return (
    <div className="overflow-x-auto rounded-dr border border-gray-border">
      <table className="w-full text-right text-sm">
        <thead className="border-b border-gray-border bg-bg-secondary">
          <tr>
            <th className="px-3 py-2.5 text-left text-kpi-label text-text-secondary">
              연도
            </th>
            <th className="px-3 py-2.5 text-kpi-label text-text-secondary">
              매출액
            </th>
            <th className="px-3 py-2.5 text-kpi-label text-text-secondary">
              영업이익
            </th>
            <th className="px-3 py-2.5 text-kpi-label text-text-secondary">
              순이익
            </th>
            <th className="px-3 py-2.5 text-kpi-label text-text-secondary">
              총자산
            </th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-border">
          {financials.map((f) => (
            <tr
              key={f.bsns_year}
              className="hover:bg-bg-secondary/50 transition-colors"
            >
              <td className="px-3 py-2.5 text-left font-medium text-text-dark">
                {f.bsns_year}
              </td>
              <td className="px-3 py-2.5 font-mono tabular-nums">
                {formatKRW(f.revenue)}
              </td>
              <td className="px-3 py-2.5 font-mono tabular-nums">
                {formatKRW(f.operating_income)}
              </td>
              <td className="px-3 py-2.5 font-mono tabular-nums">
                {formatKRW(f.net_income)}
              </td>
              <td className="px-3 py-2.5 font-mono tabular-nums">
                {formatKRW(f.total_assets)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ── 공시 & 제재 탭 ────────────────────────────────────────

function DisclosuresTab({
  disclosures,
  sanctions,
}: {
  disclosures: NonNullable<
    ReturnType<typeof useSIDeepDive>["data"]
  >["disclosures"];
  sanctions: SanctionItem[];
}) {
  const hasAny = disclosures.length > 0 || sanctions.length > 0;

  if (!hasAny) {
    return (
      <div className="rounded-dr border border-gray-border bg-bg-secondary p-6 text-center text-sm text-text-secondary">
        공시 및 제재 내역이 없습니다.
      </div>
    );
  }

  return (
    <div className="space-y-5">
      {/* M&A 관련 공시 */}
      {disclosures.length > 0 && (
        <InfoSection title={`M&A 관련 공시 (${disclosures.length}건)`}>
          <ul className="space-y-2">
            {disclosures.map((d) => (
              <li key={d.rcept_no} className="flex items-start gap-2 text-sm">
                <span className="flex-shrink-0 text-text-secondary">
                  {formatDate(d.rcept_dt)}
                </span>
                <a
                  href={`https://dart.fss.or.kr/dsaf001/main.do?rcpNo=${d.rcept_no}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-text-dark hover:text-accent hover:underline"
                >
                  {d.report_nm}
                </a>
              </li>
            ))}
          </ul>
        </InfoSection>
      )}

      {/* 제재 내역 */}
      {sanctions.length > 0 && (
        <InfoSection title={`제재 내역 (${sanctions.length}건)`}>
          <div className="overflow-x-auto rounded-dr border border-negative/20">
            <table className="w-full text-left text-sm">
              <thead className="border-b border-negative/20 bg-red-50/30">
                <tr>
                  <th className="px-3 py-2 font-medium text-negative">일자</th>
                  <th className="px-3 py-2 font-medium text-negative">유형</th>
                  <th className="px-3 py-2 font-medium text-negative">내용</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-negative/10">
                {sanctions.map((s, i) => (
                  <tr key={`${s.date}-${i}`} className="hover:bg-red-50/20">
                    <td className="whitespace-nowrap px-3 py-2 text-text-secondary">
                      {formatDate(s.date)}
                    </td>
                    <td className="px-3 py-2 text-text-dark">
                      {s.type || "-"}
                    </td>
                    <td className="px-3 py-2 text-text-dark">
                      {s.content || "-"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </InfoSection>
      )}
    </div>
  );
}

// ── 공통 UI 컴포넌트 ──────────────────────────────────────

function InfoSection({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div>
      <h4 className="mb-3 text-xs font-semibold uppercase tracking-wider text-text-secondary">
        {title}
      </h4>
      {children}
    </div>
  );
}

function InfoGrid({ children }: { children: React.ReactNode }) {
  return (
    <div className="grid grid-cols-2 gap-x-4 gap-y-3 text-sm">{children}</div>
  );
}

function InfoItem({
  label,
  value,
  wide,
}: {
  label: string;
  value?: string | null;
  wide?: boolean;
}) {
  return (
    <div className={wide ? "col-span-2" : ""}>
      <span className="text-xs text-text-secondary">{label}</span>
      <div className="text-text-dark">{value || "-"}</div>
    </div>
  );
}
