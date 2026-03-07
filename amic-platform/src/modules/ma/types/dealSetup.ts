// ── 딜 셋업 AI 에이전트 타입 ─────────────────────────────

import type { DealType, TransactionSide, DealStructure } from "./transaction";

export type DDWorkstream =
  | "FDD_FINANCIAL_STATEMENTS"
  | "FDD_REVENUE"
  | "FDD_WORKING_CAPITAL"
  | "FDD_DEBT_CASH"
  | "FDD_PROJECTIONS"
  | "LDD_CORPORATE"
  | "LDD_PERMITS"
  | "LDD_CONTRACTS"
  | "LDD_ASSETS"
  | "LDD_LABOR"
  | "LDD_LITIGATION"
  | "LDD_IP"
  | "LDD_INSURANCE"
  | "LDD_ENVIRONMENT"
  | "TDD_CORPORATE_TAX"
  | "TDD_VAT"
  | "TDD_TRANSFER_PRICING"
  | "TDD_WITHHOLDING"
  | "TDD_TAX_INCENTIVES"
  | "OTHER";

export type BuyerType =
  | "STRATEGIC"
  | "FINANCIAL_SPONSOR"
  | "FAMILY_OFFICE"
  | "INDIVIDUAL"
  | "OTHER";

export type BuyerTier = "TIER_1" | "TIER_2" | "TIER_3" | null;

// ── 요청 ──────────────────────────────────────────────────

export interface DealSetupRequest {
  description: string;
  lead_advisor_email: string;
}

// ── AI 미리보기 하위 구조 ─────────────────────────────────

export interface DealSetupTransaction {
  name: string;
  deal_type: DealType;
  side: TransactionSide;
  target_company_name: string;
  client_name: string;
  estimated_deal_value: number | null;
  currency: string;
  deal_structure: DealStructure | null;
  industry: string | null;
  target_close_date: string | null;
  notes: string | null;
}

export interface DealSetupDDItem {
  workstream: DDWorkstream;
  title: string;
  description: string | null;
  due_date: string | null;
}

export interface DealSetupTimelineItem {
  event_type: string;
  title: string;
  description: string | null;
  event_date: string;
}

export interface DealSetupBuyerItem {
  company_name: string;
  buyer_type: BuyerType | null;
  tier: BuyerTier;
  notes: string | null;
}

// ── AI 미리보기 응답 ──────────────────────────────────────

export interface DealSetupPreview {
  transaction: DealSetupTransaction;
  dd_checklist: DealSetupDDItem[];
  timeline: DealSetupTimelineItem[];
  buyer_candidates: DealSetupBuyerItem[];
  cost_usd: number;
  model_used: string;
}

// ── 확인 후 저장 요청 ─────────────────────────────────────

export interface DealSetupConfirm {
  transaction: DealSetupTransaction;
  dd_checklist: DealSetupDDItem[];
  timeline: DealSetupTimelineItem[];
  buyer_candidates: DealSetupBuyerItem[];
  lead_advisor_email: string;
}

// ── 저장 결과 ─────────────────────────────────────────────

export interface DealSetupResult {
  transaction_id: string;
  dd_checklist_count: number;
  timeline_count: number;
  buyer_count: number;
}
