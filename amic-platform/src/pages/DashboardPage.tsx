import { useRef } from "react";
import { useNavigate } from "react-router-dom";
import {
  Search,
  Handshake,
  FileStack,
  PlusCircle,
  FilePlus2,
  BarChart3,
  CalendarPlus,
} from "lucide-react";
import { Navigate } from "react-router-dom";
import { useAuth } from "@/hooks/useAuth";
import { useScrollReveal } from "@/hooks/useScrollReveal";
import { Card, PageHero } from "@/components/ui";
import { cn } from "@/lib/cn";
import forestCoverUrl from "@/assets/images/forest-cover.jpg";
import MyProjectsSection from "@/components/dashboard/MyProjectsSection";
import DashboardCalendarWidget from "@/components/dashboard/DashboardCalendarWidget";
import NewsFeedSection from "@/components/dashboard/NewsFeedSection";

/* ── Quick Action config ── */
const QUICK_ACTIONS = [
  {
    id: "new-deal",
    label: "새 딜 등록",
    icon: PlusCircle,
    to: "/ma/transactions",
    bg: "bg-amic-800",
  },
  {
    id: "new-doc",
    label: "문서 작성",
    icon: FilePlus2,
    to: "/docs",
    bg: "bg-amic",
  },
  {
    id: "fund-search",
    label: "펀드 검색",
    icon: BarChart3,
    to: "/kiis",
    bg: "bg-[#1C8F57]",
  },
  {
    id: "schedule",
    label: "일정 관리",
    icon: CalendarPlus,
    to: "/calendar",
    bg: "bg-accent",
  },
] as const;

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

export default function DashboardPage() {
  const navigate = useNavigate();
  const { user, isClient } = useAuth();

  const modulesRef = useRef<HTMLDivElement>(null);

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

      {/* ── Single 2-column grid — 우측 컬럼 하단선이 뉴스피드와 정렬 ── */}
      <div className="grid grid-cols-1 lg:grid-cols-[minmax(0,1fr)_360px] gap-6 items-stretch">
        {/* ── Left column: My Projects → News Feed ── */}
        <div className="space-y-6">
          <MyProjectsSection />
          <NewsFeedSection />
        </div>

        {/* ── Right column: Calendar → Quick Actions → Modules ── */}
        <div className="flex flex-col gap-4">
          <DashboardCalendarWidget />

          {/* Quick Actions */}
          <div>
            <h2 className="label-uppercase mb-1">Quick Actions</h2>
            <div className="grid grid-cols-2 gap-x-3 gap-y-1">
              {QUICK_ACTIONS.map((action) => (
                <button
                  key={action.id}
                  onClick={() => navigate(action.to)}
                  className="flex items-center gap-2.5 px-0.5 py-1 rounded-xl hover:bg-white/50 transition-colors text-left"
                >
                  <div
                    className={cn(
                      "w-8 h-8 rounded-lg flex items-center justify-center shrink-0",
                      action.bg,
                    )}
                  >
                    <action.icon className="w-4 h-4 text-white" />
                  </div>
                  <span className="text-xs font-medium text-text-dark">
                    {action.label}
                  </span>
                </button>
              ))}
            </div>
          </div>

          {/* Modules — flex-1로 남은 공간 채워 하단선 정렬 */}
          <div className="flex-1 flex flex-col">
            <h2 className="label-uppercase mb-1">Modules</h2>
            <div ref={modulesRef} className="flex flex-col gap-1 flex-1">
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
                  <Card padding="none" className={cn("hover-glow", mod.bg)}>
                    <div className="flex items-center gap-3 px-3 py-2.5">
                      <div className="w-9 h-9 rounded-lg bg-white/10 backdrop-blur-sm flex items-center justify-center">
                        <mod.icon className="w-[18px] h-[18px] text-white" />
                      </div>
                      <div>
                        <div className="font-semibold text-white text-sm">
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
      </div>
    </div>
  );
}
