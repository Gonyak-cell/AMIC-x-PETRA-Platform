import { useRef } from "react";
import { useNavigate } from "react-router-dom";
import type { LucideIcon } from "lucide-react";
import {
  Bell,
  FileText,
  Search,
  ArrowRight,
  Handshake,
  FileStack,
} from "lucide-react";
import { Navigate } from "react-router-dom";
import { useAuth } from "@/hooks/useAuth";
import { usePortalKpis, useModuleHealth, useAggregatedHealth } from "@/hooks/useDashboard";
import { useScrollReveal } from "@/hooks/useScrollReveal";
import { KpiCard, Card, KpiCardSkeleton, PageHero } from "@/components/ui";
import { cn } from "@/lib/cn";
import forestCoverUrl from "@/assets/images/forest-cover.jpg";


/* ── Module Card config (AMIC palette) ── */
const MODULE_CARDS = [
  {
    id: "ma",
    label: "M&A Deals",
    subtitle: "Transaction Pipeline",
    icon: Handshake,
    to: "/ma/transactions",
    bg: "bg-amic-800",
  },
  {
    id: "docs",
    label: "Deal Doc Studio",
    subtitle: "FDD, IM, TM & Legal Documents",
    icon: FileStack,
    to: "/docs",
    bg: "bg-amic",
  },
  {
    id: "kiis",
    label: "KIIS",
    subtitle: "Korea Investment Intelligence",
    icon: Search,
    to: "/kiis",
    bg: "bg-[#1C8F57]",
  },
] as const;

/* ── Module Status icon/color per aggregated module ── */
const STATUS_ICON_STYLES: Record<
  string,
  { icon: LucideIcon; bg: string; color: string }
> = {
  ma: { icon: Handshake, bg: "bg-amic-100", color: "text-amic-600" },
  docs: { icon: FileStack, bg: "bg-amic-50", color: "text-[#1C8F57]" },
  kiis: { icon: Search, bg: "bg-[#E8F8ED]", color: "text-accent" },
};

const QUICK_ACTIONS = [
  {
    label: "New Transaction",
    to: "/ma/transactions/new",
    icon: Handshake,
    description: "Start a new M&A transaction",
  },
  {
    label: "New Document",
    to: "/docs/new",
    icon: FileText,
    description: "Generate FDD, IM, or TM document",
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
  const { user, isClient } = useAuth();
  const { data: health } = useModuleHealth();
  const { data: aggregatedHealth } = useAggregatedHealth();
  const { kpis, errors, loading } = usePortalKpis(health);

  const quickActionsRef = useRef<HTMLDivElement>(null);
  const modulesRef = useRef<HTMLDivElement>(null);

  useScrollReveal(quickActionsRef, { stagger: 0.06 });
  useScrollReveal(modulesRef, { stagger: 0.08 });

  // CLIENT 역할은 MA Pipeline으로 리다이렉트
  if (isClient) return <Navigate to="/ma/transactions" replace />;

  const today = new Date().toLocaleDateString("ko-KR", {
    year: "numeric",
    month: "long",
    day: "numeric",
    weekday: "long",
  });

  return (
    <div className="space-y-6">
      {/* Dark Hero Section with Forest Cover */}
      <PageHero
        title={`Welcome, ${user?.display_name ?? "User"}${user?.title ? ` ${user.title.split("/")[0].trim()}` : ""} 님`}
        subtitle={today}
        backgroundImage={forestCoverUrl}
        backgroundOpacity={0.4}
      >
        {/* Glass Card KPIs — each card renders independently */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mt-8">
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
        </div>
      </PageHero>

      {/* Quick Actions (hover-glow-green) */}
      <div>
        <h2 className="label-uppercase mb-3">Quick Actions</h2>
        <div ref={quickActionsRef} className="grid grid-cols-1 sm:grid-cols-3 gap-4">
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

      {/* Module Status */}
      <div>
        <h2 className="label-uppercase mb-3">Module Status</h2>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          {aggregatedHealth ? (
            aggregatedHealth.map((mod) => {
              const statusColor = mod.overallHealthy
                ? "bg-positive"
                : mod.services.some((s) => s.healthy)
                  ? "bg-caution"
                  : "bg-negative";
              const statusText = mod.overallHealthy
                ? "Connected"
                : mod.services.some((s) => s.healthy)
                  ? "Degraded"
                  : "Unreachable";
              const iconBg = STATUS_ICON_STYLES[mod.id]?.bg ?? "bg-gray-100";
              const iconColor = STATUS_ICON_STYLES[mod.id]?.color ?? "text-gray-600";
              const IconComp = STATUS_ICON_STYLES[mod.id]?.icon ?? Search;

              return (
                <Card key={mod.id} padding="sm">
                  <div className="flex items-center gap-3">
                    <div
                      className={cn(
                        "w-9 h-9 rounded-lg flex items-center justify-center shrink-0",
                        iconBg,
                      )}
                    >
                      <IconComp className={cn("w-4 h-4", iconColor)} />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="text-sm font-medium text-text-dark truncate">
                        {mod.label}
                      </div>
                      <div className="flex items-center gap-1.5 mt-0.5">
                        <span
                          className={cn("h-2 w-2 rounded-full shrink-0", statusColor)}
                          aria-label={statusText}
                        />
                        <span className="text-xs text-text-secondary">
                          {statusText}
                          <span className="text-text-muted ml-1">
                            ({mod.healthySummary})
                          </span>
                        </span>
                      </div>
                    </div>
                  </div>
                </Card>
              );
            })
          ) : (
            Array.from({ length: 3 }).map((_, i) => (
              <Card key={i} padding="sm">
                <div className="flex items-center gap-3">
                  <div className="w-9 h-9 rounded-lg bg-gray-100 animate-pulse" />
                  <div className="space-y-1.5 flex-1">
                    <div className="h-4 w-24 bg-gray-100 rounded animate-pulse" />
                    <div className="h-3 w-16 bg-gray-100 rounded animate-pulse" />
                  </div>
                </div>
              </Card>
            ))
          )}
        </div>
      </div>

      {/* Modules (Gradient Background Cards) */}
      <div>
        <h2 className="label-uppercase mb-3">Modules</h2>
        <div ref={modulesRef} className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          {MODULE_CARDS.map((mod) => (
            <div
              key={mod.id}
              role="button"
              tabIndex={0}
              className="cursor-pointer"
              onClick={() => navigate(mod.to)}
              onKeyDown={(e) => {
                if (e.key === "Enter" || e.key === " ") navigate(mod.to);
              }}
            >
              <Card className={cn("hover-glow", mod.bg)}>
                <div className="flex items-center gap-3">
                  <div className="w-12 h-12 rounded-lg bg-white/10 backdrop-blur-sm flex items-center justify-center">
                    <mod.icon className="w-6 h-6 text-white" />
                  </div>
                  <div>
                    <div className="font-semibold text-white">{mod.label}</div>
                    <p className="text-xs text-white/70">{mod.subtitle}</p>
                  </div>
                </div>
              </Card>
            </div>
          ))}
        </div>
      </div>

    </div>
  );
}
