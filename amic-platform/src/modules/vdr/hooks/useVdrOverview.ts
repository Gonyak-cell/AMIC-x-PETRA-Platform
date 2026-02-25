import { useQuery } from "@tanstack/react-query";

import { maApi } from "@/api/maClient";
import type { VdrOverviewItem } from "@/modules/vdr/types/overview";

export function useVdrOverview() {
  return useQuery<VdrOverviewItem[]>({
    queryKey: ["vdr", "overview"],
    queryFn: async () => {
      const { data } = await maApi.get("/vdr/overview");
      return data;
    },
  });
}
