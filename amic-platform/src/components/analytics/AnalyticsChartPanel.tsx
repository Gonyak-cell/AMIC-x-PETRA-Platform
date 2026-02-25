import { Card } from "@/components/ui";
import { TrendLineChart } from "@/components/charts/TrendLineChart";
import { FinancialBarChart } from "@/components/charts/FinancialBarChart";
import { CHART_COLORS, CATEGORY_COLORS } from "@/components/charts/chartColors";
import type { TrendDataPoint } from "@/components/charts/TrendLineChart";
import type { BarChartDataPoint } from "@/components/charts/FinancialBarChart";
import type { TimeSeriesPoint, PipelineFunnelPoint } from "@/types/analytics";
import type { SectorAggregation } from "@/modules/kiis/types/deal";
import type { YearlyTrend } from "@/modules/kiis/types/deal";

const FUNNEL_COLORS = [
  "#6366f1", // indigo
  "#8b5cf6", // violet
  "#a855f7", // purple
  "#d946ef", // fuchsia
  "#ec4899", // pink
  "#f43f5e", // rose
  "#ef4444", // red
];

interface AnalyticsChartPanelProps {
  fddTimeSeries: TimeSeriesPoint[];
  imTimeSeries: TimeSeriesPoint[];
  maTimeSeries: TimeSeriesPoint[];
  maPhaseData?: Record<string, number>;
  pipelineFunnel?: PipelineFunnelPoint[];
  sectorData: SectorAggregation[] | undefined;
  trendData: YearlyTrend[] | undefined;
  isLoading: boolean;
}

export function AnalyticsChartPanel({
  fddTimeSeries,
  imTimeSeries,
  maTimeSeries,
  maPhaseData,
  pipelineFunnel,
  sectorData,
  trendData,
  isLoading,
}: AnalyticsChartPanelProps) {
  if (isLoading) {
    return (
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {[0, 1, 2, 3, 4, 5].map((i) => (
          <Card key={i}>
            <div className="h-[300px] bg-gray-50 animate-pulse rounded" />
          </Card>
        ))}
      </div>
    );
  }

  // Transform FDD time series for TrendLineChart
  const fddTrendData: TrendDataPoint[] = fddTimeSeries.map((p) => ({
    period: p.period,
    value: p.value,
  }));

  // Transform IM time series for TrendLineChart
  const imTrendData: TrendDataPoint[] = imTimeSeries.map((p) => ({
    period: p.period,
    value: p.value,
  }));

  // Transform MA time series for TrendLineChart
  const maTrendData: TrendDataPoint[] = maTimeSeries.map((p) => ({
    period: p.period,
    value: p.value,
  }));

  // Transform MA phase distribution for FinancialBarChart
  const maPhaseBarData: BarChartDataPoint[] = maPhaseData
    ? Object.entries(maPhaseData).map(([name, value], i) => ({
        name,
        value,
        fill: CATEGORY_COLORS[i % CATEGORY_COLORS.length],
      }))
    : [];

  // Transform pipeline funnel for FinancialBarChart
  const funnelBarData: BarChartDataPoint[] = (pipelineFunnel ?? []).map(
    (p, i) => ({
      name: p.phaseLabel,
      value: p.count,
      fill: FUNNEL_COLORS[i % FUNNEL_COLORS.length],
    }),
  );

  // Transform sector data for FinancialBarChart
  const sectorBarData: BarChartDataPoint[] = (sectorData ?? [])
    .slice(0, 8)
    .map((s, i) => ({
      name: s.sector_name || s.sector,
      value: s.deal_count,
      fill: CATEGORY_COLORS[i % CATEGORY_COLORS.length],
    }));

  // Transform yearly trends for TrendLineChart
  const yearlyTrendData: TrendDataPoint[] = (trendData ?? []).map((t) => ({
    period: String(t.year),
    value: t.deal_count,
  }));

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      {/* Pipeline Funnel — full width */}
      {funnelBarData.length > 0 && (
        <Card variant="forest-lift" className="lg:col-span-2">
          <h4 className="label-uppercase mb-3">
            M&A Pipeline Funnel
          </h4>
          <FinancialBarChart
            data={funnelBarData}
            height={280}
            colorScheme="categorical"
            aria-label="M&A pipeline funnel by phase"
          />
        </Card>
      )}

      {/* MA Transaction Creation Trend */}
      <Card variant="forest-lift">
        <h4 className="label-uppercase mb-3">
          M&A Transactions Created (Monthly)
        </h4>
        {maTrendData.length > 0 ? (
          <TrendLineChart
            data={maTrendData}
            height={260}
            showArea
            lineColor={CHART_COLORS.primary}
            aria-label="M&A transactions created per month"
          />
        ) : (
          <div className="h-[260px] flex items-center justify-center text-sm text-text-secondary">
            No M&A transaction data available
          </div>
        )}
      </Card>

      {/* MA Phase Distribution */}
      <Card variant="forest-lift">
        <h4 className="label-uppercase mb-3">
          M&A Transactions by Phase
        </h4>
        {maPhaseBarData.length > 0 ? (
          <FinancialBarChart
            data={maPhaseBarData}
            height={260}
            colorScheme="categorical"
            aria-label="M&A transaction count by phase"
          />
        ) : (
          <div className="h-[260px] flex items-center justify-center text-sm text-text-secondary">
            No phase distribution data available
          </div>
        )}
      </Card>

      {/* FDD Creation Trend */}
      <Card variant="forest-lift">
        <h4 className="label-uppercase mb-3">
          FDD Created (Monthly)
        </h4>
        {fddTrendData.length > 0 ? (
          <TrendLineChart
            data={fddTrendData}
            height={260}
            showArea
            lineColor={CHART_COLORS.primary}
            aria-label="FDD deals created per month"
          />
        ) : (
          <div className="h-[260px] flex items-center justify-center text-sm text-text-secondary">
            No deal data available
          </div>
        )}
      </Card>

      {/* KIIS Deal Trends (Yearly) */}
      <Card variant="forest-lift">
        <h4 className="label-uppercase mb-3">
          KIIS Deal Trends (Yearly)
        </h4>
        {yearlyTrendData.length > 0 ? (
          <TrendLineChart
            data={yearlyTrendData}
            height={260}
            showDots
            lineColor={CHART_COLORS.positive}
            aria-label="KIIS deal trends by year"
          />
        ) : (
          <div className="h-[260px] flex items-center justify-center text-sm text-text-secondary">
            No trend data available
          </div>
        )}
      </Card>

      {/* KIIS Sector Distribution */}
      <Card variant="forest-lift">
        <h4 className="label-uppercase mb-3">
          KIIS Deals by Sector
        </h4>
        {sectorBarData.length > 0 ? (
          <FinancialBarChart
            data={sectorBarData}
            height={260}
            colorScheme="categorical"
            aria-label="Deal count by sector"
          />
        ) : (
          <div className="h-[260px] flex items-center justify-center text-sm text-text-secondary">
            No sector data available
          </div>
        )}
      </Card>

      {/* IM Document Generation Trend */}
      <Card variant="forest-lift">
        <h4 className="label-uppercase mb-3">
          IM Documents Generated (Monthly)
        </h4>
        {imTrendData.length > 0 ? (
          <TrendLineChart
            data={imTrendData}
            height={260}
            showArea
            lineColor={CHART_COLORS.caution}
            aria-label="IM documents generated per month"
          />
        ) : (
          <div className="h-[260px] flex items-center justify-center text-sm text-text-secondary">
            No document data available
          </div>
        )}
      </Card>
    </div>
  );
}
