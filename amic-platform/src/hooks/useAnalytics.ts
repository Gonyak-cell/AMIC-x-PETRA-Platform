import { useMemo } from "react";
import { useQueries } from "@tanstack/react-query";
import api from "@/api/client";
import { kiisApi } from "@/api/kiisClient";
import { imApi } from "@/api/imClient";
import type { Deal } from "@/modules/fdd/types/deal";
import type { Document } from "@/modules/im/types/document";
import type { DashboardSummary } from "@/modules/kiis/types/dashboard";
import type {
  AnalyticsKpis,
  FddAnalytics,
  KiisAnalytics,
  ImAnalytics,
  AnalyticsFilter,
  TimeSeriesPoint,
} from "@/types/analytics";

const IM_IN_PROGRESS_STATUSES = [
  "PENDING",
  "COLLECTING",
  "ANALYZING",
  "GENERATING",
  "RENDERING",
];

function computeFddAnalytics(deals: Deal[]): FddAnalytics {
  const active = deals.filter((d) => d.status === "ACTIVE");
  const completed = deals.filter((d) => d.status === "ARCHIVED");
  const draft = deals.filter((d) => d.status === "DRAFT");

  const byPhase: Record<string, number> = {};
  for (const deal of deals) {
    byPhase[deal.current_phase] = (byPhase[deal.current_phase] ?? 0) + 1;
  }

  // Average cycle time in days for completed deals
  let avgCycleDays = 0;
  if (completed.length > 0) {
    const totalDays = completed.reduce((sum, d) => {
      const created = new Date(d.created_at).getTime();
      const updated = new Date(d.updated_at).getTime();
      return sum + (updated - created) / (1000 * 60 * 60 * 24);
    }, 0);
    avgCycleDays = Math.round(totalDays / completed.length);
  }

  return {
    totalDeals: deals.length,
    activeDeals: active.length,
    completedDeals: completed.length,
    draftDeals: draft.length,
    avgCycleDays,
    byPhase,
  };
}

function computeImAnalytics(docs: Document[]): ImAnalytics {
  const inProgress = docs.filter((d) =>
    IM_IN_PROGRESS_STATUSES.includes(d.status),
  );
  const completed = docs.filter((d) => d.status === "COMPLETED");
  const failed = docs.filter((d) => d.status === "FAILED");

  let avgGenerationMinutes = 0;
  const docsWithTime = completed.filter((d) => d.completed_at);
  if (docsWithTime.length > 0) {
    const totalMinutes = docsWithTime.reduce((sum, d) => {
      const created = new Date(d.created_at).getTime();
      const done = new Date(d.completed_at!).getTime();
      return sum + (done - created) / (1000 * 60);
    }, 0);
    avgGenerationMinutes = Math.round(totalMinutes / docsWithTime.length);
  }

  return {
    totalDocuments: docs.length,
    inProgress: inProgress.length,
    completed: completed.length,
    failed: failed.length,
    avgGenerationMinutes,
  };
}

export function useAnalyticsKpis(_filter?: AnalyticsFilter) {
  void _filter;
  const results = useQueries({
    queries: [
      {
        queryKey: ["analytics", "fdd-deals"],
        queryFn: async () => {
          const { data } = await api.get<Deal[]>("/deals");
          return data;
        },
        staleTime: 60_000,
      },
      {
        queryKey: ["analytics", "kiis-summary"],
        queryFn: async () => {
          const { data } =
            await kiisApi.get<DashboardSummary>("/dashboard/summary");
          return data;
        },
        staleTime: 60_000,
      },
      {
        queryKey: ["analytics", "im-documents"],
        queryFn: async () => {
          const { data } = await imApi.get<{ items: Document[]; total: number }>(
            "/documents",
          );
          return data;
        },
        staleTime: 60_000,
      },
    ],
  });

  const [dealsQuery, kiisQuery, docsQuery] = results;
  const isLoading = results.some((r) => r.isLoading);
  const isError = results.every((r) => r.isError);

  const kpis = useMemo<AnalyticsKpis>(() => {
    const fdd: FddAnalytics = dealsQuery.data
      ? computeFddAnalytics(dealsQuery.data)
      : {
          totalDeals: 0,
          activeDeals: 0,
          completedDeals: 0,
          draftDeals: 0,
          avgCycleDays: 0,
          byPhase: {},
        };

    const kiis: KiisAnalytics = kiisQuery.data
      ? {
          totalCompanies: kiisQuery.data.total_companies,
          totalFunds: kiisQuery.data.total_funds,
          totalReits: kiisQuery.data.total_reits,
          totalDeals: kiisQuery.data.total_deals,
          newsLast7Days: kiisQuery.data.news_last_7days,
        }
      : {
          totalCompanies: 0,
          totalFunds: 0,
          totalReits: 0,
          totalDeals: 0,
          newsLast7Days: 0,
        };

    const im: ImAnalytics = docsQuery.data
      ? computeImAnalytics(docsQuery.data.items)
      : {
          totalDocuments: 0,
          inProgress: 0,
          completed: 0,
          failed: 0,
          avgGenerationMinutes: 0,
        };

    return { fdd, kiis, im };
  }, [dealsQuery.data, kiisQuery.data, docsQuery.data]);

  return { kpis, isLoading, isError };
}

export function useAnalyticsTimeSeries(_filter?: AnalyticsFilter) {
  void _filter;
  const results = useQueries({
    queries: [
      {
        queryKey: ["analytics", "fdd-deals-ts"],
        queryFn: async () => {
          const { data } = await api.get<Deal[]>("/deals");
          return data;
        },
        staleTime: 60_000,
      },
      {
        queryKey: ["analytics", "im-documents-ts"],
        queryFn: async () => {
          const { data } = await imApi.get<{ items: Document[]; total: number }>(
            "/documents",
          );
          return data.items;
        },
        staleTime: 60_000,
      },
    ],
  });

  const [dealsQuery, docsQuery] = results;
  const isLoading = results.some((r) => r.isLoading);

  const fddTimeSeries = useMemo<TimeSeriesPoint[]>(() => {
    if (!dealsQuery.data) return [];
    const byMonth = new Map<string, number>();
    for (const deal of dealsQuery.data) {
      const month = deal.created_at.slice(0, 7); // YYYY-MM
      byMonth.set(month, (byMonth.get(month) ?? 0) + 1);
    }
    return Array.from(byMonth.entries())
      .sort(([a], [b]) => a.localeCompare(b))
      .map(([period, value]) => ({ period, value }));
  }, [dealsQuery.data]);

  const imTimeSeries = useMemo<TimeSeriesPoint[]>(() => {
    if (!docsQuery.data) return [];
    const byMonth = new Map<string, number>();
    for (const doc of docsQuery.data) {
      const month = doc.created_at.slice(0, 7);
      byMonth.set(month, (byMonth.get(month) ?? 0) + 1);
    }
    return Array.from(byMonth.entries())
      .sort(([a], [b]) => a.localeCompare(b))
      .map(([period, value]) => ({ period, value }));
  }, [docsQuery.data]);

  return { fddTimeSeries, imTimeSeries, isLoading };
}
