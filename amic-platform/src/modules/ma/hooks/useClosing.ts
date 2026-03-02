import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { maApi } from "@/api/maClient";
import type {
  ClosingChecklistItem,
  ClosingChecklistCreate,
  ClosingChecklistUpdate,
  ClosingChecklistSummary,
} from "@/modules/ma/types/closing";

export function useClosingChecklist(
  txnId: string,
  category?: string,
  active = true,
) {
  return useQuery<ClosingChecklistItem[]>({
    queryKey: ["ma", "transactions", txnId, "closing", { category }],
    queryFn: async () => {
      const params = category ? { category } : {};
      const { data } = await maApi.get(`/transactions/${txnId}/closing`, {
        params,
      });
      return data;
    },
    enabled: !!txnId && active,
  });
}

export function useClosingSummary(txnId: string, active = true) {
  return useQuery<ClosingChecklistSummary>({
    queryKey: ["ma", "transactions", txnId, "closing", "summary"],
    queryFn: async () => {
      const { data } = await maApi.get(
        `/transactions/${txnId}/closing/summary`,
      );
      return data;
    },
    enabled: !!txnId && active,
  });
}

export function useCreateClosingItem(txnId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: ClosingChecklistCreate) => {
      const { data } = await maApi.post(`/transactions/${txnId}/closing`, body);
      return data as ClosingChecklistItem;
    },
    onSuccess: () => {
      qc.invalidateQueries({
        queryKey: ["ma", "transactions", txnId, "closing"],
      });
      toast.success("Closing 항목이 생성되었습니다.");
    },
    onError: () => {
      toast.error("Closing 항목 생성에 실패했습니다.");
    },
  });
}

export function useUpdateClosingItem(txnId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({
      itemId,
      body,
    }: {
      itemId: string;
      body: ClosingChecklistUpdate;
    }) => {
      const { data } = await maApi.patch(
        `/transactions/${txnId}/closing/${itemId}`,
        body,
      );
      return data as ClosingChecklistItem;
    },
    onSuccess: () => {
      qc.invalidateQueries({
        queryKey: ["ma", "transactions", txnId, "closing"],
      });
      toast.success("Closing 항목이 수정되었습니다.");
    },
    onError: () => {
      toast.error("Closing 항목 수정에 실패했습니다.");
    },
  });
}

export function useDeleteClosingItem(txnId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (itemId: string) => {
      await maApi.delete(`/transactions/${txnId}/closing/${itemId}`);
    },
    onSuccess: () => {
      qc.invalidateQueries({
        queryKey: ["ma", "transactions", txnId, "closing"],
      });
      toast.success("Closing 항목이 삭제되었습니다.");
    },
    onError: () => {
      toast.error("Closing 항목 삭제에 실패했습니다.");
    },
  });
}
