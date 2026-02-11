import { useState } from "react";
import { Navigate } from "react-router-dom";
import { useAuth } from "@/hooks/useAuth";
import { useAnalyticsKpis, useAnalyticsTimeSeries } from "@/hooks/useAnalytics";
import { useDealsBySector, useDealTrends } from "@/modules/kiis/hooks/useDeals";
import { AnalyticsFilterBar } from "@/components/analytics/AnalyticsFilterBar";
import { ModuleKpiSection } from "@/components/analytics/ModuleKpiSection";
import { AnalyticsChartPanel } from "@/components/analytics/AnalyticsChartPanel";
import type { AnalyticsTimeRange, AnalyticsModule } from "@/types/analytics";

export default function AnalyticsPage() {
  const { hasPermission } = useAuth();
  const [timeRange, setTimeRange] = useState<AnalyticsTimeRange>("30d");
  const [selectedModule, setSelectedModule] = useState<
    AnalyticsModule | "all"
  >("all");

  const filter = { timeRange, module: selectedModule === "all" ? undefined : selectedModule };
  const { kpis, isLoading: kpisLoading, errors } = useAnalyticsKpis(filter);
  const { fddTimeSeries, imTimeSeries, isLoading: tsLoading } =
    useAnalyticsTimeSeries(filter);
  const { data: sectorData } = useDealsBySector();
  const { data: trendData } = useDealTrends();

  if (!hasPermission("audit:view")) {
    return <Navigate to="/" replace />;
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-heading font-bold text-text-dark">
          Cross-Module Analytics
        </h1>
        <p className="text-sm text-text-secondary mt-1">
          Aggregated KPIs and trends across FDD, KIIS, and IM modules
        </p>
      </div>

      {/* Filters */}
      <AnalyticsFilterBar
        timeRange={timeRange}
        selectedModule={selectedModule}
        onTimeRangeChange={setTimeRange}
        onModuleChange={setSelectedModule}
      />

      {/* KPI Cards */}
      <ModuleKpiSection
        kpis={kpis}
        isLoading={kpisLoading}
        selectedModule={selectedModule === "all" ? undefined : selectedModule}
        errors={errors}
      />

      {/* Charts */}
      <div>
        <h2 className="label-uppercase mb-3">Trends & Distributions</h2>
        <AnalyticsChartPanel
          fddTimeSeries={fddTimeSeries}
          imTimeSeries={imTimeSeries}
          sectorData={sectorData}
          trendData={trendData}
          isLoading={tsLoading}
        />
      </div>
    </div>
  );
}
