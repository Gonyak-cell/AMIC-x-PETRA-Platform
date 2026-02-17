import { useQuery } from "@tanstack/react-query";
import { kiisApi } from "@/api/kiisClient";
import type {
  FundDetailResponse,
  FundListResponse,
  FundManagerItem,
  FundManagerListResponse,
  FundListParams,
} from "@/modules/kiis/types/fund";

const FUND_LIST_STALE_TIME = 5 * 60 * 1000; // 5분
const FUND_DETAIL_STALE_TIME = 10 * 60 * 1000; // 10분
const FUND_GC_TIME = 30 * 60 * 1000; // 30분

export function useFunds(params: FundListParams = {}) {
  return useQuery<FundListResponse>({
    queryKey: ["kiis", "funds", params],
    queryFn: async () => {
      const { data } = await kiisApi.get<FundListResponse>("/kofia/funds", {
        params,
      });
      return data;
    },
    staleTime: FUND_LIST_STALE_TIME,
    gcTime: FUND_GC_TIME,
  });
}

export function useFundDetail(fundCode: string) {
  return useQuery<FundDetailResponse>({
    queryKey: ["kiis", "funds", fundCode],
    queryFn: async () => {
      const { data } = await kiisApi.get<FundDetailResponse>(
        `/kofia/funds/${fundCode}`,
      );
      return data;
    },
    enabled: !!fundCode,
    staleTime: FUND_DETAIL_STALE_TIME,
    gcTime: FUND_GC_TIME,
  });
}

export function useFundManagers(
  params: {
    company_name?: string;
    fund_code?: string;
    page?: number;
    size?: number;
  } = {},
) {
  return useQuery<FundManagerItem[]>({
    queryKey: ["kiis", "fund-managers", params],
    queryFn: async () => {
      const { data } = await kiisApi.get<FundManagerListResponse>("/kofia/managers", {
        params,
      });
      return data.items;
    },
    staleTime: FUND_LIST_STALE_TIME,
    gcTime: FUND_GC_TIME,
  });
}
