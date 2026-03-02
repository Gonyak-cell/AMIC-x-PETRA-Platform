import type { SelectOption } from "@/components/ui";

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
