/** 딜 아이템 (GET /deals/by-company/{corpCode} → items[]) */
export interface DealItem {
  id: number;
  company_id: number | null;
  investor_name: string | null;
  target_company: string;
  target_company_id: number | null;
  amount: string | null;
  amount_display: string | null;
  round_stage: string | null;
  sector: string | null;
  deal_date: string | null;
  deal_year: number | null;
  source_url: string | null;
  source_type: string | null;
  is_lead_investor: boolean;
  fund_id: number | null;
  fund_code: string | null;
  fund_name: string | null;
}

/** 딜 목록 아이템 (축약) */
export interface DealListItem {
  id: number;
  target_company: string;
  amount_display: string | null;
  round_stage: string | null;
  sector: string | null;
  deal_date: string | null;
}

/** 딜 목록 래퍼 응답 */
export interface DealListResponse {
  total: number;
  page: number;
  size: number;
  items: DealItem[];
}

/** 섹터별 집계 */
export interface SectorAggregation {
  sector: string;
  sector_name: string;
  deal_count: number;
  total_amount: string | null;
}

/** 섹터별 집계 래퍼 응답 */
export interface SectorAggregationResponse {
  total_deals: number;
  items: SectorAggregation[];
}

/** 스테이지별 집계 */
export interface StageAggregation {
  stage: string;
  stage_name: string;
  deal_count: number;
  total_amount: string | null;
}

/** 스테이지별 집계 래퍼 응답 */
export interface StageAggregationResponse {
  total_deals: number;
  items: StageAggregation[];
}

/** 연도별 트렌드 */
export interface YearlyTrend {
  year: number;
  deal_count: number;
  total_amount: string | null;
}

/** 트렌드 래퍼 응답 */
export interface TrendResponse {
  corp_code: string | null;
  corp_name: string | null;
  items: YearlyTrend[];
}

/** Deal 집계 공통 파라미터 (by-sector, by-stage) */
export interface DealAggregationParams {
  year?: number;
  years?: number;
  corp_code?: string;
}

/** Deal 트렌드 파라미터 (GET /deals/trends — year 미지원) */
export interface DealTrendParams {
  years?: number;
  corp_code?: string;
}

/** Deal by-company 조회 파라미터 */
export interface DealByCompanyParams {
  years?: number;
  sector?: string;
  stage?: string;
  page?: number;
  size?: number;
}

/** Deal by-fund 조회 파라미터 */
export interface DealByFundParams {
  years?: number;
  page?: number;
  size?: number;
}

/** 투자 규모 분포 구간 */
export interface AmountBucket {
  bucket_label: string;
  bucket_min: number;
  bucket_max: number | null;
  deal_count: number;
  total_amount: string | null;
}

/** 투자 규모 통계 (GET /deals/stats) */
export interface DealAmountStats {
  total_deals: number;
  total_amount: string | null;
  avg_amount: string | null;
  median_amount: string | null;
  min_amount: string | null;
  max_amount: string | null;
  distribution: AmountBucket[];
}

/* ─── 투자성향 정성적 요약 (GET /deals/tendency-summary) ─── */

/** 투자성향 - 대표 딜 아이템 */
export interface TendencyDealItem {
  target_company: string;
  amount_display: string | null;
  round_stage: string | null;
  deal_date: string | null;
  source_url: string | null;
}

/** 투자성향 - 섹터별 상세 */
export interface TendencySectorDetail {
  sector: string;
  sector_name: string;
  deal_count: number;
  total_amount: string | null;
  total_amount_display: string | null;
  percentage: number;
  description: string;
  deals: TendencyDealItem[];
}

/** 투자성향 - 스테이지별 상세 */
export interface TendencyStageDetail {
  stage: string;
  stage_name: string;
  deal_count: number;
  total_amount: string | null;
  total_amount_display: string | null;
  percentage: number;
  description: string;
  deals: TendencyDealItem[];
}

/** 투자성향 정성적 요약 응답 */
export interface TendencySummaryResponse {
  corp_code: string;
  years: number;
  total_deals: number;
  total_amount: string | null;
  total_amount_display: string | null;
  summary_text: string;
  sector_summary: string;
  stage_summary: string;
  sectors: TendencySectorDetail[];
  stages: TendencyStageDetail[];
}
