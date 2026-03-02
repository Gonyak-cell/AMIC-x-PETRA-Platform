import type { SelectOption } from "@/components/ui";

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
  {
    key: "FDD_GROUP",
    label: "FDD (재무실사)",
    children: [
      "FDD_FINANCIAL_STATEMENTS",
      "FDD_REVENUE",
      "FDD_WORKING_CAPITAL",
      "FDD_DEBT_CASH",
      "FDD_PROJECTIONS",
    ],
  },
  {
    key: "LDD_GROUP",
    label: "LDD (법률실사)",
    children: [
      "LDD_CORPORATE",
      "LDD_PERMITS",
      "LDD_CONTRACTS",
      "LDD_ASSETS",
      "LDD_LABOR",
      "LDD_LITIGATION",
      "LDD_IP",
      "LDD_INSURANCE",
      "LDD_ENVIRONMENT",
    ],
  },
  {
    key: "TDD_GROUP",
    label: "TDD (세무실사)",
    children: [
      "TDD_CORPORATE_TAX",
      "TDD_VAT",
      "TDD_TRANSFER_PRICING",
      "TDD_WITHHOLDING",
      "TDD_TAX_INCENTIVES",
    ],
  },
  { key: "OTHER", label: "기타", children: ["OTHER"] },
];

export const DD_SUB_LABELS: Record<string, string> = {
  // FDD
  FDD_FINANCIAL_STATEMENTS: "재무제표 분석",
  FDD_REVENUE: "매출 및 수익성",
  FDD_WORKING_CAPITAL: "운전자본",
  FDD_DEBT_CASH: "차입금 및 현금",
  FDD_PROJECTIONS: "사업계획 및 추정",
  // LDD
  LDD_CORPORATE: "회사일반",
  LDD_PERMITS: "인허가 및 법령준수",
  LDD_CONTRACTS: "계약",
  LDD_ASSETS: "자산(부동산/기타 자산)",
  LDD_LABOR: "인사노무",
  LDD_LITIGATION: "소송 및 분쟁",
  LDD_IP: "지식재산권",
  LDD_INSURANCE: "보험",
  LDD_ENVIRONMENT: "환경",
  // TDD
  TDD_CORPORATE_TAX: "법인세",
  TDD_VAT: "부가가치세",
  TDD_TRANSFER_PRICING: "이전가격",
  TDD_WITHHOLDING: "원천세",
  TDD_TAX_INCENTIVES: "세제혜택 및 감면",
};

export const DD_STATUS_OPTIONS: SelectOption[] = [
  { value: "NOT_STARTED", label: "미시작" },
  { value: "IN_PROGRESS", label: "진행 중" },
  { value: "COMPLETED", label: "완료" },
  { value: "NOT_APPLICABLE", label: "해당 없음" },
];
