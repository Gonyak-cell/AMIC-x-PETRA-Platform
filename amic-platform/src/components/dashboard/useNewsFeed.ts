/** 대시보드 뉴스 피드 React Query 훅 */

import { useQuery } from "@tanstack/react-query";
import { maApi } from "@/api/maClient";

/* ── Types ─────────────────────────────────────── */

export interface NewsFeedItem {
  id: string;
  title: string;
  lead_text: string | null;
  canonical_url: string;
  source: string;
  source_display: string;
  source_type: "kiis" | "cloudflare";
  published_at: string | null;
  category: string | null;
  category_display: string;
  is_paywalled: boolean;
  markdown_available: boolean;
}

interface NewsFeedResponse {
  items: NewsFeedItem[];
  total: number;
  cached: boolean;
  error: string | null;
}

export interface NewsFeedParams {
  source?: string;
  category?: string;
  page?: number;
  size?: number;
}

/* ── Hook ──────────────────────────────────────── */

export function useNewsFeed(params: NewsFeedParams = {}) {
  const { source, category, page = 1, size = 10 } = params;

  const queryParams: Record<string, string | number> = { page, size };
  if (source) queryParams.source = source;
  if (category) queryParams.category = category;

  const { data, isLoading, isError, error, refetch } =
    useQuery<NewsFeedResponse>({
      queryKey: ["dashboard", "news-feed", queryParams],
      queryFn: async () => {
        const { data: resp } = await maApi.get("/news-feed/latest", {
          params: queryParams,
        });
        return resp;
      },
      staleTime: 5 * 60_000, // 5분
      refetchInterval: 10 * 60_000, // 10분
    });

  return {
    items: data?.items ?? [],
    total: data?.total ?? 0,
    cached: data?.cached ?? false,
    apiError: data?.error ?? null,
    isLoading,
    isError,
    error,
    refetch,
  };
}
