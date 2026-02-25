import { useState, useEffect, useCallback } from "react";
import { useQueries } from "@tanstack/react-query";
import api from "@/api/client";
import { kiisApi } from "@/api/kiisClient";
import { imApi } from "@/api/imClient";
import { toArray } from "@/api/safe-parse";
import { getItem, setItem } from "@/lib/storage";
import type { Deal } from "@/modules/fdd/types/deal";
import type { Document } from "@/modules/im/types/document";
import type { GlobalSearchResult, SearchModule } from "@/types/search";

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
          const { data } = await api.get("/deals", { params: { limit: 200 } });
          const deals = toArray<Deal>(data);
          const q = debouncedQuery.toLowerCase();
          return normalizeDeals(
            deals.filter(
              (d) =>
                d.name?.toLowerCase().includes(q) ||
                (d.target_company_name?.toLowerCase().includes(q) ?? false),
            ),
          );
        },
        enabled,
        staleTime: 10_000,
      },
      {
        queryKey: ["global-search", "kiis", debouncedQuery],
        queryFn: async () => {
          const { data } = await kiisApi.get("/search", { params: { q: debouncedQuery } });
          return normalizeKiisResults(toArray(data));
        },
        enabled,
        staleTime: 10_000,
      },
      {
        queryKey: ["global-search", "im", debouncedQuery],
        queryFn: async () => {
          try {
            const { data } = await imApi.get("/documents", {
              params: { search: debouncedQuery },
            });
            return normalizeDocuments(toArray<Document>(data));
          } catch (err) {
            // Fallback: only on 400/422 (search param unsupported) — not on 500/network errors
            const status = (err as { response?: { status?: number } })?.response?.status;
            if (status !== 400 && status !== 422) throw err;

            const { data } = await imApi.get("/documents", {
              params: { limit: 200 },
            });
            const docs = toArray<Document>(data);
            const q = debouncedQuery.toLowerCase();
            const filtered = docs.filter(
              (d) =>
                d.company_name?.toLowerCase().includes(q) ||
                (d.project_name?.toLowerCase().includes(q) ?? false),
            );
            return normalizeDocuments(filtered);
          }
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

  const MODULE_NAMES: SearchModule[] = ["fdd", "kiis", "im"];
  const failedModules: SearchModule[] = enabled
    ? queryResults
        .map((r, i) => (r.isError ? MODULE_NAMES[i] : null))
        .filter((m): m is SearchModule => m !== null)
    : [];

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
    failedModules,
    recentSearches,
    addRecentSearch,
    clearRecentSearches,
  };
}
