import { useQuery } from "@tanstack/react-query";
import { kiisApi } from "@/api/kiisClient";
import type { SearchResult, SearchParams } from "@/modules/kiis/types/search";
import type { PaginatedResponse } from "@/modules/kiis/types/company";

export function useUnifiedSearch(params: SearchParams) {
  return useQuery<PaginatedResponse<SearchResult>>({
    queryKey: ["kiis", "search", params],
    queryFn: async () => {
      const { data } = await kiisApi.get("/search", { params });
      return data;
    },
    enabled: !!params.q && params.q.length >= 2,
  });
}
