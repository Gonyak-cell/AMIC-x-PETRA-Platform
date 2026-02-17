import { useQuery } from "@tanstack/react-query";
import { kiisApi } from "@/api/kiisClient";
import type {
  DealItem,
  DealListResponse,
  DealByCompanyParams,
  DealByFundParams,
  DealAmountStats,
  SectorAggregation,
  SectorAggregationResponse,
  StageAggregation,
  StageAggregationResponse,
  YearlyTrend,
  TrendResponse,
  DealAggregationParams,
  DealTrendParams,
  TendencySummaryResponse,
} from "@/modules/kiis/types/deal";

const CORP_CODE_RE = /^\d{8}$/;

export function useDealsByCompany(
  corpCode: string,
  params: DealByCompanyParams = {},
) {
  return useQuery<DealItem[]>({
    queryKey: ["kiis", "deals", "by-company", corpCode, params],
    queryFn: async () => {
      const { data } = await kiisApi.get<DealListResponse>(
        `/deals/by-company/${corpCode}`,
        { params },
      );
      return data.items;
    },
    enabled: CORP_CODE_RE.test(corpCode),
  });
}

export function useDealsBySector(
  params: DealAggregationParams = {},
  options?: { enabled?: boolean },
) {
  return useQuery<SectorAggregation[]>({
    queryKey: ["kiis", "deals", "by-sector", params],
    queryFn: async () => {
      const { data } = await kiisApi.get<SectorAggregationResponse>(
        "/deals/by-sector",
        { params },
      );
      return data.items;
    },
    ...(options?.enabled !== undefined && { enabled: options.enabled }),
  });
}

export function useDealsByStage(
  params: DealAggregationParams = {},
  options?: { enabled?: boolean },
) {
  return useQuery<StageAggregation[]>({
    queryKey: ["kiis", "deals", "by-stage", params],
    queryFn: async () => {
      const { data } = await kiisApi.get<StageAggregationResponse>(
        "/deals/by-stage",
        { params },
      );
      return data.items;
    },
    ...(options?.enabled !== undefined && { enabled: options.enabled }),
  });
}

export function useDealTrends(
  params: DealTrendParams = {},
  options?: { enabled?: boolean },
) {
  return useQuery<YearlyTrend[]>({
    queryKey: ["kiis", "deals", "trends", params],
    queryFn: async () => {
      const { data } = await kiisApi.get<TrendResponse>("/deals/trends", {
        params,
      });
      return data.items;
    },
    ...(options?.enabled !== undefined && { enabled: options.enabled }),
  });
}

export function useDealsByFund(
  fundCode: string,
  params: DealByFundParams = {},
  options?: { enabled?: boolean },
) {
  return useQuery<DealItem[]>({
    queryKey: ["kiis", "deals", "by-fund", fundCode, params],
    queryFn: async () => {
      const { data } = await kiisApi.get<DealListResponse>(
        `/deals/by-fund/${fundCode}`,
        { params },
      );
      return data.items;
    },
    enabled: (options?.enabled ?? true) && fundCode.length > 0,
  });
}

export function useDealStats(
  corpCode: string,
  years = 5,
  options?: { enabled?: boolean },
) {
  return useQuery<DealAmountStats>({
    queryKey: ["kiis", "deals", "stats", corpCode, years],
    queryFn: async () => {
      const { data } = await kiisApi.get<DealAmountStats>("/deals/stats", {
        params: { corp_code: corpCode, years },
      });
      return data;
    },
    enabled: (options?.enabled ?? true) && CORP_CODE_RE.test(corpCode),
  });
}

export function useTendencySummary(
  corpCode: string,
  years = 3,
  options?: { enabled?: boolean },
) {
  return useQuery<TendencySummaryResponse>({
    queryKey: ["kiis", "deals", "tendency-summary", corpCode, years],
    queryFn: async () => {
      const { data } = await kiisApi.get<TendencySummaryResponse>(
        "/deals/tendency-summary",
        { params: { corp_code: corpCode, years } },
      );
      return data;
    },
    enabled: (options?.enabled ?? true) && CORP_CODE_RE.test(corpCode),
  });
}
