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
