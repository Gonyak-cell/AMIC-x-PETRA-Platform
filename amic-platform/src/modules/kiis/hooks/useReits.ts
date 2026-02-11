import { useQuery } from "@tanstack/react-query";
import { kiisApi } from "@/api/kiisClient";
import type {
  REITsDetailResponse,
  REITsListResponse,
  REITsAssetItem,
  ReitListParams,
} from "@/modules/kiis/types/reit";

export function useReits(params: ReitListParams = {}) {
  return useQuery<REITsListResponse>({
    queryKey: ["kiis", "reits", params],
    queryFn: async () => {
      const { data } = await kiisApi.get<REITsListResponse>("/reits", {
        params,
      });
      return data;
    },
  });
}

export function useReitDetail(reitsCode: string) {
  return useQuery<REITsDetailResponse>({
    queryKey: ["kiis", "reits", reitsCode],
    queryFn: async () => {
      const { data } = await kiisApi.get<REITsDetailResponse>(
        `/reits/${reitsCode}`,
      );
      return data;
    },
    enabled: !!reitsCode,
  });
}

export function useReitAssets(reitsCode: string) {
  return useQuery<REITsAssetItem[]>({
    queryKey: ["kiis", "reits", reitsCode, "assets"],
    queryFn: async () => {
      const { data } = await kiisApi.get(
        `/reits/${reitsCode}/assets`,
      );
      return data.items;
    },
    enabled: !!reitsCode,
  });
}
