import { useQuery } from "@tanstack/react-query";
import { kiisApi } from "@/api/kiisClient";
import type { GPListResponse, GPListParams } from "@/modules/kiis/types/gp";

const GP_LIST_STALE_TIME = 5 * 60 * 1000; // 5분
const GP_GC_TIME = 30 * 60 * 1000; // 30분

export function useGPs(params: GPListParams = {}) {
  return useQuery<GPListResponse>({
    queryKey: ["kiis", "gps", params],
    queryFn: async () => {
      const { data } = await kiisApi.get<GPListResponse>("/kofia/gp", {
        params,
      });
      return data;
    },
    staleTime: GP_LIST_STALE_TIME,
    gcTime: GP_GC_TIME,
  });
}
