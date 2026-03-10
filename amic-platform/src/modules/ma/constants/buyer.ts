import type { SelectOption } from "@/components/ui";
import type { BuyerCandidate, BuyerStatus } from "../types/buyer";
import type { BuyerStageSummary, MarketingStage } from "../types/marketing_log";

// ── Deal Role (컨소시엄 역할) ────────────────────────
export const DEAL_ROLE_OPTIONS: SelectOption[] = [
  { value: "", label: "미지정" },
  { value: "SOLE_BUYER", label: "단독 매수자" },
  { value: "CONSORTIUM_LEAD", label: "컨소시엄 리드" },
  { value: "CO_INVESTOR", label: "공동투자자" },
  { value: "FINANCING_PROVIDER", label: "파이낸싱 제공자" },
];

export const DEAL_ROLE_LABELS: Record<string, string> = {
  SOLE_BUYER: "단독 매수자",
  CONSORTIUM_LEAD: "컨소시엄 리드",
  CO_INVESTOR: "공동투자자",
  FINANCING_PROVIDER: "파이낸싱 제공자",
};

// ── Consortium Status (컨소시엄 상태) ────────────────
export const CONSORTIUM_STATUS_OPTIONS: SelectOption[] = [
  { value: "TAPPING", label: "타진 중" },
  { value: "CONFIRMED", label: "확정" },
  { value: "DROPPED", label: "이탈" },
];

export const CONSORTIUM_STATUS_LABELS: Record<string, string> = {
  TAPPING: "타진 중",
  CONFIRMED: "확정",
  DROPPED: "이탈",
};

// ── Buyer Tier ───────────────────────────────────────
export const BUYER_TIER_OPTIONS: SelectOption[] = [
  { value: "", label: "전체" },
  { value: "TIER_1", label: "Tier 1" },
  { value: "TIER_2", label: "Tier 2" },
  { value: "TIER_3", label: "Tier 3" },
  { value: "NOT_TARGET", label: "대상 아님" },
];

export const BUYER_TIER_LABELS: Record<string, string> = {
  TIER_1: "Tier 1",
  TIER_2: "Tier 2",
  TIER_3: "Tier 3",
  NOT_TARGET: "대상 아님",
};

/** Tier 1/2/3 → Short List 자동 승격 대상 */
const SHORT_LIST_TIER_SET = new Set<string>(["TIER_1", "TIER_2", "TIER_3"]);

/** tier 기반 Short List 판정 (is_short_listed 플래그 + tier SSOT 보정) */
export function isShortListed(b: BuyerCandidate): boolean {
  return b.is_short_listed || (!!b.tier && SHORT_LIST_TIER_SET.has(b.tier));
}

// ── Marketing Stage ─────────────────────────────────
export const MARKETING_STAGES: MarketingStage[] = [
  "IDENTIFIED",
  "TEASER_SENT",
  "NDA_SIGNED",
  "IM_DISTRIBUTED",
  "QNA_COMPLETED",
  "MGMT_PRESENTATION",
  "LOI_RECEIVED",
  "DD_IN_PROGRESS",
];

export const MARKETING_STAGE_LABELS: Record<MarketingStage, string> = {
  IDENTIFIED: "식별",
  TEASER_SENT: "Teaser",
  NDA_SIGNED: "NDA",
  IM_DISTRIBUTED: "IM",
  QNA_COMPLETED: "Q&A",
  MGMT_PRESENTATION: "MP",
  LOI_RECEIVED: "LOI",
  DD_IN_PROGRESS: "DD",
};

/** MP(Management Presentation)는 생략 가능한 단계 */
export const SKIPPABLE_STAGES: ReadonlySet<MarketingStage> = new Set([
  "MGMT_PRESENTATION",
]);

/** Milestone 단계 (강조 표시) */
export const MILESTONE_STAGES: ReadonlySet<MarketingStage> = new Set([
  "NDA_SIGNED",
  "LOI_RECEIVED",
  "DD_IN_PROGRESS",
]);

export const MARKETING_STAGE_OPTIONS: SelectOption[] = MARKETING_STAGES.map(
  (s) => ({ value: s, label: MARKETING_STAGE_LABELS[s] }),
);

// ── Stage Map Utility ──────────────────────────────
export function buildStageMap(
  overviewData: BuyerStageSummary[],
): Map<string, Partial<Record<MarketingStage, string | null>>> {
  return new Map(overviewData.map((s) => [s.buyer_id, s.stages]));
}

/** 가장 최근 완료된 마케팅 단계 인덱스 (-1 = 없음) */
export function latestCompletedStageIndex(
  stages: Partial<Record<MarketingStage, string | null>>,
): number {
  for (let i = MARKETING_STAGES.length - 1; i >= 0; i--) {
    if (stages[MARKETING_STAGES[i]]) return i;
  }
  return -1;
}

/** 완료된 마케팅 단계 수 (생략 가능 단계는 미완료 시 분모에서 제외) */
export function countCompletedStages(
  stages: Partial<Record<MarketingStage, string | null>> | undefined,
): number {
  if (!stages) return 0;
  return MARKETING_STAGES.filter((s) => stages[s]).length;
}

/** 유효 단계 수 (생략 가능 단계는 완료되지 않았으면 제외) */
export function effectiveStageCount(
  stages: Partial<Record<MarketingStage, string | null>> | undefined,
): number {
  if (!stages) return MARKETING_STAGES.length;
  return MARKETING_STAGES.filter((s) => !SKIPPABLE_STAGES.has(s) || stages[s])
    .length;
}

// ── Buyer Type ────────────────────────────────────────
export const BUYER_TYPE_OPTIONS: SelectOption[] = [
  { value: "", label: "전체" },
  { value: "STRATEGIC", label: "전략적 투자자" },
  { value: "FINANCIAL_SPONSOR", label: "재무적 투자자 (PE)" },
  { value: "FAMILY_OFFICE", label: "패밀리 오피스" },
  { value: "INDIVIDUAL", label: "개인" },
  { value: "OTHER", label: "기타" },
];

// ── Buyer Status ──────────────────────────────────────
export const BUYER_STATUS_OPTIONS: SelectOption[] = [
  { value: "", label: "전체" },
  { value: "IDENTIFIED", label: "식별" },
  { value: "CONTACTED", label: "접촉" },
  { value: "NDA_SENT", label: "NDA 발송" },
  { value: "NDA_SIGNED", label: "NDA 체결" },
  { value: "CIM_SENT", label: "IM 발송" },
  { value: "INTEREST_CONFIRMED", label: "관심 확인" },
  { value: "IOI_RECEIVED", label: "IOI 접수" },
  { value: "IOI_ACCEPTED", label: "IOI 수락" },
  { value: "DD_GRANTED", label: "DD 허가" },
  { value: "DD_IN_PROGRESS", label: "DD 진행 중" },
  { value: "LOI_RECEIVED", label: "LOI 접수" },
  { value: "LOI_ACCEPTED", label: "LOI 수락" },
  { value: "SELECTED", label: "최종 선정" },
  { value: "REJECTED", label: "거절" },
  { value: "BID_SUBMITTED", label: "입찰 제출" },
  { value: "BID_NOT_SUBMITTED", label: "입찰 미제출" },
  { value: "BID_DROPPED", label: "입찰 철회" },
];

// ── 매수자 Long List / Short List 분류 ────────────────
export const LONG_LIST_STATUSES: BuyerStatus[] = [
  "IDENTIFIED",
  "CONTACTED",
  "NDA_SENT",
  "NDA_SIGNED",
];
export const SHORT_LIST_STATUSES: BuyerStatus[] = [
  "CIM_SENT",
  "INTEREST_CONFIRMED",
  "IOI_RECEIVED",
  "IOI_ACCEPTED",
  "DD_GRANTED",
  "DD_IN_PROGRESS",
  "LOI_RECEIVED",
  "LOI_ACCEPTED",
  "SELECTED",
  "REJECTED",
  "BID_SUBMITTED",
  "BID_NOT_SUBMITTED",
  "BID_DROPPED",
];

// ── Funnel KPI 단계별 상태 분류 ──────────────────────
// REJECTED는 터미널 상태이므로 퍼널 단계에 포함하지 않음
export const FUNNEL_NDA_AND_AFTER: ReadonlySet<string> = new Set<BuyerStatus>([
  "NDA_SIGNED",
  "CIM_SENT",
  "INTEREST_CONFIRMED",
  "IOI_RECEIVED",
  "IOI_ACCEPTED",
  "DD_GRANTED",
  "DD_IN_PROGRESS",
  "LOI_RECEIVED",
  "LOI_ACCEPTED",
  "SELECTED",
  "BID_SUBMITTED",
  "BID_NOT_SUBMITTED",
  "BID_DROPPED",
]);

export const FUNNEL_CIM_AND_AFTER: ReadonlySet<string> = new Set<BuyerStatus>([
  "CIM_SENT",
  "INTEREST_CONFIRMED",
  "IOI_RECEIVED",
  "IOI_ACCEPTED",
  "DD_GRANTED",
  "DD_IN_PROGRESS",
  "LOI_RECEIVED",
  "LOI_ACCEPTED",
  "SELECTED",
  "BID_SUBMITTED",
  "BID_NOT_SUBMITTED",
  "BID_DROPPED",
]);

export const FUNNEL_DD_AND_AFTER: ReadonlySet<string> = new Set<BuyerStatus>([
  "DD_GRANTED",
  "DD_IN_PROGRESS",
  "LOI_RECEIVED",
  "LOI_ACCEPTED",
  "SELECTED",
  "BID_SUBMITTED",
  "BID_NOT_SUBMITTED",
  "BID_DROPPED",
]);
