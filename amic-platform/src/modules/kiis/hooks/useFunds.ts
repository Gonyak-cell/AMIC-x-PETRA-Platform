import { useQuery } from "@tanstack/react-query";
import { kiisApi } from "@/api/kiisClient";
import type {
  FundDetailResponse,
  FundListResponse,
  FundManagerItem,
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

export function useFundManagers(params: { company_name?: string } = {}) {
  return useQuery<FundManagerItem[]>({
    queryKey: ["kiis", "managers", params],
    queryFn: async () => {
      const { data } = await kiisApi.get<FundManagerItem[]>("/kofia/managers", {
        params,
      });
      return data;
    },
  });
}
