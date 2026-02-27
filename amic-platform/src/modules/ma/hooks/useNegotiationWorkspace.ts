import { useQuery } from "@tanstack/react-query";
import { maApi } from "@/api/maClient";
import type { NegotiationGanttData, MarkupComparison } from "@/modules/ma/types/negotiation_workspace";

export function useNegotiationGantt(txnId: string) {
  return useQuery<NegotiationGanttData>({
    queryKey: ["ma", "transactions", txnId, "contracts", "negotiation-gantt"],
    queryFn: async () => {
      const { data } = await maApi.get(`/transactions/${txnId}/contracts/negotiation-gantt`);
      return data;
    },
    enabled: !!txnId,
  });
}

export function useMarkupComparison(
  txnId: string,
  contractId: string | null,
  versionA: number | null,
  versionB: number | null,
) {
  return useQuery<MarkupComparison>({
    queryKey: ["ma", "transactions", txnId, "contracts", contractId, "markups", "compare", versionA, versionB],
    queryFn: async () => {
      const { data } = await maApi.get(
        `/transactions/${txnId}/contracts/${contractId}/markups/compare`,
        { params: { version_a: versionA, version_b: versionB } },
      );
      return data;
    },
    enabled: !!txnId && !!contractId && versionA != null && versionB != null && versionA !== versionB,
  });
}
