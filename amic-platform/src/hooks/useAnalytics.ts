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
  AnalyticsTimeRange,
  TimeSeriesPoint,
} from "@/types/analytics";

const IM_IN_PROGRESS_STATUSES = [
  "PENDING",
  "COLLECTING",
  "ANALYZING",
  "GENERATING",
  "RENDERING",
];

function getTimeRangeCutoff(range: AnalyticsTimeRange): Date | null {
  const days: Record<AnalyticsTimeRange, number> = {
    "7d": 7,
    "30d": 30,
    "90d": 90,
    "1y": 365,
    all: 0,
  };
  const d = days[range];
  return d > 0 ? new Date(Date.now() - d * 86_400_000) : null;
}

function filterByDate<T extends { created_at: string }>(
  items: T[],
  cutoff: Date | null,
): T[] {
  if (!cutoff) return items;
  return items.filter((item) => new Date(item.created_at) >= cutoff);
}

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
      return sum + Math.max(0, updated - created) / (1000 * 60 * 60 * 24);
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

const EMPTY_FDD: FddAnalytics = {
  totalDeals: 0,
  activeDeals: 0,
  completedDeals: 0,
  draftDeals: 0,
  avgCycleDays: 0,
  byPhase: {},
};

const EMPTY_KIIS: KiisAnalytics = {
  totalCompanies: 0,
  totalFunds: 0,
  totalReits: 0,
  totalDeals: 0,
  newsLast7Days: 0,
};

const EMPTY_IM: ImAnalytics = {
  totalDocuments: 0,
  inProgress: 0,
  completed: 0,
  failed: 0,
  avgGenerationMinutes: 0,
};

export interface AnalyticsKpiErrors {
  fdd: boolean;
  kiis: boolean;
  im: boolean;
}

export function useAnalyticsKpis(filter?: AnalyticsFilter) {
  const cutoff = filter ? getTimeRangeCutoff(filter.timeRange) : null;
  const moduleFilter = filter?.module;

  const results = useQueries({
    queries: [
      {
        queryKey: ["analytics", "fdd-deals"],
        queryFn: async () => {
          const { data } = await api.get<Deal[]>("/deals");
          return data;
        },
        staleTime: 60_000,
        enabled: !moduleFilter || moduleFilter === "fdd",
      },
      {
        queryKey: ["analytics", "kiis-summary"],
        queryFn: async () => {
          const { data } =
            await kiisApi.get<DashboardSummary>("/dashboard/summary");
          return data;
        },
        staleTime: 60_000,
        enabled: !moduleFilter || moduleFilter === "kiis",
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
        enabled: !moduleFilter || moduleFilter === "im",
      },
    ],
  });

  const [dealsQuery, kiisQuery, docsQuery] = results;
  const isLoading = results.some((r) => r.isLoading);
  const isError = results.some((r) => r.isError);

  const errors: AnalyticsKpiErrors = {
    fdd: dealsQuery.isError,
    kiis: kiisQuery.isError,
    im: docsQuery.isError,
  };

  const kpis = useMemo<AnalyticsKpis>(() => {
    const fdd: FddAnalytics =
      !moduleFilter || moduleFilter === "fdd"
        ? dealsQuery.data
          ? computeFddAnalytics(filterByDate(dealsQuery.data, cutoff))
          : EMPTY_FDD
        : EMPTY_FDD;

    // KIIS summary is pre-aggregated; time range filter cannot be applied
    const kiisData = kiisQuery.data;
    const getCount = (label: string) =>
      kiisData?.counts?.find((c) => c.label === label)?.count ?? 0;
    const kiis: KiisAnalytics =
      !moduleFilter || moduleFilter === "kiis"
        ? kiisData
          ? {
              totalCompanies: getCount("기업"),
              totalFunds: getCount("펀드"),
              totalReits: getCount("리츠"),
              totalDeals: getCount("딜"),
              newsLast7Days: kiisData.recent_news_count,
            }
          : EMPTY_KIIS
        : EMPTY_KIIS;

    const im: ImAnalytics =
      !moduleFilter || moduleFilter === "im"
        ? docsQuery.data
          ? computeImAnalytics(filterByDate(docsQuery.data.items, cutoff))
          : EMPTY_IM
        : EMPTY_IM;

    return { fdd, kiis, im };
  }, [dealsQuery.data, kiisQuery.data, docsQuery.data, cutoff, moduleFilter]);

  return { kpis, isLoading, isError, errors };
}

export function useAnalyticsTimeSeries(filter?: AnalyticsFilter) {
  const cutoff = filter ? getTimeRangeCutoff(filter.timeRange) : null;
  const moduleFilter = filter?.module;

  const results = useQueries({
    queries: [
      {
        queryKey: ["analytics", "fdd-deals"],
        queryFn: async () => {
          const { data } = await api.get<Deal[]>("/deals");
          return data;
        },
        staleTime: 60_000,
        enabled: !moduleFilter || moduleFilter === "fdd",
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
        enabled: !moduleFilter || moduleFilter === "im",
      },
    ],
  });

  const [dealsQuery, docsQuery] = results;
  const isLoading = results.some((r) => r.isLoading);
  const isError = results.some((r) => r.isError);

  const fddTimeSeries = useMemo<TimeSeriesPoint[]>(() => {
    if (!dealsQuery.data) return [];
    const filtered = filterByDate(dealsQuery.data, cutoff);
    const byMonth = new Map<string, number>();
    for (const deal of filtered) {
      const month = deal.created_at.slice(0, 7); // YYYY-MM
      byMonth.set(month, (byMonth.get(month) ?? 0) + 1);
    }
    return Array.from(byMonth.entries())
      .sort(([a], [b]) => a.localeCompare(b))
      .map(([period, value]) => ({ period, value }));
  }, [dealsQuery.data, cutoff]);

  const imTimeSeries = useMemo<TimeSeriesPoint[]>(() => {
    if (!docsQuery.data) return [];
    const filtered = filterByDate(docsQuery.data.items, cutoff);
    const byMonth = new Map<string, number>();
    for (const doc of filtered) {
      const month = doc.created_at.slice(0, 7);
      byMonth.set(month, (byMonth.get(month) ?? 0) + 1);
    }
    return Array.from(byMonth.entries())
      .sort(([a], [b]) => a.localeCompare(b))
      .map(([period, value]) => ({ period, value }));
  }, [docsQuery.data, cutoff]);

  return { fddTimeSeries, imTimeSeries, isLoading, isError };
}
