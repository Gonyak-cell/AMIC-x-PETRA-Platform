import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { maApi } from "@/api/maClient";
import type {
  NDA,
  NDACreate,
  NDASummary,
  NDAUpdate,
  NdaPartyType,
} from "@/modules/ma/types/nda";

interface UseNdasOptions {
  buyerId?: string;
  partyType?: NdaPartyType;
  active?: boolean;
}

function invalidateNdaRelatedQueries(
  qc: ReturnType<typeof useQueryClient>,
  txnId: string,
) {
  qc.invalidateQueries({
    queryKey: ["ma", "transactions", txnId, "ndas"],
  });
  qc.invalidateQueries({
    queryKey: ["ma", "transactions", txnId, "buyers"],
  });
  qc.invalidateQueries({
    queryKey: ["ma", "transactions", txnId, "short-list", "overview"],
  });
  qc.invalidateQueries({
    queryKey: ["ma", "transactions", txnId, "workspace-summary"],
  });
}

export function useNdas(txnId: string, options: UseNdasOptions = {}) {
  const { buyerId, partyType, active = true } = options;

  return useQuery<NDA[]>({
    queryKey: ["ma", "transactions", txnId, "ndas", { buyerId, partyType }],
    queryFn: async () => {
      const params = {
        ...(buyerId ? { buyer_id: buyerId } : {}),
        ...(partyType ? { party_type: partyType } : {}),
      };
      const { data } = await maApi.get(`/transactions/${txnId}/ndas`, {
        params,
      });
      return data;
    },
    enabled: !!txnId && active,
  });
}

export function useNdaSummary(
  txnId: string,
  options: Pick<UseNdasOptions, "partyType" | "active"> = {},
) {
  const { partyType, active = true } = options;

  return useQuery<NDASummary>({
    queryKey: ["ma", "transactions", txnId, "ndas", "summary", { partyType }],
    queryFn: async () => {
      const { data } = await maApi.get(`/transactions/${txnId}/ndas/summary`, {
        params: partyType ? { party_type: partyType } : {},
      });
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
      invalidateNdaRelatedQueries(qc, txnId);
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
      invalidateNdaRelatedQueries(qc, txnId);
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
      invalidateNdaRelatedQueries(qc, txnId);
      toast.success("NDA가 삭제되었습니다.");
    },
    onError: () => {
      toast.error("NDA 삭제에 실패했습니다.");
    },
  });
}
