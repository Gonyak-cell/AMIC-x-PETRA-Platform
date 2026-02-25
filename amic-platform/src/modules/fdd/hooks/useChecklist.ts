import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import api from "@/api/client";

// ── Types ──────────────────────────────────────────────

export type ChecklistItemStatus =
  | "AUTO_GENERATED"
  | "CONFIRMED"
  | "CORRECTED"
  | "FLAGGED"
  | "NOT_APPLICABLE";

export type ChecklistSeverity = "HIGH" | "MEDIUM" | "LOW" | "INFO";

export type ChecklistStatus =
  | "GENERATING"
  | "PENDING_REVIEW"
  | "REVIEWED"
  | "FINALIZED";

export type ChecklistCategory =
  | "REVENUE_RECOGNITION"
  | "COGS_CLASSIFICATION"
  | "SGA_ANALYSIS"
  | "NON_RECURRING_ITEMS"
  | "RELATED_PARTY_TRANSACTIONS"
  | "EBITDA_ADJUSTMENTS"
  | "NWC_CLASSIFICATION"
  | "AR_AGING"
  | "AP_AGING"
  | "INVENTORY_ANALYSIS"
  | "NWC_SEASONALITY"
  | "DEBT_SCHEDULE"
  | "DEBT_LIKE_ITEMS"
  | "CASH_LIKE_ITEMS"
  | "LEASE_OBLIGATIONS"
  | "TAX_REVIEW"
  | "CONTINGENT_LIABILITIES"
  | "OFF_BALANCE_SHEET";

export interface VdrLink {
  id: string;
  upload_file_id: string | null;
  vdr_folder_id: string | null;
  evidence_link_id: string | null;
  source_detail: Record<string, unknown> | null;
  description: string | null;
}

export interface ChecklistItem {
  id: string;
  category: ChecklistCategory;
  order_index: number;
  title: string;
  description: string;
  auto_finding: string | null;
  auto_amount: string | null;
  user_correction: string | null;
  user_amount: string | null;
  status: ChecklistItemStatus;
  severity: ChecklistSeverity | null;
  reviewed_by: string | null;
  reviewed_at: string | null;
  vdr_links: VdrLink[];
  metadata: Record<string, unknown> | null;
}

export interface Checklist {
  id: string;
  deal_id: string;
  version: number;
  status: ChecklistStatus;
  items: ChecklistItem[];
  notes: string | null;
  created_by: string;
  created_at: string;
  updated_at: string;
  finalized_at: string | null;
  total_items: number;
  confirmed_count: number;
  corrected_count: number;
  flagged_count: number;
  pending_count: number;
}

// ── Category grouping ──────────────────────────────────

export const CATEGORY_GROUPS = {
  "Quality of Earnings": [
    "REVENUE_RECOGNITION",
    "COGS_CLASSIFICATION",
    "SGA_ANALYSIS",
    "NON_RECURRING_ITEMS",
    "RELATED_PARTY_TRANSACTIONS",
    "EBITDA_ADJUSTMENTS",
  ],
  "Net Working Capital": [
    "NWC_CLASSIFICATION",
    "AR_AGING",
    "AP_AGING",
    "INVENTORY_ANALYSIS",
    "NWC_SEASONALITY",
  ],
  "Net Debt": [
    "DEBT_SCHEDULE",
    "DEBT_LIKE_ITEMS",
    "CASH_LIKE_ITEMS",
    "LEASE_OBLIGATIONS",
  ],
  Other: [
    "TAX_REVIEW",
    "CONTINGENT_LIABILITIES",
    "OFF_BALANCE_SHEET",
  ],
} as const;

// ── Hooks ──────────────────────────────────────────────

export function useChecklist(dealId: string) {
  return useQuery({
    queryKey: ["fdd", "checklist", dealId],
    queryFn: async () => {
      const { data } = await api.get<Checklist>(
        `/deals/${dealId}/checklist`
      );
      return data;
    },
    retry: false,
  });
}

export function useUpdateChecklistItem(dealId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({
      itemId,
      update,
    }: {
      itemId: string;
      update: {
        status: ChecklistItemStatus;
        user_correction?: string | null;
        user_amount?: string | null;
      };
    }) => {
      const { data } = await api.put<ChecklistItem>(
        `/deals/${dealId}/checklist/items/${itemId}`,
        update
      );
      return data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["fdd", "checklist", dealId] });
    },
  });
}

export function useBulkUpdateItems(dealId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({
      checklistId,
      items,
    }: {
      checklistId: string;
      items: {
        item_id: string;
        status: ChecklistItemStatus;
        user_correction?: string | null;
        user_amount?: string | null;
      }[];
    }) => {
      const { data } = await api.put<ChecklistItem[]>(
        `/deals/${dealId}/checklist/${checklistId}/bulk-update`,
        { items }
      );
      return data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["fdd", "checklist", dealId] });
    },
  });
}

export function useFinalizeChecklist(dealId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({
      checklistId,
      notes,
    }: {
      checklistId: string;
      notes?: string;
    }) => {
      const { data } = await api.post<Checklist>(
        `/deals/${dealId}/checklist/${checklistId}/finalize`,
        { notes }
      );
      return data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["fdd", "checklist", dealId] });
    },
  });
}
