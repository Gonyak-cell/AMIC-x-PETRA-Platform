import { useNavigate } from "react-router-dom";
import {
  Briefcase,
  Bell,
  FileText,
  AlertTriangle,
  Plus,
  Search,
  ArrowRight,
  Handshake,
} from "lucide-react";
import { useAuth } from "@/hooks/useAuth";
import { usePortalKpis, useModuleHealth } from "@/hooks/useDashboard";
import { KpiCard, Card, KpiCardSkeleton, PageHero } from "@/components/ui";
import { cn } from "@/lib/cn";

const QUICK_ACTIONS = [
  {
    label: "New Transaction",
    to: "/ma/transactions/new",
    icon: Handshake,
    description: "Start a new M&A transaction",
  },
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
];

export default function DashboardPage() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const { kpis, errors, loading } = usePortalKpis();
  const { data: health } = useModuleHealth();

  const today = new Date().toLocaleDateString("ko-KR", {
    year: "numeric",
    month: "long",
    day: "numeric",
    weekday: "long",
  });

  return (
    <div className="space-y-6">
      {/* Dark Hero Section */}
      <PageHero
        title={`Welcome, ${user?.display_name ?? "User"}`}
        subtitle={today}
      >
        {/* Glass Card KPIs — each card renders independently */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4 mt-8">
          {loading.ma ? (
            <KpiCardSkeleton />
          ) : (
            <KpiCard
              label="Active M&A Deals"
              value={errors.ma ? "—" : String(kpis.activeMaDeals)}
              icon={Handshake}
              variant={errors.ma ? "negative" : "positive"}
              hoverLift
              generous
              className="glass-card"
            />
          )}
          {loading.fdd ? (
            <KpiCardSkeleton />
          ) : (
            <KpiCard
              label="Active FDD Deals"
              value={errors.fdd ? "—" : String(kpis.activeDeals)}
              icon={Briefcase}
              variant={errors.fdd ? "negative" : "positive"}
              hoverLift
              generous
              className="glass-card"
            />
          )}
          {loading.kiis ? (
            <KpiCardSkeleton />
          ) : (
            <KpiCard
              label="Watchlist Alerts"
              value={errors.kiis ? "—" : String(kpis.watchlistAlerts)}
              icon={Bell}
              variant={errors.kiis ? "negative" : "default"}
              hoverLift
              generous
              className="glass-card"
            />
          )}
          {loading.im ? (
            <KpiCardSkeleton />
          ) : (
            <KpiCard
              label="IM In Progress"
              value={errors.im ? "—" : String(kpis.imInProgress)}
              icon={FileText}
              variant={errors.im ? "negative" : "caution"}
              hoverLift
              generous
              className="glass-card"
            />
          )}
          {loading.fdd ? (
            <KpiCardSkeleton />
          ) : (
            <KpiCard
              label="Draft Deals"
              value={errors.fdd ? "—" : String(kpis.pendingIssues)}
              icon={AlertTriangle}
              variant="negative"
              hoverLift
              generous
              className="glass-card"
            />
          )}
        </div>
      </PageHero>

      {/* Quick Actions (hover-glow-green) */}
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
              <Card className="hover-glow-green">
                <div className="flex items-start gap-3">
                  <div className="w-10 h-10 rounded-lg bg-accent/10 flex items-center justify-center">
                    <action.icon className="w-5 h-5 text-accent" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="font-medium text-text-dark group-hover:text-accent transition-colors flex items-center gap-1">
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

      {/* Module Status (Slim Bar) */}
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
                  <span className="text-sm text-text-dark font-medium">{m.label}</span>
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

      {/* Modules (Gradient Background Cards) */}
      <div>
        <h2 className="label-uppercase mb-3">Modules</h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <div
            role="button"
            tabIndex={0}
            className="cursor-pointer"
            onClick={() => navigate("/ma/transactions")}
            onKeyDown={(e) => {
              if (e.key === "Enter" || e.key === " ") navigate("/ma/transactions");
            }}
          >
            <Card className="hover-glow bg-gradient-to-br from-amic-700 to-amic-900">
              <div className="flex items-center gap-3">
                <div className="w-12 h-12 rounded-lg bg-white/10 backdrop-blur-sm flex items-center justify-center">
                  <Handshake className="w-6 h-6 text-white" />
                </div>
                <div>
                  <div className="font-semibold text-white">M&A Deals</div>
                  <p className="text-xs text-white/70">
                    Transaction Pipeline
                  </p>
                </div>
              </div>
            </Card>
          </div>
          <div
            role="button"
            tabIndex={0}
            className="cursor-pointer"
            onClick={() => navigate("/fdd/deals")}
            onKeyDown={(e) => {
              if (e.key === "Enter" || e.key === " ") navigate("/fdd/deals");
            }}
          >
            <Card className="hover-glow bg-gradient-to-br from-amic to-amic-700">
              <div className="flex items-center gap-3">
                <div className="w-12 h-12 rounded-lg bg-white/10 backdrop-blur-sm flex items-center justify-center">
                  <Briefcase className="w-6 h-6 text-white" />
                </div>
                <div>
                  <div className="font-semibold text-white">Auto FDD</div>
                  <p className="text-xs text-white/70">
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
            <Card className="hover-glow bg-gradient-to-br from-accent to-accent-hover">
              <div className="flex items-center gap-3">
                <div className="w-12 h-12 rounded-lg bg-white/10 backdrop-blur-sm flex items-center justify-center">
                  <Search className="w-6 h-6 text-white" />
                </div>
                <div>
                  <div className="font-semibold text-white">KIIS</div>
                  <p className="text-xs text-white/70">
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
            <Card className="hover-glow bg-gradient-to-br from-amic-500 to-amic">
              <div className="flex items-center gap-3">
                <div className="w-12 h-12 rounded-lg bg-white/10 backdrop-blur-sm flex items-center justify-center">
                  <FileText className="w-6 h-6 text-white" />
                </div>
                <div>
                  <div className="font-semibold text-white">IM Generator</div>
                  <p className="text-xs text-white/70">
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
