import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { kiisApi } from "@/api/kiisClient";
import type {
  NewsDetail,
  NewsListParams,
  NewsListResponse,
  NewsCollectResponse,
} from "@/modules/kiis/types/news";

export function useNewsList(params: NewsListParams = {}) {
  return useQuery<NewsListResponse>({
    queryKey: ["kiis", "news", params],
    queryFn: async () => {
      const { data } = await kiisApi.get("/news", { params });
      return data;
    },
  });
}

export function useNewsDetail(articleId: number) {
  return useQuery<NewsDetail>({
    queryKey: ["kiis", "news", articleId],
    queryFn: async () => {
      const { data } = await kiisApi.get(`/news/${articleId}`);
      return data;
    },
    enabled: !!articleId,
  });
}

export function useCollectNews() {
  const queryClient = useQueryClient();
  return useMutation<NewsCollectResponse[], Error, { source?: string } | void>({
    mutationFn: async (vars) => {
      const { data } = await kiisApi.post("/news/collect", null, {
        params: vars ?? {},
      });
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["kiis", "news"] });
    },
  });
}
