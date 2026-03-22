import { useMemo } from "react";
import { useQueries } from "@tanstack/react-query";
import api from "@/api/client";
import { kiisApi } from "@/api/kiisClient";
import { imApi } from "@/api/imClient";
import { maApi } from "@/api/maClient";
import { toArray } from "@/api/safe-parse";
import type { Deal } from "@/modules/fdd/types/deal";
import type { Document } from "@/modules/im/types/document";
import type { DashboardSummary } from "@/modules/kiis/types/dashboard";
import type { ModuleHealth } from "@/types/dashboard";
import type {
  AnalyticsKpis,
  FddAnalytics,
  KiisAnalytics,
  ImAnalytics,
  MaAnalytics,
  DocsAnalytics,
  PipelineFunnelPoint,
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

interface MaDashboardStatsResponse {
  total_transactions: number;
  active_transactions: number;
  total_deal_value: number | null;
  by_phase: Array<{ phase: string; count: number; total_value: number | null }>;
  by_status: Record<string, number>;
  by_side: Record<string, number>;
  recent_activity_count: number;
}

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

const EMPTY_MA: MaAnalytics = {
  totalTransactions: 0,
  activeTransactions: 0,
  totalDealValue: null,
  recentActivityCount: 0,
  byPhase: {},
  byStatus: {},
  bySide: {},
  pipelineFunnel: [],
};

const EMPTY_DOCS: DocsAnalytics = {
  totalLegalDocs: 0,
  totalMarketingDocs: 0,
  totalLddReports: 0,
  readyCount: 0,
  generatingCount: 0,
};

const PHASE_ORDER = [
  "ENGAGEMENT",
  "PREPARATION",
  "MARKETING",
  "BIDDING",
  "MAIN_DUE_DILIGENCE",
  "NEGOTIATION",
  "CLOSING",
  "POST_CLOSING",
] as const;

const PHASE_LABELS: Record<string, string> = {
  ENGAGEMENT: "Engagement",
  PREPARATION: "Preparation",
  MARKETING: "Marketing",
  BIDDING: "Bidding",
  MAIN_DUE_DILIGENCE: "Main DD",
  NEGOTIATION: "Negotiation",
  CLOSING: "Closing",
  POST_CLOSING: "거래종결",
};

function buildPipelineFunnel(
  byPhase: Array<{ phase: string; count: number; total_value: number | null }>,
): PipelineFunnelPoint[] {
  const map = new Map(byPhase.map((p) => [p.phase, p]));
  return PHASE_ORDER.map((phase) => ({
    phase,
    phaseLabel: PHASE_LABELS[phase] ?? phase,
    count: map.get(phase)?.count ?? 0,
    totalValue: map.get(phase)?.total_value ?? null,
  }));
}

export interface AnalyticsKpiErrors {
  fdd: AnalyticsKpiErrorState | null;
  kiis: AnalyticsKpiErrorState | null;
  im: AnalyticsKpiErrorState | null;
  ma: AnalyticsKpiErrorState | null;
  docs: AnalyticsKpiErrorState | null;
}

function isModuleUp(health: ModuleHealth[] | undefined, mod: string): boolean {
  if (!health) return false;
  return health.find((m) => m.module === mod)?.healthy === true;
}

export type AnalyticsKpiErrorKind =
  | "unreachable"
  | "unauthorized"
  | "forbidden"
  | "unavailable";

export interface AnalyticsKpiErrorState {
  kind: AnalyticsKpiErrorKind;
  status?: number;
}

function getErrorStatus(error: unknown): number | undefined {
  if (!error || typeof error !== "object") return undefined;
  const response = (error as { response?: { status?: number } }).response;
  return typeof response?.status === "number" ? response.status : undefined;
}

function getErrorState(
  error: unknown,
  moduleHealthy: boolean,
): AnalyticsKpiErrorState | null {
  if (!moduleHealthy) {
    return { kind: "unreachable" };
  }
  if (!error) return null;

  const status = getErrorStatus(error);
  if (status === 401) {
    return { kind: "unauthorized", status };
  }
  if (status === 403) {
    return { kind: "forbidden", status };
  }
  if (status != null) {
    return { kind: "unavailable", status };
  }
  return { kind: "unreachable" };
}

export function useAnalyticsKpis(
  filter?: AnalyticsFilter,
  health?: ModuleHealth[],
) {
  const cutoff = filter ? getTimeRangeCutoff(filter.timeRange) : null;
  const moduleFilter = filter?.module;

  const results = useQueries({
    queries: [
      {
        queryKey: ["analytics", "fdd-deals"],
        queryFn: async () => {
          const { data } = await api.get("/deals");
          return toArray<Deal>(data);
        },
        staleTime: 60_000,
        enabled:
          (!moduleFilter || moduleFilter === "fdd") &&
          isModuleUp(health, "fdd"),
      },
      {
        queryKey: ["analytics", "kiis-summary"],
        queryFn: async () => {
          const { data } =
            await kiisApi.get<DashboardSummary>("/dashboard/summary");
          return data;
        },
        staleTime: 60_000,
        enabled:
          (!moduleFilter || moduleFilter === "kiis") &&
          isModuleUp(health, "kiis"),
      },
      {
        queryKey: ["analytics", "im-documents"],
        queryFn: async () => {
          const { data } = await imApi.get("/documents");
          return toArray<Document>(data);
        },
        staleTime: 60_000,
        retry: false,
        enabled:
          (!moduleFilter || moduleFilter === "im") && isModuleUp(health, "im"),
      },
      {
        queryKey: ["analytics", "ma-dashboard-stats"],
        queryFn: async () => {
          const { data } =
            await maApi.get<MaDashboardStatsResponse>("/dashboard/stats");
          return data;
        },
        staleTime: 60_000,
        enabled:
          (!moduleFilter || moduleFilter === "ma" || moduleFilter === "docs") &&
          isModuleUp(health, "ma"),
      },
      {
        queryKey: ["analytics", "docs-counts"],
        queryFn: async () => {
          const { data } = await maApi.get<{
            total_legal: number;
            total_marketing: number;
            total_ldd: number;
          }>("/dashboard/docs-stats");
          return {
            totalLegal: data.total_legal,
            totalMarketing: data.total_marketing,
            totalLdd: data.total_ldd,
          };
        },
        staleTime: 60_000,
        enabled:
          (!moduleFilter || moduleFilter === "docs") &&
          isModuleUp(health, "ma"),
      },
    ],
  });

  const [dealsQuery, kiisQuery, imDocsQuery, maQuery, docsCountsQuery] =
    results;
  const isLoading = results.some((r) => r.isLoading);
  const isError = results.some((r) => r.isError);

  const errors: AnalyticsKpiErrors = {
    fdd: getErrorState(dealsQuery.error, isModuleUp(health, "fdd")),
    kiis: getErrorState(kiisQuery.error, isModuleUp(health, "kiis")),
    im: getErrorState(imDocsQuery.error, isModuleUp(health, "im")),
    ma: getErrorState(maQuery.error, isModuleUp(health, "ma")),
    docs: getErrorState(docsCountsQuery.error, isModuleUp(health, "ma")),
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
        ? imDocsQuery.data
          ? computeImAnalytics(filterByDate(imDocsQuery.data, cutoff))
          : EMPTY_IM
        : EMPTY_IM;

    const maData = maQuery.data;
    const ma: MaAnalytics =
      !moduleFilter || moduleFilter === "ma"
        ? maData
          ? {
              totalTransactions: maData.total_transactions,
              activeTransactions: maData.active_transactions,
              totalDealValue: maData.total_deal_value,
              recentActivityCount: maData.recent_activity_count,
              byPhase: Object.fromEntries(
                maData.by_phase.map((p) => [p.phase, p.count]),
              ),
              byStatus: maData.by_status,
              bySide: maData.by_side,
              pipelineFunnel: buildPipelineFunnel(maData.by_phase),
            }
          : EMPTY_MA
        : EMPTY_MA;

    const docsData = docsCountsQuery.data;
    const docs: DocsAnalytics =
      !moduleFilter || moduleFilter === "docs"
        ? docsData
          ? {
              totalLegalDocs: docsData.totalLegal,
              totalMarketingDocs: docsData.totalMarketing,
              totalLddReports: docsData.totalLdd,
              readyCount:
                docsData.totalLegal +
                docsData.totalMarketing +
                docsData.totalLdd,
              generatingCount: 0,
            }
          : EMPTY_DOCS
        : EMPTY_DOCS;

    return { fdd, kiis, im, ma, docs };
  }, [
    dealsQuery.data,
    kiisQuery.data,
    imDocsQuery.data,
    maQuery.data,
    docsCountsQuery.data,
    cutoff,
    moduleFilter,
  ]);

  return { kpis, isLoading, isError, errors };
}

export function useAnalyticsTimeSeries(
  filter?: AnalyticsFilter,
  health?: ModuleHealth[],
) {
  const cutoff = filter ? getTimeRangeCutoff(filter.timeRange) : null;
  const moduleFilter = filter?.module;

  const results = useQueries({
    queries: [
      {
        queryKey: ["analytics", "fdd-deals"],
        queryFn: async () => {
          const { data } = await api.get("/deals");
          return toArray<Deal>(data);
        },
        staleTime: 60_000,
        enabled:
          (!moduleFilter || moduleFilter === "fdd") &&
          isModuleUp(health, "fdd"),
      },
      {
        queryKey: ["analytics", "im-documents"],
        queryFn: async () => {
          const { data } = await imApi.get("/documents");
          return toArray<Document>(data);
        },
        staleTime: 60_000,
        retry: false,
        enabled:
          (!moduleFilter || moduleFilter === "im") && isModuleUp(health, "im"),
      },
      {
        queryKey: ["analytics", "ma-transactions-all"],
        queryFn: async () => {
          // 백엔드 limit 최대 100이므로 페이지네이션으로 전체 수집
          const PAGE = 100;
          const first = await maApi.get<{
            items: Array<{ created_at: string }>;
            total: number;
          }>("/transactions", { params: { limit: PAGE, offset: 0 } });
          const all = [...(first.data.items ?? [])];
          const total = first.data.total ?? 0;
          // 추가 페이지가 필요하면 병렬 요청
          if (total > PAGE) {
            const pages = Math.ceil(total / PAGE) - 1;
            const rest = await Promise.all(
              Array.from({ length: Math.min(pages, 9) }, (_, i) =>
                maApi.get<{ items: Array<{ created_at: string }> }>(
                  "/transactions",
                  { params: { limit: PAGE, offset: (i + 1) * PAGE } },
                ),
              ),
            );
            for (const r of rest) all.push(...(r.data.items ?? []));
          }
          return all;
        },
        staleTime: 60_000,
        enabled:
          (!moduleFilter || moduleFilter === "ma") && isModuleUp(health, "ma"),
      },
    ],
  });

  const [dealsQuery, docsQuery, maTransQuery] = results;
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
    const filtered = filterByDate(docsQuery.data, cutoff);
    const byMonth = new Map<string, number>();
    for (const doc of filtered) {
      const month = doc.created_at.slice(0, 7);
      byMonth.set(month, (byMonth.get(month) ?? 0) + 1);
    }
    return Array.from(byMonth.entries())
      .sort(([a], [b]) => a.localeCompare(b))
      .map(([period, value]) => ({ period, value }));
  }, [docsQuery.data, cutoff]);

  const maTimeSeries = useMemo<TimeSeriesPoint[]>(() => {
    if (!maTransQuery.data) return [];
    const filtered = filterByDate(
      maTransQuery.data as Array<{ created_at: string }>,
      cutoff,
    );
    const byMonth = new Map<string, number>();
    for (const txn of filtered) {
      const month = txn.created_at.slice(0, 7);
      byMonth.set(month, (byMonth.get(month) ?? 0) + 1);
    }
    return Array.from(byMonth.entries())
      .sort(([a], [b]) => a.localeCompare(b))
      .map(([period, value]) => ({ period, value }));
  }, [maTransQuery.data, cutoff]);

  return { fddTimeSeries, imTimeSeries, maTimeSeries, isLoading, isError };
}
