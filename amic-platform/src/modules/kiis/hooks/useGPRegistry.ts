import { useQuery } from "@tanstack/react-query";
import { kiisApi } from "@/api/kiisClient";
import type {
  GPRegistryListResponse,
  GPRegistryParams,
} from "@/modules/kiis/types/gpRegistry";

const GP_REGISTRY_STALE_TIME = 30 * 60 * 1000; // 30분 (공공데이터 갱신 주기가 느림)
const GP_REGISTRY_GC_TIME = 60 * 60 * 1000; // 1시간

export function useGPRegistry(params: GPRegistryParams = {}) {
  return useQuery<GPRegistryListResponse>({
    queryKey: ["kiis", "gp-registry", params],
    queryFn: async () => {
      const { data } = await kiisApi.get<GPRegistryListResponse>(
        "/public-data/gp",
        { params },
      );
      return data;
    },
    staleTime: GP_REGISTRY_STALE_TIME,
    gcTime: GP_REGISTRY_GC_TIME,
  });
}
