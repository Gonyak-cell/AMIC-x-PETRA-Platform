import { useQueries, useQuery } from "@tanstack/react-query";
import api from "@/api/client";
import { kiisApi } from "@/api/kiisClient";
import { imApi } from "@/api/imClient";
import { maApi } from "@/api/maClient";
import type {
  PortalKpis,
  PortalKpiErrors,
  ModuleHealth,
  AggregatedModuleHealth,
} from "@/types/dashboard";

/** Dashboard-specific short timeout to avoid blocking UI when a backend is down */
const DASH_TIMEOUT = 5_000;

export function usePortalKpis(health?: ModuleHealth[]) {
  const kiisUp = health?.find((m) => m.module === "kiis")?.healthy;
  const maUp = health?.find((m) => m.module === "ma")?.healthy;

  const results = useQueries({
    queries: [
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
        enabled: kiisUp === true,
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
        enabled: maUp === true,
      },
    ],
  });

  const [alertsQuery, maQuery] = results;

  const isLoading = results.every((r) => r.isLoading) || health === undefined;
  const isError = results.every((r) => r.isError);

  const kpis: PortalKpis = {
    watchlistAlerts: alertsQuery.data?.count ?? 0,
    activeMaDeals: maQuery.data?.total ?? 0,
  };

  const errors: PortalKpiErrors = {
    kiis: alertsQuery.isError || kiisUp === false,
    ma: maQuery.isError || maUp === false,
  };

  const loading = {
    kiis: alertsQuery.isLoading || health === undefined,
    ma: maQuery.isLoading || health === undefined,
  };

  return { kpis, isLoading, isError, errors, loading };
}

export function useModuleHealth() {
  return useQuery<ModuleHealth[]>({
    queryKey: ["portal", "health"],
    queryFn: async () => {
      const checks = [
        { module: "fdd" as const, label: "FDD Engine", fn: () => api.get("/health") },
        { module: "kiis" as const, label: "KIIS", fn: () => kiisApi.get("/health") },
        { module: "im" as const, label: "IM", fn: () => imApi.get("/health") },
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

function aggregateHealth(raw: ModuleHealth[]): AggregatedModuleHealth[] {
  const find = (mod: string) => raw.find((m) => m.module === mod);

  const fdd = find("fdd");
  const im = find("im");
  const kiis = find("kiis");
  const ma = find("ma");

  const countHealthy = (services: { healthy: boolean }[]) =>
    services.filter((s) => s.healthy).length;

  const docsServices = [
    { name: "FDD Engine", healthy: fdd?.healthy ?? false },
    { name: "IM Engine", healthy: im?.healthy ?? false },
  ];
  const maServices = [
    { name: "Deal Management", healthy: ma?.healthy ?? false },
  ];
  const kiisServices = [
    { name: "KIIS API", healthy: kiis?.healthy ?? false },
  ];

  return [
    {
      id: "ma",
      label: "M&A Deals",
      services: maServices,
      overallHealthy: ma?.healthy ?? false,
      healthySummary: `${countHealthy(maServices)}/${maServices.length}`,
    },
    {
      id: "docs",
      label: "Deal Doc Studio",
      services: docsServices,
      overallHealthy: docsServices.every((s) => s.healthy),
      healthySummary: `${countHealthy(docsServices)}/${docsServices.length}`,
    },
    {
      id: "kiis",
      label: "KIIS",
      services: kiisServices,
      overallHealthy: kiis?.healthy ?? false,
      healthySummary: `${countHealthy(kiisServices)}/${kiisServices.length}`,
    },
  ];
}

export function useAggregatedHealth() {
  const { data: health, ...rest } = useModuleHealth();
  const aggregated = health ? aggregateHealth(health) : undefined;
  return { data: aggregated, ...rest };
}
