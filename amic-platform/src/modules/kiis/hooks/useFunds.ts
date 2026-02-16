import { useQuery } from "@tanstack/react-query";
import { kiisApi } from "@/api/kiisClient";
import type {
  FundDetailResponse,
  FundListResponse,
  FundManagerItem,
  FundManagerListResponse,
  FundListParams,
} from "@/modules/kiis/types/fund";

export function useFunds(params: FundListParams = {}) {
  return useQuery<FundListResponse>({
    queryKey: ["kiis", "funds", params],
    queryFn: async () => {
      const { data } = await kiisApi.get<FundListResponse>("/kofia/funds", {
        params,
      });
      return data;
    },
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
  });
}
