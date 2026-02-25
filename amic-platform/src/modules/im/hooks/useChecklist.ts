import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { imApi } from "@/api/imClient";
import type {
  Checklist,
  ChecklistItem,
  ChecklistSummary,
} from "@/modules/im/types/checklist";
import { CHECKLIST_IN_PROGRESS_STATUSES } from "@/modules/im/types/checklist";

const POLL_INTERVAL_MS = 3_000;

// ── Query Keys ──────────────────────────────────────────────

const checklistQK = (documentId: string) =>
  ["im", "documents", documentId, "checklist"] as const;

const summaryQK = (documentId: string) =>
  ["im", "documents", documentId, "checklist", "summary"] as const;

// ── Queries ─────────────────────────────────────────────────

/** Fetch the full checklist (with items) for a document. */
export function useChecklist(documentId: string) {
  return useQuery<Checklist>({
    queryKey: checklistQK(documentId),
    queryFn: async () => {
      const { data } = await imApi.get(
        `/documents/${documentId}/checklist`,
      );
      return data;
    },
    enabled: !!documentId,
    refetchInterval: (query): number | false => {
      const status = query.state.data?.status;
      if (status && CHECKLIST_IN_PROGRESS_STATUSES.includes(status)) {
        return POLL_INTERVAL_MS;
      }
      return false;
    },
  });
}

/** Fetch the aggregated checklist summary (category breakdown). */
export function useChecklistSummary(documentId: string) {
  return useQuery<ChecklistSummary>({
    queryKey: summaryQK(documentId),
    queryFn: async () => {
      const { data } = await imApi.get(
        `/documents/${documentId}/checklist/summary`,
      );
      return data;
    },
    enabled: !!documentId,
  });
}

// ── Mutations ───────────────────────────────────────────────

/** Update a single checklist item (inline edit). */
export function useUpdateChecklistItem(documentId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({
      itemId,
      body,
    }: {
      itemId: string;
      body: Partial<Pick<ChecklistItem, "confirmed_value" | "status" | "notes">>;
    }) => {
      const { data } = await imApi.patch(
        `/documents/${documentId}/checklist/items/${itemId}`,
        body,
      );
      return data as ChecklistItem;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: checklistQK(documentId) });
      qc.invalidateQueries({ queryKey: summaryQK(documentId) });
    },
    onError: () => {
      toast.error("Failed to update checklist item");
    },
  });
}

/** Batch update multiple checklist items (e.g. "confirm all in category"). */
export function useBatchUpdateItems(documentId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (
      items: { item_id: string; status: string; confirmed_value?: string }[],
    ) => {
      const { data } = await imApi.post(
        `/documents/${documentId}/checklist/items/batch-update`,
        { items },
      );
      return data as { updated_count: number };
    },
    onSuccess: (result) => {
      qc.invalidateQueries({ queryKey: checklistQK(documentId) });
      qc.invalidateQueries({ queryKey: summaryQK(documentId) });
      toast.success(`${result.updated_count} items updated`);
    },
    onError: () => {
      toast.error("Failed to batch update items");
    },
  });
}

/** Confirm the entire checklist and trigger IM generation. */
export function useConfirmChecklist(documentId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async () => {
      const { data } = await imApi.post(
        `/documents/${documentId}/checklist/confirm`,
      );
      return data as { status: string; generation_task_id: string | null };
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: checklistQK(documentId) });
      qc.invalidateQueries({ queryKey: summaryQK(documentId) });
      qc.invalidateQueries({ queryKey: ["im", "documents", documentId] });
      toast.success("Checklist confirmed — IM generation started");
    },
    onError: () => {
      toast.error("Failed to confirm checklist");
    },
  });
}
