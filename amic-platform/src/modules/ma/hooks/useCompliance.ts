import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { maApi } from "@/api/maClient";
import type {
  ComplianceItem,
  ComplianceItemCreate,
  ComplianceItemUpdate,
  ComplianceSummary,
} from "@/modules/ma/types/compliance";

export function useCompliance(
  txnId: string,
  category?: string,
  status?: string,
  active = true,
) {
  return useQuery<ComplianceItem[]>({
    queryKey: ["ma", "transactions", txnId, "compliance", { category, status }],
    queryFn: async () => {
      const params: Record<string, string> = {};
      if (category) params.category = category;
      if (status) params.status = status;
      const { data } = await maApi.get(`/transactions/${txnId}/compliance`, {
        params,
      });
      return data;
    },
    enabled: !!txnId && active,
  });
}

export function useComplianceSummary(txnId: string, active = true) {
  return useQuery<ComplianceSummary>({
    queryKey: ["ma", "transactions", txnId, "compliance", "summary"],
    queryFn: async () => {
      const { data } = await maApi.get(
        `/transactions/${txnId}/compliance/summary`,
      );
      return data;
    },
    enabled: !!txnId && active,
  });
}

export function useCreateCompliance(txnId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: ComplianceItemCreate) => {
      const { data } = await maApi.post(
        `/transactions/${txnId}/compliance`,
        body,
      );
      return data as ComplianceItem;
    },
    onSuccess: () => {
      qc.invalidateQueries({
        queryKey: ["ma", "transactions", txnId, "compliance"],
      });
      toast.success("컴플라이언스 항목이 추가되었습니다.");
    },
    onError: () => {
      toast.error("컴플라이언스 항목 추가에 실패했습니다.");
    },
  });
}

export function useUpdateCompliance(txnId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({
      itemId,
      body,
    }: {
      itemId: string;
      body: ComplianceItemUpdate;
    }) => {
      const { data } = await maApi.patch(
        `/transactions/${txnId}/compliance/${itemId}`,
        body,
      );
      return data as ComplianceItem;
    },
    onSuccess: () => {
      qc.invalidateQueries({
        queryKey: ["ma", "transactions", txnId, "compliance"],
      });
      toast.success("컴플라이언스 항목이 수정되었습니다.");
    },
    onError: () => {
      toast.error("컴플라이언스 항목 수정에 실패했습니다.");
    },
  });
}

export function useDeleteCompliance(txnId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (itemId: string) => {
      await maApi.delete(`/transactions/${txnId}/compliance/${itemId}`);
    },
    onSuccess: () => {
      qc.invalidateQueries({
        queryKey: ["ma", "transactions", txnId, "compliance"],
      });
      toast.success("컴플라이언스 항목이 삭제되었습니다.");
    },
    onError: () => {
      toast.error("컴플라이언스 항목 삭제에 실패했습니다.");
    },
  });
}
