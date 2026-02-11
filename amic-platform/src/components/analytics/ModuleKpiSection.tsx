import {
  Briefcase,
  Building2,
  FileText,
  TrendingUp,
  Clock,
  AlertTriangle,
  Newspaper,
  Wallet,
  Building,
  CheckCircle,
  XCircle,
} from "lucide-react";
import { KpiCard, KpiCardSkeleton } from "@/components/ui";
import type { AnalyticsKpis } from "@/types/analytics";

interface ModuleKpiSectionProps {
  kpis: AnalyticsKpis;
  isLoading: boolean;
}

export function ModuleKpiSection({ kpis, isLoading }: ModuleKpiSectionProps) {
  if (isLoading) {
    return (
      <div className="space-y-6">
        {[0, 1, 2].map((i) => (
          <div
            key={i}
            className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4"
          >
            <KpiCardSkeleton />
            <KpiCardSkeleton />
            <KpiCardSkeleton />
            <KpiCardSkeleton />
          </div>
        ))}
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* FDD KPIs */}
      <div>
        <h3 className="text-sm font-medium text-text-secondary mb-2">
          Auto FDD
        </h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <KpiCard
            label="Total Deals"
            value={String(kpis.fdd.totalDeals)}
            icon={Briefcase}
          />
          <KpiCard
            label="Active Deals"
            value={String(kpis.fdd.activeDeals)}
            icon={TrendingUp}
            variant="positive"
          />
          <KpiCard
            label="Avg Cycle (days)"
            value={String(kpis.fdd.avgCycleDays)}
            icon={Clock}
            variant="caution"
          />
          <KpiCard
            label="Draft Deals"
            value={String(kpis.fdd.draftDeals)}
            icon={AlertTriangle}
            variant="negative"
          />
        </div>
      </div>

      {/* KIIS KPIs */}
      <div>
        <h3 className="text-sm font-medium text-text-secondary mb-2">KIIS</h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <KpiCard
            label="Companies"
            value={String(kpis.kiis.totalCompanies)}
            icon={Building2}
          />
          <KpiCard
            label="Funds"
            value={String(kpis.kiis.totalFunds)}
            icon={Wallet}
            variant="positive"
          />
          <KpiCard
            label="REITs"
            value={String(kpis.kiis.totalReits)}
            icon={Building}
          />
          <KpiCard
            label="News (7d)"
            value={String(kpis.kiis.newsLast7Days)}
            icon={Newspaper}
            variant="caution"
          />
        </div>
      </div>

      {/* IM KPIs */}
      <div>
        <h3 className="text-sm font-medium text-text-secondary mb-2">
          IM Generator
        </h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <KpiCard
            label="Total Documents"
            value={String(kpis.im.totalDocuments)}
            icon={FileText}
          />
          <KpiCard
            label="Completed"
            value={String(kpis.im.completed)}
            icon={CheckCircle}
            variant="positive"
          />
          <KpiCard
            label="In Progress"
            value={String(kpis.im.inProgress)}
            icon={Clock}
            variant="caution"
          />
          <KpiCard
            label="Failed"
            value={String(kpis.im.failed)}
            icon={XCircle}
            variant="negative"
          />
        </div>
      </div>
    </div>
  );
}
