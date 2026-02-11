import { useQuery } from "@tanstack/react-query";
import { kiisApi } from "@/api/kiisClient";
import type { DashboardSummary } from "@/modules/kiis/types/dashboard";

export function useDashboardSummary() {
  return useQuery<DashboardSummary>({
    queryKey: ["kiis", "dashboard", "summary"],
    queryFn: async () => {
      const { data } = await kiisApi.get("/dashboard/summary");
      return data;
    },
  });
}
