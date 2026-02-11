import { useState, useEffect, useCallback } from "react";
import { useQueries } from "@tanstack/react-query";
import api from "@/api/client";
import { kiisApi } from "@/api/kiisClient";
import { imApi } from "@/api/imClient";
import { getItem, setItem } from "@/lib/storage";
import type { Deal } from "@/modules/fdd/types/deal";
import type { Document } from "@/modules/im/types/document";
import type { GlobalSearchResult } from "@/types/search";

const RECENT_KEY = "recent_searches";
const MAX_RECENT = 5;

function normalizeDeals(deals: Deal[]): GlobalSearchResult[] {
  return deals.map((d) => ({
    id: d.id,
    module: "fdd" as const,
    type: "deal",
    title: d.name,
    subtitle: d.target_company_name,
    path: `/fdd/deals/${d.id}`,
  }));
}

function normalizeKiisResults(
  items: Array<{ type: string; id: string; name: string; description: string | null }>,
): GlobalSearchResult[] {
  const typeRoutes: Record<string, string> = {
    company: "/kiis/companies",
    fund: "/kiis/funds",
    reit: "/kiis/reits",
    news: "/kiis/news",
  };
  return items.map((item) => ({
    id: item.id,
    module: "kiis" as const,
    type: item.type,
    title: item.name,
    subtitle: item.description,
    path: `${typeRoutes[item.type] ?? "/kiis"}/${item.id}`,
  }));
}

function normalizeDocuments(docs: Document[]): GlobalSearchResult[] {
  return docs.map((d) => ({
    id: d.id,
    module: "im" as const,
    type: "project",
    title: d.project_name ?? d.company_name,
    subtitle: d.company_name,
    path: `/im/${d.id}`,
  }));
}

export function useGlobalSearch(query: string) {
  const [debouncedQuery, setDebouncedQuery] = useState("");

  useEffect(() => {
    const timer = setTimeout(() => setDebouncedQuery(query), 300);
    return () => clearTimeout(timer);
  }, [query]);

  const enabled = debouncedQuery.length >= 2;

  const queryResults = useQueries({
    queries: [
      {
        queryKey: ["global-search", "fdd", debouncedQuery],
        queryFn: async () => {
          const { data } = await api.get<Deal[]>("/deals", {
            params: { search: debouncedQuery },
          });
          return normalizeDeals(data);
        },
        enabled,
        staleTime: 10_000,
      },
      {
        queryKey: ["global-search", "kiis", debouncedQuery],
        queryFn: async () => {
          const { data } = await kiisApi.get<{
            items: Array<{ type: string; id: string; name: string; description: string | null }>;
          }>("/search", { params: { q: debouncedQuery } });
          return normalizeKiisResults(data.items);
        },
        enabled,
        staleTime: 10_000,
      },
      {
        queryKey: ["global-search", "im", debouncedQuery],
        queryFn: async () => {
          const { data } = await imApi.get<{ items: Document[] }>("/documents", {
            params: { search: debouncedQuery },
          });
          return normalizeDocuments(data.items);
        },
        enabled,
        staleTime: 10_000,
      },
    ],
  });

  const isLoading = enabled && queryResults.some((r) => r.isLoading);

  const results: GlobalSearchResult[] = queryResults.flatMap(
    (r) => r.data ?? [],
  );

  // Recent searches management
  const [recentSearches, setRecentSearches] = useState<string[]>(() =>
    getItem<string[]>(RECENT_KEY, []),
  );

  const addRecentSearch = useCallback((term: string) => {
    setRecentSearches((prev) => {
      const filtered = prev.filter((s) => s !== term);
      const next = [term, ...filtered].slice(0, MAX_RECENT);
      setItem(RECENT_KEY, next);
      return next;
    });
  }, []);

  const clearRecentSearches = useCallback(() => {
    setRecentSearches([]);
    setItem(RECENT_KEY, []);
  }, []);

  return {
    results,
    isLoading,
    recentSearches,
    addRecentSearch,
    clearRecentSearches,
  };
}
