/** GP Research 타입 정의 — Master-Detail UI 전용 */

export type LicenseType = "pef" | "vc" | "nta";
export type SponsorType =
  | "independent"
  | "financial_group"
  | "corporate_cvc"
  | "holding_cvc";

/* ── 차트 데이터 포인트 ── */

export interface FundHistoryPoint {
  year: number;
  commitAmount: number; // 억 원 (Bar)
  cumAum: number; // 억 원 (Line)
}

export interface IRRScatterPoint {
  fundName: string;
  fundSize: number; // 억 원
  grossIrr: number; // %
  vintage: number;
}

export interface SectorAllocationPoint {
  sector: string;
  value: number; // 억 원
}

/* ── 상세 카드 ── */

export interface PortfolioCompanyCard {
  name: string;
  sector: string;
  investDate: string;
  investAmount: number; // 억 원
  coGPs: string[];
  status: "active" | "exited" | "written_off";
}

export interface KeyManInfo {
  name: string;
  title: string;
  yearsExperience: number;
  education: string;
  previousFirm?: string;
  trackRecord: string[];
}

export interface NewsTimelineItem {
  date: string;
  title: string;
  source: string;
  sentiment: "positive" | "neutral" | "negative";
}

/* ── 마스터 아이템 ── */

export interface GPResearchItem {
  id: string;
  name: string;
  nameEn?: string;
  logoUrl?: string;
  established: string; // "2010.03"
  licenses: LicenseType[];
  sponsorType: SponsorType;
  cumAum: number; // 억 원
  activeFundCount: number;
  totalFundCount: number;
  portfolioCompanyCount: number;
  estimatedDryPowder: number; // 억 원
  keyPerson: string;

  // Detail 데이터
  fundHistory: FundHistoryPoint[];
  irrScatter: IRRScatterPoint[];
  sectorAllocation: SectorAllocationPoint[];
  portfolioCompanies: PortfolioCompanyCard[];
  keyManList: KeyManInfo[];
  newsTimeline: NewsTimelineItem[];
}

/* ── 라벨 매핑 ── */

export const LICENSE_LABELS: Record<LicenseType, string> = {
  pef: "PEF GP (기관전용사모)",
  vc: "VC GP (벤처투자)",
  nta: "신기사 GP (신기술사업)",
};

export const LICENSE_SHORT_LABELS: Record<LicenseType, string> = {
  pef: "PEF",
  vc: "VC",
  nta: "신기사",
};

export const SPONSOR_LABELS: Record<SponsorType, string> = {
  independent: "독립계",
  financial_group: "금융지주계열",
  corporate_cvc: "일반기업 CVC",
  holding_cvc: "지주회사 CVC",
};

export const SPONSOR_BADGE_VARIANT: Record<
  SponsorType,
  "info" | "success" | "warning" | "neutral"
> = {
  independent: "info",
  financial_group: "success",
  corporate_cvc: "warning",
  holding_cvc: "neutral",
};

/* ── deal-mgmt GP 프로필 연동 ── */

/** deal-mgmt /pef-registry/gp-profiles API 응답 타입 */
export interface GpProfileFromMA {
  id: string;
  raw_name: string;
  logo_url?: string | null;
  total_committed_sum: number | null;
  recent_pef_count: number | null;
  total_pef_count: number | null;
  portfolio_sectors: string[] | null;
  portfolio_companies: string[] | null;
  yearly_pef_counts: Record<string, number> | null;
}

/** GpProfileFromMA → GPResearchItem 변환 어댑터 */
export function adaptGpProfileToResearchItem(
  gp: GpProfileFromMA,
): GPResearchItem {
  return {
    id: gp.id,
    name: gp.raw_name,
    logoUrl: gp.logo_url ?? undefined,
    established: "-",
    licenses: ["pef"],
    sponsorType: "independent",
    cumAum: gp.total_committed_sum ?? 0,
    activeFundCount: gp.recent_pef_count ?? 0,
    totalFundCount: gp.total_pef_count ?? 0,
    portfolioCompanyCount: gp.portfolio_companies?.length ?? 0,
    estimatedDryPowder: 0,
    keyPerson: "-",
    fundHistory: Object.entries(gp.yearly_pef_counts ?? {}).map(
      ([year, count]) => ({
        year: Number(year),
        commitAmount: count,
        cumAum: 0,
      }),
    ),
    irrScatter: [],
    sectorAllocation: (gp.portfolio_sectors ?? []).map((sector) => ({
      sector,
      value: 0,
    })),
    portfolioCompanies: (gp.portfolio_companies ?? []).map((name) => ({
      name,
      sector: "-",
      investDate: "-",
      investAmount: 0,
      coGPs: [],
      status: "active" as const,
    })),
    keyManList: [],
    newsTimeline: [],
  };
}
