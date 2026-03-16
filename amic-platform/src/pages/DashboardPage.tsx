import { useRef } from "react";
import { useNavigate } from "react-router-dom";
import {
  FileText,
  Search,
  ArrowRight,
  Handshake,
  FileStack,
} from "lucide-react";
import { Navigate } from "react-router-dom";
import { useAuth } from "@/hooks/useAuth";
import { useScrollReveal } from "@/hooks/useScrollReveal";
import { Card, PageHero } from "@/components/ui";
import { cn } from "@/lib/cn";
import forestCoverUrl from "@/assets/images/forest-cover.jpg";
import MyProjectsSection from "@/components/dashboard/MyProjectsSection";
import DashboardCalendarWidget from "@/components/dashboard/DashboardCalendarWidget";

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
        compact
      />

      {/* ── 2-column body: main + right rail ── */}
      <div className="grid grid-cols-1 lg:grid-cols-[minmax(0,1fr)_360px] gap-6">
        {/* ── Left: Main content ── */}
        <div className="space-y-6">
          {/* MY PROJECTS */}
          <MyProjectsSection />

          {/* Quick Actions */}
          <div>
            <h2 className="label-uppercase mb-3">Quick Actions</h2>
            <div
              ref={quickActionsRef}
              className="grid grid-cols-1 sm:grid-cols-3 gap-4"
            >
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

          {/* Modules */}
          <div>
            <h2 className="label-uppercase mb-3">Modules</h2>
            <div
              ref={modulesRef}
              className="grid grid-cols-1 sm:grid-cols-3 gap-4"
            >
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
                        <div className="font-semibold text-white">
                          {mod.label}
                        </div>
                        <p className="text-xs text-white/70">{mod.subtitle}</p>
                      </div>
                    </div>
                  </Card>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* ── Right rail: Activity + Calendar ── */}
        <aside className="space-y-6">
          <DashboardCalendarWidget />
        </aside>
      </div>
    </div>
  );
}
