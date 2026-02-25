import { useState } from "react";
import { Navigate } from "react-router-dom";
import { useAuth } from "@/hooks/useAuth";
import { useModuleHealth } from "@/hooks/useDashboard";
import { useAnalyticsKpis, useAnalyticsTimeSeries } from "@/hooks/useAnalytics";
import { useDealsBySector, useDealTrends } from "@/modules/kiis/hooks/useDeals";
import { AnalyticsFilterBar } from "@/components/analytics/AnalyticsFilterBar";
import { ModuleKpiSection } from "@/components/analytics/ModuleKpiSection";
import { AnalyticsChartPanel } from "@/components/analytics/AnalyticsChartPanel";
import { PageHero } from "@/components/ui";
import type { AnalyticsTimeRange, AnalyticsModule } from "@/types/analytics";
import heroImg from "@/assets/images/heroes/hero-arch-diamond.jpg";

export default function AnalyticsPage() {
  const { hasPermission } = useAuth();
  const [timeRange, setTimeRange] = useState<AnalyticsTimeRange>("30d");
  const [selectedModule, setSelectedModule] = useState<
    AnalyticsModule | "all"
  >("all");

  const { data: health } = useModuleHealth();
  const filter = { timeRange, module: selectedModule === "all" ? undefined : selectedModule };
  const { kpis, isLoading: kpisLoading, errors } = useAnalyticsKpis(filter, health);
  const { fddTimeSeries, imTimeSeries, maTimeSeries, isLoading: tsLoading } =
    useAnalyticsTimeSeries(filter, health);
  const { data: sectorData } = useDealsBySector();
  const { data: trendData } = useDealTrends();

  if (!hasPermission("audit:view")) {
    return <Navigate to="/" replace />;
  }

  return (
    <div className="space-y-6">
      {/* Hero Section */}
      <PageHero
        title="Cross-Module Analytics"
        subtitle="Aggregated KPIs and trends across M&A, FDD, KIIS, IM, and Docs modules"
        backgroundImage={heroImg}
        backgroundOpacity={0.18}
        compact
      />

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
          maTimeSeries={maTimeSeries}
          maPhaseData={kpis.ma.byPhase}
          pipelineFunnel={kpis.ma.pipelineFunnel}
          sectorData={sectorData}
          trendData={trendData}
          isLoading={tsLoading}
        />
      </div>
    </div>
  );
}
