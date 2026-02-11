import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { kiisApi } from "@/api/kiisClient";
import type { NewsArticle, NewsListParams } from "@/modules/kiis/types/news";
import type { PaginatedResponse } from "@/modules/kiis/types/company";

export function useNewsList(params: NewsListParams = {}) {
  return useQuery<PaginatedResponse<NewsArticle>>({
    queryKey: ["kiis", "news", params],
    queryFn: async () => {
      const { data } = await kiisApi.get("/news", { params });
      return data;
    },
  });
}

export function useNewsDetail(articleId: string) {
  return useQuery<NewsArticle>({
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
  return useMutation({
    mutationFn: async () => {
      const { data } = await kiisApi.post("/news/collect");
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["kiis", "news"] });
    },
  });
}
