import { useQuery } from "@tanstack/react-query";
import { kiisApi } from "@/api/kiisClient";
import type { SearchResponse, SearchParams } from "@/modules/kiis/types/search";

export function useUnifiedSearch(params: SearchParams) {
  return useQuery<SearchResponse>({
    queryKey: ["kiis", "search", params],
    queryFn: async () => {
      const { data } = await kiisApi.get("/search", { params });
      return data;
    },
    enabled: !!params.q && params.q.length >= 2,
  });
}
