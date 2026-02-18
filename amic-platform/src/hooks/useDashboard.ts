import { useQueries, useQuery } from "@tanstack/react-query";
import api from "@/api/client";
import { kiisApi } from "@/api/kiisClient";
import { imApi } from "@/api/imClient";
import { maApi } from "@/api/maClient";
import type { Deal } from "@/modules/fdd/types/deal";
import type { Document } from "@/modules/im/types/document";
import type { PortalKpis, PortalKpiErrors, ModuleHealth } from "@/types/dashboard";

/** Dashboard-specific short timeout to avoid blocking UI when a backend is down */
const DASH_TIMEOUT = 5_000;

export function usePortalKpis() {
  const results = useQueries({
    queries: [
      {
        queryKey: ["portal", "deals"],
        queryFn: async () => {
          const { data } = await api.get<Deal[]>("/deals", { timeout: DASH_TIMEOUT });
          return data;
        },
        staleTime: 30_000,
        retry: 0,
      },
      {
        queryKey: ["portal", "alerts-count"],
        queryFn: async () => {
          const { data } = await kiisApi.get<{ count: number }>(
            "/alerts/unread-count",
            { timeout: DASH_TIMEOUT },
          );
          return data;
        },
        staleTime: 30_000,
        retry: 0,
      },
      {
        queryKey: ["portal", "documents"],
        queryFn: async () => {
          const { data } = await imApi.get<{ items: Document[]; total: number }>(
            "/documents",
            { timeout: DASH_TIMEOUT },
          );
          return data;
        },
        staleTime: 30_000,
        retry: 0,
      },
      {
        queryKey: ["portal", "ma-transactions"],
        queryFn: async () => {
          const { data } = await maApi.get<{ items: unknown[]; total: number }>(
            "/transactions",
            { timeout: DASH_TIMEOUT, params: { status: "ACTIVE", limit: 100 } },
          );
          return data;
        },
        staleTime: 30_000,
        retry: 0,
      },
    ],
  });

  const [dealsQuery, alertsQuery, docsQuery, maQuery] = results;

  // Each query settles independently — "loading" only while ALL are still pending
  const isLoading = results.every((r) => r.isLoading);
  const isError = results.every((r) => r.isError);

  const IN_PROGRESS_STATUSES = [
    "PENDING",
    "COLLECTING",
    "ANALYZING",
    "GENERATING",
    "RENDERING",
  ];

  const kpis: PortalKpis = {
    activeDeals: dealsQuery.data
      ? dealsQuery.data.filter((d) => d.status === "ACTIVE").length
      : 0,
    watchlistAlerts: alertsQuery.data?.count ?? 0,
    imInProgress: docsQuery.data
      ? docsQuery.data.items.filter((d) =>
          IN_PROGRESS_STATUSES.includes(d.status),
        ).length
      : 0,
    pendingIssues: dealsQuery.data
      ? dealsQuery.data.filter((d) => d.status === "DRAFT").length
      : 0,
    activeMaDeals: maQuery.data?.total ?? 0,
  };

  const errors: PortalKpiErrors = {
    fdd: dealsQuery.isError,
    kiis: alertsQuery.isError,
    im: docsQuery.isError,
    ma: maQuery.isError,
  };

  const loading = {
    fdd: dealsQuery.isLoading,
    kiis: alertsQuery.isLoading,
    im: docsQuery.isLoading,
    ma: maQuery.isLoading,
  };

  return { kpis, isLoading, isError, errors, loading };
}

export function useModuleHealth() {
  return useQuery<ModuleHealth[]>({
    queryKey: ["portal", "health"],
    queryFn: async () => {
      const checks = [
        { module: "fdd" as const, label: "Auto FDD", fn: () => api.get("/health") },
        { module: "kiis" as const, label: "KIIS", fn: () => kiisApi.get("/health") },
        { module: "im" as const, label: "IM Generator", fn: () => imApi.get("/health") },
        { module: "ma" as const, label: "M&A Deals", fn: () => maApi.get("/health") },
      ];

      const results = await Promise.allSettled(
        checks.map((c) =>
          Promise.race([
            c.fn(),
            new Promise((_, reject) =>
              setTimeout(() => reject(new Error("timeout")), 3000),
            ),
          ]),
        ),
      );

      return checks.map((c, i) => ({
        module: c.module,
        label: c.label,
        healthy: results[i].status === "fulfilled",
      }));
    },
    staleTime: 60_000,
    refetchInterval: 60_000,
  });
}
