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
  Handshake,
  DollarSign,
  Activity,
  Scale,
  Megaphone,
  FileSearch,
  Files,
} from "lucide-react";
import { KpiCard, KpiCardSkeleton } from "@/components/ui";
import type { AnalyticsKpis, AnalyticsModule } from "@/types/analytics";
import type { AnalyticsKpiErrors } from "@/hooks/useAnalytics";

interface ModuleKpiSectionProps {
  kpis: AnalyticsKpis;
  isLoading: boolean;
  selectedModule?: AnalyticsModule;
  errors?: AnalyticsKpiErrors;
}

export function ModuleKpiSection({
  kpis,
  isLoading,
  selectedModule,
  errors,
}: ModuleKpiSectionProps) {
  if (isLoading) {
    return (
      <div className="space-y-6">
        {[0, 1, 2, 3].map((i) => (
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

  const showMa = !selectedModule || selectedModule === "ma";
  const showDocs = !selectedModule || selectedModule === "docs";
  const showFdd = !selectedModule || selectedModule === "fdd";
  const showKiis = !selectedModule || selectedModule === "kiis";
  const showIm = !selectedModule || selectedModule === "im";

  return (
    <div className="space-y-6">
      {/* MA KPIs */}
      {showMa && (
        <div>
          <h3 className="label-uppercase mb-2">M&A</h3>
          {errors?.ma ? (
            <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">
              M&A backend is unreachable. Data may be unavailable.
            </div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              <KpiCard
                label="Total Transactions"
                value={String(kpis.ma.totalTransactions)}
                icon={Handshake}
                hoverLift
                generous
              />
              <KpiCard
                label="Active Deals"
                value={String(kpis.ma.activeTransactions)}
                icon={TrendingUp}
                variant="positive"
                hoverLift
                generous
              />
              <KpiCard
                label="Total Deal Value"
                value={
                  kpis.ma.totalDealValue != null
                    ? `₩${(kpis.ma.totalDealValue / 1_000_000_000).toFixed(1)}B`
                    : "N/A"
                }
                icon={DollarSign}
                variant="caution"
                hoverLift
                generous
              />
              <KpiCard
                label="Recent Activity (7d)"
                value={String(kpis.ma.recentActivityCount)}
                icon={Activity}
                hoverLift
                generous
              />
            </div>
          )}
        </div>
      )}

      {/* Docs KPIs */}
      {showDocs && (
        <div>
          <h3 className="label-uppercase mb-2">Docs</h3>
          {errors?.docs ? (
            <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">
              Docs data is unreachable. Data may be unavailable.
            </div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              <KpiCard
                label="Legal Documents"
                value={String(kpis.docs.totalLegalDocs)}
                icon={Scale}
                hoverLift
                generous
              />
              <KpiCard
                label="Marketing Materials"
                value={String(kpis.docs.totalMarketingDocs)}
                icon={Megaphone}
                variant="positive"
                hoverLift
                generous
              />
              <KpiCard
                label="LDD Reports"
                value={String(kpis.docs.totalLddReports)}
                icon={FileSearch}
                variant="caution"
                hoverLift
                generous
              />
              <KpiCard
                label="Total Documents"
                value={String(kpis.docs.readyCount)}
                icon={Files}
                hoverLift
                generous
              />
            </div>
          )}
        </div>
      )}

      {/* FDD KPIs */}
      {showFdd && (
        <div>
          <h3 className="label-uppercase mb-2">FDD</h3>
          {errors?.fdd ? (
            <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">
              FDD backend is unreachable. Data may be unavailable.
            </div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              <KpiCard
                label="Total Deals"
                value={String(kpis.fdd.totalDeals)}
                icon={Briefcase}
                hoverLift
                generous
              />
              <KpiCard
                label="Active Deals"
                value={String(kpis.fdd.activeDeals)}
                icon={TrendingUp}
                variant="positive"
                hoverLift
                generous
              />
              <KpiCard
                label="Avg Cycle (days)"
                value={String(kpis.fdd.avgCycleDays)}
                icon={Clock}
                variant="caution"
                hoverLift
                generous
              />
              <KpiCard
                label="Draft Deals"
                value={String(kpis.fdd.draftDeals)}
                icon={AlertTriangle}
                variant="negative"
                hoverLift
                generous
              />
            </div>
          )}
        </div>
      )}

      {/* KIIS KPIs */}
      {showKiis && (
        <div>
          <h3 className="label-uppercase mb-2">KIIS</h3>
          {errors?.kiis ? (
            <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">
              KIIS backend is unreachable. Data may be unavailable.
            </div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              <KpiCard
                label="Companies"
                value={String(kpis.kiis.totalCompanies)}
                icon={Building2}
                hoverLift
                generous
              />
              <KpiCard
                label="Funds"
                value={String(kpis.kiis.totalFunds)}
                icon={Wallet}
                variant="positive"
                hoverLift
                generous
              />
              <KpiCard
                label="REITs"
                value={String(kpis.kiis.totalReits)}
                icon={Building}
                hoverLift
                generous
              />
              <KpiCard
                label="News (7d)"
                value={String(kpis.kiis.newsLast7Days)}
                icon={Newspaper}
                variant="caution"
                hoverLift
                generous
              />
            </div>
          )}
        </div>
      )}

      {/* IM KPIs */}
      {showIm && (
        <div>
          <h3 className="label-uppercase mb-2">IM</h3>
          {errors?.im ? (
            <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">
              IM backend is unreachable. Data may be unavailable.
            </div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              <KpiCard
                label="Total Documents"
                value={String(kpis.im.totalDocuments)}
                icon={FileText}
                hoverLift
                generous
              />
              <KpiCard
                label="Completed"
                value={String(kpis.im.completed)}
                icon={CheckCircle}
                variant="positive"
                hoverLift
                generous
              />
              <KpiCard
                label="In Progress"
                value={String(kpis.im.inProgress)}
                icon={Clock}
                variant="caution"
                hoverLift
                generous
              />
              <KpiCard
                label="Failed"
                value={String(kpis.im.failed)}
                icon={XCircle}
                variant="negative"
                hoverLift
                generous
              />
            </div>
          )}
        </div>
      )}
    </div>
  );
}
