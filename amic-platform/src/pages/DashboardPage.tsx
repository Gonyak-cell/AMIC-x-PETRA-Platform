import { useNavigate } from "react-router-dom";
import {
  Briefcase,
  Bell,
  FileText,
  AlertTriangle,
  Plus,
  Search,
  Star,
  ArrowRight,
} from "lucide-react";
import { useAuth } from "@/hooks/useAuth";
import { usePortalKpis, useModuleHealth } from "@/hooks/useDashboard";
import { KpiCard, Card, KpiCardSkeleton } from "@/components/ui";
import { cn } from "@/lib/cn";

const QUICK_ACTIONS = [
  {
    label: "New Deal",
    to: "/fdd/deals/new",
    icon: Plus,
    description: "Start a new FDD deal",
  },
  {
    label: "New IM",
    to: "/im/new",
    icon: FileText,
    description: "Generate Investment Memorandum",
  },
  {
    label: "Search Company",
    to: "/kiis/companies",
    icon: Search,
    description: "Look up company information",
  },
  {
    label: "Watchlist",
    to: "/kiis/watchlist",
    icon: Star,
    description: "View watchlist & alerts",
  },
];

export default function DashboardPage() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const { kpis, isLoading: kpisLoading, errors } = usePortalKpis();
  const { data: health } = useModuleHealth();

  const today = new Date().toLocaleDateString("ko-KR", {
    year: "numeric",
    month: "long",
    day: "numeric",
    weekday: "long",
  });

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div>
        <h1 className="text-2xl font-heading font-bold text-text-dark">
          Welcome, {user?.display_name ?? "User"}
        </h1>
        <p className="text-sm text-text-secondary mt-1">{today}</p>
      </div>

      {/* Cross-module KPI Row */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {kpisLoading ? (
          <>
            <KpiCardSkeleton />
            <KpiCardSkeleton />
            <KpiCardSkeleton />
            <KpiCardSkeleton />
          </>
        ) : (
          <>
            <KpiCard
              label="Active FDD Deals"
              value={errors.fdd ? "—" : String(kpis.activeDeals)}
              icon={Briefcase}
              variant={errors.fdd ? "negative" : "positive"}
              hoverLift
              generous
            />
            <KpiCard
              label="Watchlist Alerts"
              value={errors.kiis ? "—" : String(kpis.watchlistAlerts)}
              icon={Bell}
              variant={errors.kiis ? "negative" : "default"}
              hoverLift
              generous
            />
            <KpiCard
              label="IM In Progress"
              value={errors.im ? "—" : String(kpis.imInProgress)}
              icon={FileText}
              variant={errors.im ? "negative" : "caution"}
              hoverLift
              generous
            />
            <KpiCard
              label="Draft Deals"
              value={errors.fdd ? "—" : String(kpis.pendingIssues)}
              icon={AlertTriangle}
              variant="negative"
              hoverLift
              generous
            />
          </>
        )}
      </div>

      {/* Quick Actions */}
      <div>
        <h2 className="label-uppercase mb-3">Quick Actions</h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {QUICK_ACTIONS.map((action) => (
            <div
              key={action.to}
              role="button"
              tabIndex={0}
              className="cursor-pointer group"
              onClick={() => navigate(action.to)}
              onKeyDown={(e) => {
                if (e.key === "Enter" || e.key === " ") navigate(action.to);
              }}
            >
              <Card variant="forest-lift">
                <div className="flex items-start gap-3">
                  <div className="w-10 h-10 rounded-lg bg-amic-100 flex items-center justify-center">
                    <action.icon className="w-5 h-5 text-amic" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="font-medium text-text-dark group-hover:text-amic transition-colors flex items-center gap-1">
                      {action.label}
                      <ArrowRight className="h-3.5 w-3.5 opacity-0 group-hover:opacity-100 transition-opacity" />
                    </div>
                    <p className="text-xs text-text-secondary mt-0.5">
                      {action.description}
                    </p>
                  </div>
                </div>
              </Card>
            </div>
          ))}
        </div>
      </div>

      {/* Module Status */}
      <div>
        <h2 className="label-uppercase mb-3">Module Status</h2>
        <Card>
          <div className="flex flex-wrap gap-6">
            {health ? (
              health.map((m) => (
                <div key={m.module} className="flex items-center gap-2">
                  <span
                    className={cn(
                      "h-2.5 w-2.5 rounded-full",
                      m.healthy ? "bg-positive" : "bg-negative",
                    )}
                    aria-label={m.healthy ? "Connected" : "Disconnected"}
                  />
                  <span className="text-sm text-text-dark">{m.label}</span>
                  <span className="text-xs text-text-secondary">
                    {m.healthy ? "Connected" : "Unreachable"}
                  </span>
                </div>
              ))
            ) : (
              <div className="flex items-center gap-2">
                <span className="h-2.5 w-2.5 rounded-full bg-gray-300 animate-pulse" />
                <span className="text-sm text-text-secondary">
                  Checking module status...
                </span>
              </div>
            )}
          </div>
        </Card>
      </div>

      {/* Module Navigation Shortcuts */}
      <div>
        <h2 className="label-uppercase mb-3">Modules</h2>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div
            role="button"
            tabIndex={0}
            className="cursor-pointer"
            onClick={() => navigate("/fdd/deals")}
            onKeyDown={(e) => {
              if (e.key === "Enter" || e.key === " ") navigate("/fdd/deals");
            }}
          >
            <Card variant="forest-lift">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-lg bg-amic-100 flex items-center justify-center">
                  <Briefcase className="w-5 h-5 text-amic" />
                </div>
                <div>
                  <div className="font-medium text-text-dark">Auto FDD</div>
                  <p className="text-xs text-text-secondary">
                    Financial Due Diligence
                  </p>
                </div>
              </div>
            </Card>
          </div>
          <div
            role="button"
            tabIndex={0}
            className="cursor-pointer"
            onClick={() => navigate("/kiis")}
            onKeyDown={(e) => {
              if (e.key === "Enter" || e.key === " ") navigate("/kiis");
            }}
          >
            <Card variant="forest-lift">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-lg bg-accent-light flex items-center justify-center">
                  <Search className="w-5 h-5 text-accent" />
                </div>
                <div>
                  <div className="font-medium text-text-dark">KIIS</div>
                  <p className="text-xs text-text-secondary">
                    Korea Investment Intelligence
                  </p>
                </div>
              </div>
            </Card>
          </div>
          <div
            role="button"
            tabIndex={0}
            className="cursor-pointer"
            onClick={() => navigate("/im")}
            onKeyDown={(e) => {
              if (e.key === "Enter" || e.key === " ") navigate("/im");
            }}
          >
            <Card variant="forest-lift">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-lg bg-amic-100 flex items-center justify-center">
                  <FileText className="w-5 h-5 text-amic-500" />
                </div>
                <div>
                  <div className="font-medium text-text-dark">IM Generator</div>
                  <p className="text-xs text-text-secondary">
                    Investment Memorandum
                  </p>
                </div>
              </div>
            </Card>
          </div>
        </div>
      </div>
    </div>
  );
}
