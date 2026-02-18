import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { maApi } from "@/api/maClient";
import type {
  DDChecklistItem,
  DDChecklistCreate,
  DDChecklistUpdate,
  DDChecklistSummary,
} from "@/modules/ma/types/dd_checklist";

export function useDDChecklist(
  txnId: string,
  workstream?: string,
  status?: string,
) {
  return useQuery<DDChecklistItem[]>({
    queryKey: [
      "ma",
      "transactions",
      txnId,
      "dd-checklist",
      { workstream, status },
    ],
    queryFn: async () => {
      const params: Record<string, string> = {};
      if (workstream) params.workstream = workstream;
      if (status) params.status = status;
      const { data } = await maApi.get(
        `/transactions/${txnId}/dd-checklist`,
        { params },
      );
      return data;
    },
    enabled: !!txnId,
  });
}

export function useDDChecklistSummary(txnId: string) {
  return useQuery<DDChecklistSummary>({
    queryKey: ["ma", "transactions", txnId, "dd-checklist", "summary"],
    queryFn: async () => {
      const { data } = await maApi.get(
        `/transactions/${txnId}/dd-checklist/summary`,
      );
      return data;
    },
    enabled: !!txnId,
  });
}

export function useCreateDDChecklistItem(txnId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: DDChecklistCreate) => {
      const { data } = await maApi.post(
        `/transactions/${txnId}/dd-checklist`,
        body,
      );
      return data as DDChecklistItem;
    },
    onSuccess: () => {
      qc.invalidateQueries({
        queryKey: ["ma", "transactions", txnId, "dd-checklist"],
      });
      toast.success("체크리스트 항목이 추가되었습니다.");
    },
    onError: () => {
      toast.error("체크리스트 항목 추가에 실패했습니다.");
    },
  });
}

export function useUpdateDDChecklistItem(txnId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({
      itemId,
      body,
    }: {
      itemId: string;
      body: DDChecklistUpdate;
    }) => {
      const { data } = await maApi.patch(
        `/transactions/${txnId}/dd-checklist/${itemId}`,
        body,
      );
      return data as DDChecklistItem;
    },
    onSuccess: () => {
      qc.invalidateQueries({
        queryKey: ["ma", "transactions", txnId, "dd-checklist"],
      });
    },
    onError: () => {
      toast.error("체크리스트 항목 수정에 실패했습니다.");
    },
  });
}

export function useDeleteDDChecklistItem(txnId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (itemId: string) => {
      await maApi.delete(`/transactions/${txnId}/dd-checklist/${itemId}`);
    },
    onSuccess: () => {
      qc.invalidateQueries({
        queryKey: ["ma", "transactions", txnId, "dd-checklist"],
      });
      toast.success("체크리스트 항목이 삭제되었습니다.");
    },
    onError: () => {
      toast.error("체크리스트 항목 삭제에 실패했습니다.");
    },
  });
}
