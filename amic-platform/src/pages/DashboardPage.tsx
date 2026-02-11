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
  const { kpis, isLoading: kpisLoading } = usePortalKpis();
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
              value={String(kpis.activeDeals)}
              icon={Briefcase}
              variant="positive"
            />
            <KpiCard
              label="Watchlist Alerts"
              value={String(kpis.watchlistAlerts)}
              icon={Bell}
            />
            <KpiCard
              label="IM In Progress"
              value={String(kpis.imInProgress)}
              icon={FileText}
              variant="caution"
            />
            <KpiCard
              label="Draft Deals"
              value={String(kpis.pendingIssues)}
              icon={AlertTriangle}
              variant="negative"
            />
          </>
        )}
      </div>

      {/* Quick Actions */}
      <div>
        <h2 className="text-lg font-heading font-semibold text-text-dark mb-3">
          Quick Actions
        </h2>
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
              <Card className="hover:shadow-md transition-shadow">
                <div className="flex items-start gap-3">
                  <div className="p-2 bg-amic/10 rounded-lg">
                    <action.icon className="h-5 w-5 text-amic" />
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
        <h2 className="text-lg font-heading font-semibold text-text-dark mb-3">
          Module Status
        </h2>
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
        <h2 className="text-lg font-heading font-semibold text-text-dark mb-3">
          Modules
        </h2>
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
            <Card className="hover:shadow-md transition-shadow">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-blue-50 rounded-lg">
                  <Briefcase className="h-5 w-5 text-blue-600" />
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
            <Card className="hover:shadow-md transition-shadow">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-emerald-50 rounded-lg">
                  <Search className="h-5 w-5 text-emerald-600" />
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
            <Card className="hover:shadow-md transition-shadow">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-purple-50 rounded-lg">
                  <FileText className="h-5 w-5 text-purple-600" />
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
