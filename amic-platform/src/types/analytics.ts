export type AnalyticsModule = "fdd" | "kiis" | "im" | "ma" | "docs";

export type AnalyticsTimeRange = "7d" | "30d" | "90d" | "1y" | "all";

export interface FddAnalytics {
  totalDeals: number;
  activeDeals: number;
  completedDeals: number;
  draftDeals: number;
  avgCycleDays: number;
  byPhase: Record<string, number>;
}

export interface KiisAnalytics {
  totalCompanies: number;
  totalFunds: number;
  totalReits: number;
  totalDeals: number;
  newsLast7Days: number;
}

export interface ImAnalytics {
  totalDocuments: number;
  inProgress: number;
  completed: number;
  failed: number;
  avgGenerationMinutes: number;
}

export interface PipelineFunnelPoint {
  phase: string;
  phaseLabel: string;
  count: number;
  totalValue: number | null;
}

export interface MaAnalytics {
  totalTransactions: number;
  activeTransactions: number;
  totalDealValue: number | null;
  recentActivityCount: number;
  byPhase: Record<string, number>;
  byStatus: Record<string, number>;
  bySide: Record<string, number>;
  pipelineFunnel: PipelineFunnelPoint[];
}

export interface DocsAnalytics {
  totalLegalDocs: number;
  totalMarketingDocs: number;
  totalLddReports: number;
  readyCount: number;
  generatingCount: number;
}

export interface AnalyticsKpis {
  fdd: FddAnalytics;
  kiis: KiisAnalytics;
  im: ImAnalytics;
  ma: MaAnalytics;
  docs: DocsAnalytics;
}

export interface TimeSeriesPoint {
  period: string;
  value: number;
  displayValue?: string;
}

export interface AnalyticsFilter {
  timeRange: AnalyticsTimeRange;
  module?: AnalyticsModule;
}
