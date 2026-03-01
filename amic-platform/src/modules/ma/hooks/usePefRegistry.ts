import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { maApi } from "@/api/maClient";
import type { FIRecommendation } from "@/modules/ma/types/pef_registry";
import type { BiddingSummary } from "@/modules/ma/types/buyer";

export function useFIRecommendations(txnId: string) {
  return useQuery({
    queryKey: ["fi-recommendations", txnId],
    queryFn: async () => {
      const { data } = await maApi.get<FIRecommendation[]>(
        `/transactions/${txnId}/fi-recommendations`,
      );
      return data;
    },
    enabled: !!txnId,
    staleTime: 60_000,
  });
}

export function useBiddingSummary(txnId: string) {
  return useQuery({
    queryKey: ["bidding-summary", txnId],
    queryFn: async () => {
      const { data } = await maApi.get<BiddingSummary>(
        `/transactions/${txnId}/buyers/bidding-summary`,
      );
      return data;
    },
    enabled: !!txnId,
    staleTime: 30_000,
  });
}

export function usePromoteShortList(txnId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (buyerIds: string[]) => {
      const { data } = await maApi.post(
        `/transactions/${txnId}/buyers/promote-short-list`,
        { buyer_ids: buyerIds },
      );
      return data;
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: ["buyers", txnId],
      });
    },
  });
}
