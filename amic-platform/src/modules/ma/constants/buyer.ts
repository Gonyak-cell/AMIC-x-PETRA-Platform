import type { SelectOption } from "@/components/ui";
import type { BuyerStatus } from "../types/buyer";
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

// ── Marketing Stage ─────────────────────────────────
export const MARKETING_STAGES: MarketingStage[] = [
  "IDENTIFIED",
  "EMAIL_SENT",
  "PHONE_CALL",
  "ADVISOR_MEETING",
  "NDA_SIGNED",
  "TARGET_MEETING",
];

export const MARKETING_STAGE_LABELS: Record<MarketingStage, string> = {
  IDENTIFIED: "식별",
  EMAIL_SENT: "메일전송",
  PHONE_CALL: "전화",
  ADVISOR_MEETING: "자문사 미팅",
  NDA_SIGNED: "NDA 체결",
  TARGET_MEETING: "대상회사 미팅",
};

export const MARKETING_STAGE_OPTIONS: SelectOption[] = [
  { value: "IDENTIFIED", label: "식별" },
  { value: "EMAIL_SENT", label: "메일전송" },
  { value: "PHONE_CALL", label: "전화" },
  { value: "ADVISOR_MEETING", label: "자문사 미팅" },
  { value: "NDA_SIGNED", label: "NDA 체결" },
  { value: "TARGET_MEETING", label: "대상회사 미팅" },
];

// ── Stage Map Utility ──────────────────────────────
export function buildStageMap(
  overviewData: BuyerStageSummary[],
): Map<string, Record<MarketingStage, string | null>> {
  return new Map(overviewData.map((s) => [s.buyer_id, s.stages]));
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
  { value: "IDENTIFIED", label: "식별" },
  { value: "CONTACTED", label: "접촉" },
  { value: "NDA_SENT", label: "NDA 발송" },
  { value: "NDA_SIGNED", label: "NDA 체결" },
  { value: "CIM_SENT", label: "CIM 발송" },
  { value: "INTEREST_CONFIRMED", label: "관심 확인" },
  { value: "IOI_RECEIVED", label: "IOI 접수" },
  { value: "IOI_ACCEPTED", label: "IOI 수락" },
  { value: "DD_GRANTED", label: "DD 허가" },
  { value: "DD_IN_PROGRESS", label: "DD 진행 중" },
  { value: "LOI_RECEIVED", label: "LOI 접수" },
  { value: "LOI_ACCEPTED", label: "LOI 수락" },
  { value: "SELECTED", label: "최종 선정" },
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
];
