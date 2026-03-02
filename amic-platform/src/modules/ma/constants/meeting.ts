import type { SelectOption } from "@/components/ui";

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
