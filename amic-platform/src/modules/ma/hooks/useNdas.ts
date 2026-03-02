import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { maApi } from "@/api/maClient";
import type {
  NDA,
  NDACreate,
  NDAUpdate,
  NDASummary,
} from "@/modules/ma/types/nda";

export function useNdas(txnId: string, buyerId?: string, active = true) {
  return useQuery<NDA[]>({
    queryKey: ["ma", "transactions", txnId, "ndas", { buyerId }],
    queryFn: async () => {
      const params = buyerId ? { buyer_id: buyerId } : {};
      const { data } = await maApi.get(`/transactions/${txnId}/ndas`, {
        params,
      });
      return data;
    },
    enabled: !!txnId && active,
  });
}

export function useNdaSummary(txnId: string, active = true) {
  return useQuery<NDASummary>({
    queryKey: ["ma", "transactions", txnId, "ndas", "summary"],
    queryFn: async () => {
      const { data } = await maApi.get(`/transactions/${txnId}/ndas/summary`);
      return data;
    },
    enabled: !!txnId && active,
  });
}

export function useCreateNda(txnId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: NDACreate) => {
      const { data } = await maApi.post(`/transactions/${txnId}/ndas`, body);
      return data as NDA;
    },
    onSuccess: () => {
      qc.invalidateQueries({
        queryKey: ["ma", "transactions", txnId, "ndas"],
      });
      toast.success("NDA가 생성되었습니다.");
    },
    onError: () => {
      toast.error("NDA 생성에 실패했습니다.");
    },
  });
}

export function useUpdateNda(txnId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ ndaId, body }: { ndaId: string; body: NDAUpdate }) => {
      const { data } = await maApi.patch(
        `/transactions/${txnId}/ndas/${ndaId}`,
        body,
      );
      return data as NDA;
    },
    onSuccess: () => {
      qc.invalidateQueries({
        queryKey: ["ma", "transactions", txnId, "ndas"],
      });
      toast.success("NDA가 수정되었습니다.");
    },
    onError: () => {
      toast.error("NDA 수정에 실패했습니다.");
    },
  });
}

export function useDeleteNda(txnId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (ndaId: string) => {
      await maApi.delete(`/transactions/${txnId}/ndas/${ndaId}`);
    },
    onSuccess: () => {
      qc.invalidateQueries({
        queryKey: ["ma", "transactions", txnId, "ndas"],
      });
      toast.success("NDA가 삭제되었습니다.");
    },
    onError: () => {
      toast.error("NDA 삭제에 실패했습니다.");
    },
  });
}
