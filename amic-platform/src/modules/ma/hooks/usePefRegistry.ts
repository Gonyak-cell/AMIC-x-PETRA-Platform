import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import axios from "axios";
import { toast } from "sonner";
import { maApi } from "@/api/maClient";
import type { FIRecommendation } from "@/modules/ma/types/pef_registry";
import type { BiddingSummary } from "@/modules/ma/types/buyer";

interface FIRecommendationParams {
  excludeProjectFunds?: boolean;
  lowerMultiplier?: number;
  upperMultiplier?: number;
  limit?: number;
}

export function useFIRecommendations(
  txnId: string,
  params?: FIRecommendationParams,
) {
  return useQuery({
    queryKey: ["ma", "transactions", txnId, "fi-recommendations", params],
    queryFn: async () => {
      const { data } = await maApi.get<FIRecommendation[]>(
        `/transactions/${txnId}/fi-recommendations`,
        {
          params: {
            ...(params?.excludeProjectFunds !== undefined && {
              exclude_project_funds: params.excludeProjectFunds,
            }),
            ...(params?.lowerMultiplier !== undefined && {
              lower_multiplier: params.lowerMultiplier,
            }),
            ...(params?.upperMultiplier !== undefined && {
              upper_multiplier: params.upperMultiplier,
            }),
            ...(params?.limit !== undefined && {
              limit: params.limit,
            }),
          },
        },
      );
      return data;
    },
    enabled: !!txnId,
    staleTime: 60_000,
    retry: (failureCount, error) => {
      // 응답이 있으면 5xx만 재시도, 4xx(422 배수 오류, 401 인증 실패 등)는 재시도하지 않음
      if (axios.isAxiosError(error) && error.response) {
        return error.response.status >= 500 && failureCount < 2;
      }
      // 네트워크 에러(응답 없음): 2회까지 재시도
      return failureCount < 2;
    },
  });
}

export function useBiddingSummary(txnId: string) {
  return useQuery({
    queryKey: ["ma", "transactions", txnId, "bidding-summary"],
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
        queryKey: ["ma", "transactions", txnId, "buyers"],
      });
    },
    onError: () => {
      toast.error("Short-List 승격에 실패했습니다.");
    },
  });
}
