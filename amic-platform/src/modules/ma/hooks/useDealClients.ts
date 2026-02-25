import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { maApi } from "@/api/maClient";

export interface DealClient {
  id: string;
  transaction_id: string;
  email: string;
  display_name: string;
  organization: string | null;
  added_by_email: string | null;
  created_at: string;
}

export interface DealClientCreate {
  email: string;
  display_name: string;
  organization?: string;
}

export function useDealClients(txnId: string) {
  return useQuery<DealClient[]>({
    queryKey: ["ma", "transactions", txnId, "clients"],
    queryFn: async () => {
      const { data } = await maApi.get(`/transactions/${txnId}/clients`);
      return data;
    },
    enabled: !!txnId,
  });
}

export function useAddDealClient(txnId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: DealClientCreate) => {
      const { data } = await maApi.post(`/transactions/${txnId}/clients`, body);
      return data as DealClient;
    },
    onSuccess: () => {
      qc.invalidateQueries({
        queryKey: ["ma", "transactions", txnId, "clients"],
      });
      toast.success("고객이 배정되었습니다.");
    },
    onError: () => {
      toast.error("고객 배정에 실패했습니다.");
    },
  });
}

export function useRemoveDealClient(txnId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (clientId: string) => {
      await maApi.delete(`/transactions/${txnId}/clients/${clientId}`);
    },
    onSuccess: () => {
      qc.invalidateQueries({
        queryKey: ["ma", "transactions", txnId, "clients"],
      });
      toast.success("고객 배정이 해제되었습니다.");
    },
    onError: () => {
      toast.error("고객 배정 해제에 실패했습니다.");
    },
  });
}
