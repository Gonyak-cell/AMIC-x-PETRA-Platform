import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { maApi } from "@/api/maClient";
import type {
  RiskItem,
  RiskItemCreate,
  RiskItemUpdate,
  RiskSummary,
} from "@/modules/ma/types/risk";

export function useRisks(
  txnId: string,
  category?: string,
  status?: string,
  severity?: string,
  active = true,
) {
  return useQuery<RiskItem[]>({
    queryKey: [
      "ma",
      "transactions",
      txnId,
      "risks",
      { category, status, severity },
    ],
    queryFn: async () => {
      const params: Record<string, string> = {};
      if (category) params.category = category;
      if (status) params.status = status;
      if (severity) params.severity = severity;
      const { data } = await maApi.get(`/transactions/${txnId}/risks`, {
        params,
      });
      return data;
    },
    enabled: !!txnId && active,
  });
}

export function useRiskSummary(txnId: string, active = true) {
  return useQuery<RiskSummary>({
    queryKey: ["ma", "transactions", txnId, "risks", "summary"],
    queryFn: async () => {
      const { data } = await maApi.get(`/transactions/${txnId}/risks/summary`);
      return data;
    },
    enabled: !!txnId && active,
  });
}

export function useCreateRisk(txnId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: RiskItemCreate) => {
      const { data } = await maApi.post(`/transactions/${txnId}/risks`, body);
      return data as RiskItem;
    },
    onSuccess: () => {
      qc.invalidateQueries({
        queryKey: ["ma", "transactions", txnId, "risks"],
      });
      toast.success("리스크 항목이 추가되었습니다.");
    },
    onError: () => {
      toast.error("리스크 항목 추가에 실패했습니다.");
    },
  });
}

export function useUpdateRisk(txnId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({
      itemId,
      body,
    }: {
      itemId: string;
      body: RiskItemUpdate;
    }) => {
      const { data } = await maApi.patch(
        `/transactions/${txnId}/risks/${itemId}`,
        body,
      );
      return data as RiskItem;
    },
    onSuccess: () => {
      qc.invalidateQueries({
        queryKey: ["ma", "transactions", txnId, "risks"],
      });
      toast.success("리스크 항목이 수정되었습니다.");
    },
    onError: () => {
      toast.error("리스크 항목 수정에 실패했습니다.");
    },
  });
}

export function useDeleteRisk(txnId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (itemId: string) => {
      await maApi.delete(`/transactions/${txnId}/risks/${itemId}`);
    },
    onSuccess: () => {
      qc.invalidateQueries({
        queryKey: ["ma", "transactions", txnId, "risks"],
      });
      toast.success("리스크 항목이 삭제되었습니다.");
    },
    onError: () => {
      toast.error("리스크 항목 삭제에 실패했습니다.");
    },
  });
}
