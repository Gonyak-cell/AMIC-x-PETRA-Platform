import type { SelectOption } from "@/components/ui";
import type { TransactionPhase } from "./types/transaction";
import type { BuyerStatus } from "./types/buyer";
import type { RFIStatus, RFICategory, RFIItemPriority, RFIItemStatus } from "./types/rfi";

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
  // FDD
  { value: "FDD_FINANCIAL_STATEMENTS", label: "재무제표 분석" },
  { value: "FDD_REVENUE", label: "매출 및 수익성" },
  { value: "FDD_WORKING_CAPITAL", label: "운전자본" },
  { value: "FDD_DEBT_CASH", label: "차입금 및 현금" },
  { value: "FDD_PROJECTIONS", label: "사업계획 및 추정" },
  // LDD
  { value: "LDD_CORPORATE", label: "회사일반" },
  { value: "LDD_PERMITS", label: "인허가 및 법령준수" },
  { value: "LDD_CONTRACTS", label: "계약" },
  { value: "LDD_ASSETS", label: "자산(부동산/기타 자산)" },
  { value: "LDD_LABOR", label: "인사노무" },
  { value: "LDD_LITIGATION", label: "소송 및 분쟁" },
  { value: "LDD_IP", label: "지식재산권" },
  { value: "LDD_INSURANCE", label: "보험" },
  { value: "LDD_ENVIRONMENT", label: "환경" },
  // TDD
  { value: "TDD_CORPORATE_TAX", label: "법인세" },
  { value: "TDD_VAT", label: "부가가치세" },
  { value: "TDD_TRANSFER_PRICING", label: "이전가격" },
  { value: "TDD_WITHHOLDING", label: "원천세" },
  { value: "TDD_TAX_INCENTIVES", label: "세제혜택 및 감면" },
  // 기타
  { value: "OTHER", label: "기타" },
];

/** 워크스트림 그룹 계층 구조 (FDD/LDD/TDD + 기타) */
export interface DDWorkstreamGroupConfig {
  key: string;
  label: string;
  children: string[];
}

export const DD_WORKSTREAM_HIERARCHY: DDWorkstreamGroupConfig[] = [
  { key: "FDD_GROUP", label: "FDD (재무실사)", children: ["FDD_FINANCIAL_STATEMENTS", "FDD_REVENUE", "FDD_WORKING_CAPITAL", "FDD_DEBT_CASH", "FDD_PROJECTIONS"] },
  { key: "LDD_GROUP", label: "LDD (법률실사)", children: ["LDD_CORPORATE", "LDD_PERMITS", "LDD_CONTRACTS", "LDD_ASSETS", "LDD_LABOR", "LDD_LITIGATION", "LDD_IP", "LDD_INSURANCE", "LDD_ENVIRONMENT"] },
  { key: "TDD_GROUP", label: "TDD (세무실사)", children: ["TDD_CORPORATE_TAX", "TDD_VAT", "TDD_TRANSFER_PRICING", "TDD_WITHHOLDING", "TDD_TAX_INCENTIVES"] },
  { key: "OTHER", label: "기타", children: ["OTHER"] },
];

export const DD_SUB_LABELS: Record<string, string> = {
  // FDD
  FDD_FINANCIAL_STATEMENTS: "재무제표 분석", FDD_REVENUE: "매출 및 수익성",
  FDD_WORKING_CAPITAL: "운전자본", FDD_DEBT_CASH: "차입금 및 현금", FDD_PROJECTIONS: "사업계획 및 추정",
  // LDD
  LDD_CORPORATE: "회사일반", LDD_PERMITS: "인허가 및 법령준수", LDD_CONTRACTS: "계약",
  LDD_ASSETS: "자산(부동산/기타 자산)", LDD_LABOR: "인사노무", LDD_LITIGATION: "소송 및 분쟁",
  LDD_IP: "지식재산권", LDD_INSURANCE: "보험", LDD_ENVIRONMENT: "환경",
  // TDD
  TDD_CORPORATE_TAX: "법인세", TDD_VAT: "부가가치세", TDD_TRANSFER_PRICING: "이전가격",
  TDD_WITHHOLDING: "원천세", TDD_TAX_INCENTIVES: "세제혜택 및 감면",
};

export const DD_STATUS_OPTIONS: SelectOption[] = [
  { value: "NOT_STARTED", label: "미시작" },
  { value: "IN_PROGRESS", label: "진행 중" },
  { value: "COMPLETED", label: "완료" },
  { value: "NOT_APPLICABLE", label: "해당 없음" },
];

// ── Contract Type (Phase 3) ──────────────────────────
export const CONTRACT_TYPE_OPTIONS: SelectOption[] = [
  { value: "SPA", label: "SPA (주식매매계약)" },
  { value: "SHAREHOLDERS_AGREEMENT", label: "SHA (주주간계약)" },
  { value: "BTA", label: "BTA (영업양수도계약)" },
  { value: "SSA", label: "SSA (신주인수계약)" },
  { value: "AMENDMENT", label: "수정계약" },
  { value: "SIDE_LETTER", label: "사이드레터" },
  { value: "ESCROW_AGREEMENT", label: "에스크로 계약" },
  { value: "OTHER", label: "기타" },
];

export const ISSUE_DECISION_STATUS_OPTIONS: SelectOption[] = [
  { value: "PENDING", label: "미결정" },
  { value: "CONSIDER_ACCEPTING", label: "수용 검토" },
  { value: "CANNOT_ACCEPT", label: "수용 불가" },
];

export const MARKUP_TYPE_OPTIONS: SelectOption[] = [
  { value: "draft", label: "Draft" },
  { value: "1st", label: "1st Markup" },
  { value: "2nd", label: "2nd Markup" },
  { value: "3rd", label: "3rd Markup" },
  { value: "4th", label: "4th Markup" },
  { value: "final", label: "Final" },
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

// ── Note Type (Phase 5A) ───────────────────────────────
export const NOTE_TYPE_OPTIONS: SelectOption[] = [
  { value: "COMMENT", label: "코멘트" },
  { value: "DECISION", label: "결정사항" },
  { value: "QUESTION", label: "질문" },
  { value: "ACTION_ITEM", label: "액션아이템" },
];

// ── Approval Type (Phase 5A) ──────────────────────────
export const APPROVAL_TYPE_OPTIONS: SelectOption[] = [
  { value: "PHASE_ADVANCE", label: "단계 전환" },
  { value: "STATUS_CHANGE", label: "상태 변경" },
  { value: "CONTRACT_SIGN", label: "계약 체결" },
  { value: "DEAL_TERMS", label: "거래 조건" },
];

export const APPROVAL_STATUS_OPTIONS: SelectOption[] = [
  { value: "PENDING", label: "대기" },
  { value: "APPROVED", label: "승인" },
  { value: "REJECTED", label: "거절" },
  { value: "CANCELLED", label: "취소" },
];

// ── Risk Category (Phase 5B) ───────────────────────────
export const RISK_CATEGORY_OPTIONS: SelectOption[] = [
  { value: "REGULATORY", label: "규제 (Regulatory)" },
  { value: "FINANCIAL", label: "재무 (Financial)" },
  { value: "LEGAL", label: "법률 (Legal)" },
  { value: "OPERATIONAL", label: "운영 (Operational)" },
  { value: "REPUTATIONAL", label: "평판 (Reputational)" },
  { value: "TAX", label: "세무 (Tax)" },
  { value: "ENVIRONMENTAL", label: "환경 (Environmental)" },
  { value: "MARKET", label: "시장 (Market)" },
  { value: "OTHER", label: "기타" },
];

export const RISK_SEVERITY_OPTIONS: SelectOption[] = [
  { value: "CRITICAL", label: "치명적" },
  { value: "HIGH", label: "높음" },
  { value: "MEDIUM", label: "보통" },
  { value: "LOW", label: "낮음" },
];

export const RISK_LIKELIHOOD_OPTIONS: SelectOption[] = [
  { value: "VERY_HIGH", label: "매우 높음" },
  { value: "HIGH", label: "높음" },
  { value: "MEDIUM", label: "보통" },
  { value: "LOW", label: "낮음" },
  { value: "VERY_LOW", label: "매우 낮음" },
];

export const RISK_STATUS_OPTIONS: SelectOption[] = [
  { value: "IDENTIFIED", label: "식별" },
  { value: "ASSESSING", label: "평가 중" },
  { value: "MITIGATING", label: "완화 중" },
  { value: "MITIGATED", label: "완화됨" },
  { value: "ACCEPTED", label: "수용" },
  { value: "CLOSED", label: "종료" },
];

// ── Compliance Category (Phase 5B) ─────────────────────
export const COMPLIANCE_CATEGORY_OPTIONS: SelectOption[] = [
  { value: "ANTITRUST", label: "독점규제 (Antitrust)" },
  { value: "FOREIGN_INVESTMENT", label: "외국인투자 (FDI)" },
  { value: "SECURITIES", label: "증권 (Securities)" },
  { value: "DATA_PRIVACY", label: "개인정보 (Data Privacy)" },
  { value: "ANTI_CORRUPTION", label: "반부패 (Anti-Corruption)" },
  { value: "SANCTIONS", label: "제재 (Sanctions)" },
  { value: "ENVIRONMENTAL", label: "환경 (Environmental)" },
  { value: "LABOR", label: "노동 (Labor)" },
  { value: "TAX", label: "세무 (Tax)" },
  { value: "PERMITS", label: "인허가 (Permits)" },
  { value: "OTHER", label: "기타" },
];

export const COMPLIANCE_STATUS_OPTIONS: SelectOption[] = [
  { value: "NOT_STARTED", label: "미시작" },
  { value: "IN_REVIEW", label: "검토 중" },
  { value: "PENDING_APPROVAL", label: "승인 대기" },
  { value: "APPROVED", label: "승인" },
  { value: "FLAGGED", label: "주의" },
  { value: "NON_COMPLIANT", label: "미준수" },
  { value: "WAIVED", label: "면제" },
];

// ── Permit Filing Type (인허가 신고유형) ──────────────────
export const PERMIT_FILING_TYPE_OPTIONS: SelectOption[] = [
  { value: "CHANGE_NOTIFICATION", label: "변경신고" },
  { value: "CHANGE_APPROVAL", label: "변경허가" },
  { value: "NEW_REGISTRATION", label: "신규등록/허가" },
  { value: "RENEWAL", label: "갱신" },
];

// ── Permit Timing Type (인허가 사전/사후) ─────────────────
export const PERMIT_TIMING_TYPE_OPTIONS: SelectOption[] = [
  { value: "PRE_FILING", label: "사전" },
  { value: "POST_FILING", label: "사후" },
  { value: "BOTH", label: "사전+사후" },
];

// ── Permit Requirement Status (인허가 요건 상태) ──────────
export const PERMIT_REQUIREMENT_STATUS_OPTIONS: SelectOption[] = [
  { value: "IDENTIFIED", label: "확인됨" },
  { value: "DOCUMENTS_PREPARING", label: "서류 준비 중" },
  { value: "FILED", label: "신고 완료" },
  { value: "APPROVED", label: "승인" },
  { value: "NOT_APPLICABLE", label: "해당 없음" },
];

// ── Meeting Channel (미팅 채널) ────────────────────────
export const MEETING_CHANNEL_OPTIONS: SelectOption[] = [
  { value: "IN_PERSON", label: "대면" },
  { value: "EMAIL", label: "이메일" },
  { value: "PHONE", label: "전화" },
  { value: "VIDEO", label: "화상" },
  { value: "HYBRID", label: "하이브리드" },
];

// ── Meeting Status (미팅 상태) ──────────────────────────
export const MEETING_STATUS_OPTIONS: SelectOption[] = [
  { value: "SCHEDULED", label: "예정" },
  { value: "COMPLETED", label: "완료" },
  { value: "CANCELLED", label: "취소" },
  { value: "POSTPONED", label: "연기" },
];

// ── Buyer Reaction (매수인 반응) ────────────────────────
export const BUYER_REACTION_OPTIONS: SelectOption[] = [
  { value: "VERY_POSITIVE", label: "매우 긍정" },
  { value: "POSITIVE", label: "긍정" },
  { value: "NEUTRAL", label: "중립" },
  { value: "NEGATIVE", label: "부정" },
  { value: "VERY_NEGATIVE", label: "매우 부정" },
];

// ── Condition Match (조건 일치도) ────────────────────────
export const CONDITION_MATCH_OPTIONS: SelectOption[] = [
  { value: "FULL_MATCH", label: "완전 부합" },
  { value: "PARTIAL_MATCH", label: "부분 부합" },
  { value: "MISMATCH", label: "불일치" },
  { value: "NOT_ASSESSED", label: "미평가" },
];

// ── Negotiation Issue Status (협상 이견 상태) ────────────
export const NEGOTIATION_ISSUE_STATUS_OPTIONS: SelectOption[] = [
  { value: "OPEN", label: "미해결" },
  { value: "IN_PROGRESS", label: "논의 중" },
  { value: "AGREED", label: "합의" },
  { value: "DEFERRED", label: "보류" },
  { value: "DEADLOCKED", label: "교착" },
];

// ── Negotiation Issue Priority (협상 이견 우선순위) ───────
export const NEGOTIATION_ISSUE_PRIORITY_OPTIONS: SelectOption[] = [
  { value: "CRITICAL", label: "긴급" },
  { value: "HIGH", label: "높음" },
  { value: "MEDIUM", label: "보통" },
  { value: "LOW", label: "낮음" },
];

// ── Action Item Status (액션아이템 상태) ─────────────────
export const ACTION_ITEM_STATUS_OPTIONS: SelectOption[] = [
  { value: "PENDING", label: "대기" },
  { value: "IN_PROGRESS", label: "진행 중" },
  { value: "COMPLETED", label: "완료" },
  { value: "CANCELLED", label: "취소" },
];

// ── Attendee Role (참석자 역할) ──────────────────────────
export const ATTENDEE_ROLE_OPTIONS: SelectOption[] = [
  { value: "SELLER_ADVISOR", label: "매도자문" },
  { value: "BUYER_ADVISOR", label: "매수자문" },
  { value: "LEGAL_COUNSEL", label: "법률자문" },
  { value: "CLIENT_REPRESENTATIVE", label: "의뢰인 대표" },
  { value: "COUNTERPARTY", label: "상대방" },
  { value: "OBSERVER", label: "옵저버" },
  { value: "OTHER", label: "기타" },
];

// ── RFI Status ───────────────────────────────────────
export const RFI_STATUS_OPTIONS: SelectOption[] = [
  { value: "", label: "전체" },
  { value: "DRAFT", label: "초안" },
  { value: "SENT", label: "발송됨" },
  { value: "PARTIALLY_RESPONDED", label: "일부 응답" },
  { value: "FULLY_RESPONDED", label: "전체 응답" },
  { value: "CLOSED", label: "마감" },
  { value: "CANCELLED", label: "취소" },
];

// ── RFI Category ─────────────────────────────────────
export const RFI_CATEGORY_OPTIONS: SelectOption[] = [
  { value: "", label: "전체" },
  { value: "GENERAL", label: "일반" },
  { value: "FINANCIAL", label: "재무" },
  { value: "TAX", label: "세무" },
  { value: "LEGAL", label: "법률" },
  { value: "OPERATIONAL", label: "운영" },
  { value: "COMMERCIAL", label: "영업" },
  { value: "HR", label: "인사" },
  { value: "IT", label: "IT" },
  { value: "ENVIRONMENTAL", label: "환경" },
  { value: "INSURANCE", label: "보험" },
  { value: "IP", label: "지재권" },
  { value: "REAL_ESTATE", label: "부동산" },
  { value: "VALUATION", label: "밸류에이션" },
  { value: "OTHER", label: "기타" },
];

// ── RFI Priority ─────────────────────────────────────
export const RFI_PRIORITY_OPTIONS: SelectOption[] = [
  { value: "CRITICAL", label: "긴급" },
  { value: "HIGH", label: "높음" },
  { value: "MEDIUM", label: "보통" },
  { value: "LOW", label: "낮음" },
];

// ── RFI Item Status ──────────────────────────────────
export const RFI_ITEM_STATUS_OPTIONS: SelectOption[] = [
  { value: "", label: "전체" },
  { value: "PENDING", label: "대기" },
  { value: "RESPONDED", label: "응답됨" },
  { value: "CLARIFICATION_NEEDED", label: "추가확인" },
  { value: "ACCEPTED", label: "확인완료" },
  { value: "NOT_APPLICABLE", label: "해당없음" },
];

// ── RFI Labels (공용 — 컴포넌트 간 중복 제거) ──────────

export const RFI_STATUS_LABELS: Record<RFIStatus, string> = {
  DRAFT: "초안",
  SENT: "발송됨",
  PARTIALLY_RESPONDED: "일부 응답",
  FULLY_RESPONDED: "전체 응답",
  CLOSED: "마감",
  CANCELLED: "취소",
};

export const RFI_CATEGORY_LABELS: Record<RFICategory, string> = {
  GENERAL: "일반",
  FINANCIAL: "재무",
  TAX: "세무",
  LEGAL: "법률",
  OPERATIONAL: "운영",
  COMMERCIAL: "영업",
  HR: "인사",
  IT: "IT",
  ENVIRONMENTAL: "환경",
  INSURANCE: "보험",
  IP: "지재권",
  REAL_ESTATE: "부동산",
  VALUATION: "밸류에이션",
  OTHER: "기타",
};

export const RFI_PRIORITY_LABELS: Record<RFIItemPriority, string> = {
  CRITICAL: "긴급",
  HIGH: "높음",
  MEDIUM: "보통",
  LOW: "낮음",
};

export const RFI_ITEM_STATUS_LABELS: Record<RFIItemStatus, string> = {
  PENDING: "대기",
  RESPONDED: "응답됨",
  CLARIFICATION_NEEDED: "추가확인",
  ACCEPTED: "확인완료",
  NOT_APPLICABLE: "해당없음",
};

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
    label: "Closing",
    description: "SPA 체결, 선행조건 충족, 거래 완결",
    icon: "CheckCircle",
    order: 6,
  },
  {
    phase: "POST_CLOSING",
    label: "Post-Closing",
    description: "가격조정 정산, PMI 지원, 프로젝트 종결",
    icon: "Archive",
    order: 7,
  },
];

// ── Phase ↔ Tab 매핑 ────────────────────────────────
export const PHASE_TAB_MAP: Record<TransactionPhase, string> = {
  ENGAGEMENT: "engagement",
  PREPARATION: "marketing-materials",
  MARKETING: "buyers",
  BIDDING_DD: "dd-checklist",
  NEGOTIATION: "contracts",
  CLOSING: "closing",
  POST_CLOSING: "pmi",
};

// ── 단계별 표시 탭 (전 단계 공통 + 단계별) ────────────
export const ALWAYS_VISIBLE_TABS = [
  "overview",
] as const;

export const PHASE_VISIBLE_TABS: Record<TransactionPhase, readonly string[]> = {
  ENGAGEMENT:   [...ALWAYS_VISIBLE_TABS, "engagement", "rfi"],
  PREPARATION:  [...ALWAYS_VISIBLE_TABS, "marketing-materials", "models", "ndas", "vdr"],
  MARKETING:    [...ALWAYS_VISIBLE_TABS, "buyers", "marketing-logs", "vdr"],
  BIDDING_DD:   [...ALWAYS_VISIBLE_TABS, "bids", "dd-checklist", "rfi", "vdr"],
  NEGOTIATION:  [...ALWAYS_VISIBLE_TABS, "contracts", "negotiation-logs", "vdr"],
  CLOSING:      [...ALWAYS_VISIBLE_TABS, "closing", "vdr"],
  POST_CLOSING: [...ALWAYS_VISIBLE_TABS, "pmi", "earnout", "vdr"],
};

// ── 매수자 Long List / Short List 분류 ────────────────
export const LONG_LIST_STATUSES: BuyerStatus[] = [
  "IDENTIFIED", "CONTACTED", "NDA_SENT", "NDA_SIGNED",
];
export const SHORT_LIST_STATUSES: BuyerStatus[] = [
  "CIM_SENT", "INTEREST_CONFIRMED", "IOI_RECEIVED", "IOI_ACCEPTED",
  "DD_GRANTED", "DD_IN_PROGRESS", "LOI_RECEIVED", "LOI_ACCEPTED",
  "SELECTED", "REJECTED",
];

// ── 파이프라인 마일스톤 ─────────────────────────────
export const PHASE_MILESTONES: { afterPhase: TransactionPhase; label: string }[] = [
  { afterPhase: "MARKETING", label: "MOU Signed" },
  { afterPhase: "CLOSING", label: "Deal Closed" },
];
