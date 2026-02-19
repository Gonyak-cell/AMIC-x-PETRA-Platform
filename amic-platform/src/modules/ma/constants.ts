import type { SelectOption } from "@/components/ui";
import type { TransactionPhase } from "./types/transaction";

// ── Transaction Side ──────────────────────────────────
export const TRANSACTION_SIDE_OPTIONS: SelectOption[] = [
  { value: "", label: "전체" },
  { value: "SELL", label: "매도 (Sell-side)" },
  { value: "BUY", label: "매수 (Buy-side)" },
  { value: "DUAL", label: "듀얼 (Dual)" },
];

// ── Transaction Status ────────────────────────────────
export const TRANSACTION_STATUS_OPTIONS: SelectOption[] = [
  { value: "", label: "전체" },
  { value: "DRAFT", label: "초안" },
  { value: "ACTIVE", label: "진행 중" },
  { value: "ON_HOLD", label: "보류" },
  { value: "COMPLETED", label: "완료" },
  { value: "TERMINATED", label: "종료" },
];

// ── Currency ──────────────────────────────────────────
export const CURRENCY_OPTIONS: SelectOption[] = [
  { value: "KRW", label: "KRW (원)" },
  { value: "USD", label: "USD ($)" },
  { value: "EUR", label: "EUR (€)" },
  { value: "JPY", label: "JPY (¥)" },
  { value: "CNY", label: "CNY (¥)" },
];

// ── Deal Structure ────────────────────────────────────
export const DEAL_STRUCTURE_OPTIONS: SelectOption[] = [
  { value: "", label: "선택 안함" },
  { value: "SHARE_ACQUISITION", label: "지분인수" },
  { value: "ASSET_ACQUISITION", label: "자산인수" },
  { value: "MERGER", label: "합병" },
  { value: "CORPORATE_SPLIT", label: "분할" },
  { value: "MBO", label: "경영진 인수 (MBO)" },
  { value: "OTHER", label: "기타" },
];

// ── Investment Type ───────────────────────────────────
export const INVESTMENT_TYPE_OPTIONS: SelectOption[] = [
  { value: "", label: "선택 안함" },
  { value: "EQUITY", label: "지분투자" },
  { value: "DEBT", label: "채권투자" },
  { value: "MEZZANINE", label: "메자닌" },
  { value: "CONVERTIBLE", label: "전환사채" },
  { value: "OTHER", label: "기타" },
];

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
  { value: "REJECTED", label: "거절" },
];

// ── Engagement Type ───────────────────────────────────
export const ENGAGEMENT_TYPE_OPTIONS: SelectOption[] = [
  { value: "EXCLUSIVE", label: "전속 (Exclusive)" },
  { value: "NON_EXCLUSIVE", label: "비전속 (Non-Exclusive)" },
  { value: "CO_ADVISORY", label: "공동자문 (Co-Advisory)" },
];

// ── Working Group Role ────────────────────────────────
export const WORKING_GROUP_ROLE_OPTIONS: SelectOption[] = [
  { value: "LEAD_ADVISOR", label: "리드 어드바이저" },
  { value: "LEGAL_COUNSEL", label: "법률 자문" },
  { value: "ACCOUNTING_ADVISOR", label: "회계 자문" },
  { value: "TAX_ADVISOR", label: "세무 자문" },
  { value: "INDUSTRY_EXPERT", label: "산업 전문가" },
  { value: "VALUATION_ADVISOR", label: "밸류에이션 자문" },
  { value: "OTHER", label: "기타" },
];

// ── NDA Type ────────────────────────────────────────
export const NDA_TYPE_OPTIONS: SelectOption[] = [
  { value: "ONE_WAY", label: "단방향 (One-Way)" },
  { value: "MUTUAL", label: "상호 (Mutual)" },
];

export const NDA_STATUS_OPTIONS: SelectOption[] = [
  { value: "DRAFT", label: "초안" },
  { value: "SENT", label: "발송" },
  { value: "SIGNED", label: "체결" },
  { value: "EXPIRED", label: "만료" },
  { value: "REJECTED", label: "거절" },
];

// ── Bid Type ────────────────────────────────────────
export const BID_TYPE_OPTIONS: SelectOption[] = [
  { value: "IOI", label: "IOI" },
  { value: "LOI", label: "LOI" },
  { value: "FINAL_OFFER", label: "최종 제안" },
];

export const BID_STATUS_OPTIONS: SelectOption[] = [
  { value: "SUBMITTED", label: "제출" },
  { value: "UNDER_REVIEW", label: "검토 중" },
  { value: "ACCEPTED", label: "수락" },
  { value: "REJECTED", label: "거절" },
  { value: "WITHDRAWN", label: "철회" },
  { value: "EXPIRED", label: "만료" },
];

export const VALUATION_METHOD_OPTIONS: SelectOption[] = [
  { value: "", label: "선택 안함" },
  { value: "EV_EBITDA", label: "EV/EBITDA" },
  { value: "EV_REVENUE", label: "EV/Revenue" },
  { value: "PRICE_BOOK", label: "P/B" },
  { value: "DCF", label: "DCF" },
  { value: "COMPARABLE", label: "유사기업 비교" },
  { value: "OTHER", label: "기타" },
];

// ── DD Workstream ───────────────────────────────────
export const DD_WORKSTREAM_OPTIONS: SelectOption[] = [
  { value: "FINANCIAL", label: "재무 (Financial)" },
  { value: "LEGAL", label: "법률 (Legal)" },
  { value: "TAX", label: "세무 (Tax)" },
  { value: "COMMERCIAL", label: "사업 (Commercial)" },
  { value: "IT", label: "IT" },
  { value: "HR", label: "인사 (HR)" },
  { value: "ENVIRONMENTAL", label: "환경 (Environmental)" },
  { value: "INSURANCE", label: "보험 (Insurance)" },
  { value: "OTHER", label: "기타" },
];

export const DD_STATUS_OPTIONS: SelectOption[] = [
  { value: "NOT_STARTED", label: "미시작" },
  { value: "IN_PROGRESS", label: "진행 중" },
  { value: "COMPLETED", label: "완료" },
  { value: "NOT_APPLICABLE", label: "해당 없음" },
];

// ── Contract Type (Phase 3) ──────────────────────────
export const CONTRACT_TYPE_OPTIONS: SelectOption[] = [
  { value: "SPA", label: "SPA (주식매매계약)" },
  { value: "AMENDMENT", label: "수정계약" },
  { value: "SIDE_LETTER", label: "사이드레터" },
  { value: "SHAREHOLDERS_AGREEMENT", label: "주주간계약 (SHA)" },
  { value: "ESCROW_AGREEMENT", label: "에스크로 계약" },
  { value: "OTHER", label: "기타" },
];

export const CONTRACT_STATUS_OPTIONS: SelectOption[] = [
  { value: "DRAFT", label: "초안" },
  { value: "UNDER_REVIEW", label: "검토 중" },
  { value: "PENDING_SIGNATURE", label: "서명 대기" },
  { value: "PARTIALLY_SIGNED", label: "일부 서명" },
  { value: "FULLY_EXECUTED", label: "체결 완료" },
  { value: "TERMINATED", label: "종료" },
];

export const SIGNATURE_STATUS_OPTIONS: SelectOption[] = [
  { value: "NOT_REQUIRED", label: "불필요" },
  { value: "PENDING", label: "대기" },
  { value: "SIGNED", label: "서명 완료" },
  { value: "DECLINED", label: "거절" },
];

// ── Closing Category (Phase 3) ──────────────────────
export const CLOSING_CATEGORY_OPTIONS: SelectOption[] = [
  { value: "REGULATORY", label: "인허가 (Regulatory)" },
  { value: "LEGAL", label: "법률 (Legal)" },
  { value: "FINANCIAL", label: "재무 (Financial)" },
  { value: "CORPORATE", label: "기업 (Corporate)" },
  { value: "CONDITION_PRECEDENT", label: "선행조건 (CP)" },
  { value: "FUND_FLOW", label: "자금이체 (Fund Flow)" },
  { value: "OTHER", label: "기타" },
];

export const CLOSING_CONDITION_STATUS_OPTIONS: SelectOption[] = [
  { value: "PENDING", label: "대기" },
  { value: "IN_PROGRESS", label: "진행 중" },
  { value: "COMPLETED", label: "완료" },
  { value: "WAIVED", label: "면제" },
  { value: "NOT_APPLICABLE", label: "해당 없음" },
];

// ── PMI Category (Phase 4) ───────────────────────────
export const PMI_CATEGORY_OPTIONS: SelectOption[] = [
  { value: "INTEGRATION_PLAN", label: "통합 계획" },
  { value: "DAY_ONE", label: "Day One" },
  { value: "FIRST_100_DAYS", label: "First 100 Days" },
  { value: "SYNERGY", label: "시너지" },
  { value: "CULTURE", label: "기업 문화" },
  { value: "IT_SYSTEMS", label: "IT 시스템" },
  { value: "HR", label: "인사 (HR)" },
  { value: "COMMUNICATION", label: "커뮤니케이션" },
  { value: "OTHER", label: "기타" },
];

export const PMI_STATUS_OPTIONS: SelectOption[] = [
  { value: "NOT_STARTED", label: "미시작" },
  { value: "IN_PROGRESS", label: "진행 중" },
  { value: "COMPLETED", label: "완료" },
  { value: "BLOCKED", label: "차단됨" },
  { value: "DEFERRED", label: "연기" },
];

export const PMI_PRIORITY_OPTIONS: SelectOption[] = [
  { value: "CRITICAL", label: "긴급" },
  { value: "HIGH", label: "높음" },
  { value: "MEDIUM", label: "보통" },
  { value: "LOW", label: "낮음" },
];

// ── Earnout (Phase 4) ───────────────────────────────
export const EARNOUT_STATUS_OPTIONS: SelectOption[] = [
  { value: "PENDING", label: "대기" },
  { value: "MEASUREMENT_PERIOD", label: "측정 기간" },
  { value: "ACHIEVED", label: "달성" },
  { value: "PARTIALLY_ACHIEVED", label: "부분 달성" },
  { value: "MISSED", label: "미달성" },
  { value: "DISPUTED", label: "분쟁 중" },
];

export const EARNOUT_METRIC_OPTIONS: SelectOption[] = [
  { value: "REVENUE", label: "매출액" },
  { value: "EBITDA", label: "EBITDA" },
  { value: "NET_INCOME", label: "순이익" },
  { value: "CUSTOMER_COUNT", label: "고객 수" },
  { value: "CONTRACT_VALUE", label: "계약 금액" },
  { value: "WORKING_CAPITAL", label: "운전자본" },
  { value: "OTHER", label: "기타" },
];

// ── 7단계 Phase 설정 ─────────────────────────────────
export interface PhaseConfigItem {
  phase: TransactionPhase;
  label: string;
  description: string;
  icon: string;
  order: number;
}

export const PHASE_CONFIG: PhaseConfigItem[] = [
  {
    phase: "ENGAGEMENT",
    label: "수임",
    description: "클라이언트 수임계약 체결 및 이해충돌 검토",
    icon: "Handshake",
    order: 1,
  },
  {
    phase: "PREPARATION",
    label: "준비",
    description: "대상기업 분석, CIM 작성, 바이어 롱리스트 구성",
    icon: "ClipboardList",
    order: 2,
  },
  {
    phase: "MARKETING",
    label: "마케팅",
    description: "잠재 매수자 접촉, NDA 체결, CIM 배포",
    icon: "Megaphone",
    order: 3,
  },
  {
    phase: "BIDDING_DD",
    label: "입찰/DD",
    description: "IOI 접수, 실사 진행, LOI 접수",
    icon: "Search",
    order: 4,
  },
  {
    phase: "NEGOTIATION",
    label: "협상",
    description: "최종 후보 선정, SPA 협상, 가격 조정",
    icon: "Scale",
    order: 5,
  },
  {
    phase: "CLOSING",
    label: "클로징",
    description: "SPA 체결, 선행조건 충족, 거래 완결",
    icon: "CheckCircle",
    order: 6,
  },
  {
    phase: "POST_CLOSING",
    label: "포스트 클로징",
    description: "가격조정 정산, PMI 지원, 프로젝트 종결",
    icon: "Archive",
    order: 7,
  },
];
