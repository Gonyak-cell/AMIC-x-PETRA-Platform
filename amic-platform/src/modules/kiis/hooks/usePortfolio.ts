import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { kiisApi } from "@/api/kiisClient";
import type {
  PortfolioListResponse,
  PortfolioListParams,
  PortfolioSummary,
  SyncResponse,
  SurvivalCheckResponse,
  ValuationUpdateRequest,
  ValuationUpdateResponse,
} from "@/modules/kiis/types/portfolio";

export function usePortfolio(corpCode: string, params: PortfolioListParams = {}) {
  return useQuery<PortfolioListResponse>({
    queryKey: ["kiis", "portfolio", corpCode, params],
    queryFn: async () => {
      const { data } = await kiisApi.get<PortfolioListResponse>(
        `/portfolio/by-investor/${corpCode}`,
        { params },
      );
      return data;
    },
    enabled: !!corpCode,
  });
}

export function usePortfolioSummary(corpCode: string) {
  return useQuery<PortfolioSummary>({
    queryKey: ["kiis", "portfolio", corpCode, "summary"],
    queryFn: async () => {
      const { data } = await kiisApi.get<PortfolioSummary>(
        `/portfolio/by-investor/${corpCode}/summary`,
      );
      return data;
    },
    enabled: !!corpCode,
  });
}

export function useSyncPortfolio(corpCode: string) {
  const queryClient = useQueryClient();
  return useMutation<SyncResponse>({
    mutationFn: async () => {
      const { data } = await kiisApi.post(
        `/portfolio/by-investor/${corpCode}/sync`,
      );
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["kiis", "portfolio", corpCode],
      });
    },
  });
}

export function useCheckSurvival(corpCode: string) {
  const queryClient = useQueryClient();
  return useMutation<SurvivalCheckResponse, Error, number>({
    mutationFn: async (portfolioId) => {
      const { data } = await kiisApi.post(
        `/portfolio/${portfolioId}/check-survival`,
      );
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["kiis", "portfolio", corpCode],
      });
    },
  });
}

export function useUpdateValuation(corpCode: string) {
  const queryClient = useQueryClient();
  return useMutation<
    ValuationUpdateResponse,
    Error,
    { portfolioId: number; body: ValuationUpdateRequest }
  >({
    mutationFn: async ({ portfolioId, body }) => {
      const { data } = await kiisApi.put(
        `/portfolio/${portfolioId}/valuation`,
        body,
      );
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["kiis", "portfolio", corpCode],
      });
    },
  });
}
