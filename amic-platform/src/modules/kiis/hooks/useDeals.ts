import { useQuery } from "@tanstack/react-query";
import { kiisApi } from "@/api/kiisClient";
import type {
  DealItem,
  DealListResponse,
  SectorAggregation,
  SectorAggregationResponse,
  StageAggregation,
  StageAggregationResponse,
  YearlyTrend,
  TrendResponse,
  DealAggregationParams,
} from "@/modules/kiis/types/deal";

export function useDealsByCompany(corpCode: string) {
  return useQuery<DealItem[]>({
    queryKey: ["kiis", "deals", "by-company", corpCode],
    queryFn: async () => {
      const { data } = await kiisApi.get<DealListResponse>(
        `/deals/by-company/${corpCode}`,
      );
      return data.items;
    },
    enabled: !!corpCode,
  });
}

export function useDealsBySector(params: DealAggregationParams = {}) {
  return useQuery<SectorAggregation[]>({
    queryKey: ["kiis", "deals", "by-sector", params],
    queryFn: async () => {
      const { data } = await kiisApi.get<SectorAggregationResponse>(
        "/deals/by-sector",
        { params },
      );
      return data.items;
    },
  });
}

export function useDealsByStage(params: DealAggregationParams = {}) {
  return useQuery<StageAggregation[]>({
    queryKey: ["kiis", "deals", "by-stage", params],
    queryFn: async () => {
      const { data } = await kiisApi.get<StageAggregationResponse>(
        "/deals/by-stage",
        { params },
      );
      return data.items;
    },
  });
}

export function useDealTrends(params: DealAggregationParams = {}) {
  return useQuery<YearlyTrend[]>({
    queryKey: ["kiis", "deals", "trends", params],
    queryFn: async () => {
      const { data } = await kiisApi.get<TrendResponse>("/deals/trends", {
        params,
      });
      return data.items;
    },
  });
}
