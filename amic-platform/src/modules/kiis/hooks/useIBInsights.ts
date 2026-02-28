import { useQuery } from "@tanstack/react-query";
import { kiisApi } from "@/api/kiisClient";
import type { IBInsightResponse } from "@/modules/kiis/types/ibInsight";

const IB_INSIGHTS_STALE_TIME = 5 * 60 * 1000; // 5분
const IB_INSIGHTS_GC_TIME = 30 * 60 * 1000; // 30분

export function useIBInsights(corpCode: string, months = 6) {
  return useQuery<IBInsightResponse>({
    queryKey: ["kiis", "ib-insights", corpCode, months],
    queryFn: async () => {
      const { data } = await kiisApi.get(`/gps/${corpCode}/ib-insights`, {
        params: { months },
      });
      return data;
    },
    enabled: /^\d{8}$/.test(corpCode),
    staleTime: IB_INSIGHTS_STALE_TIME,
    gcTime: IB_INSIGHTS_GC_TIME,
  });
}
