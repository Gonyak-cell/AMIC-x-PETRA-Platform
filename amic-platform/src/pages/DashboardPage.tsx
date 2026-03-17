import { useRef } from "react";
import { useNavigate } from "react-router-dom";
import { Search, Handshake, FileStack } from "lucide-react";
import { Navigate } from "react-router-dom";
import { useAuth } from "@/hooks/useAuth";
import { useScrollReveal } from "@/hooks/useScrollReveal";
import { Card, PageHero } from "@/components/ui";
import { cn } from "@/lib/cn";
import forestCoverUrl from "@/assets/images/forest-cover.jpg";
import MyProjectsSection from "@/components/dashboard/MyProjectsSection";
import DashboardCalendarWidget from "@/components/dashboard/DashboardCalendarWidget";
import NewsFeedSection from "@/components/dashboard/NewsFeedSection";

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
  const newsFeedRef = useRef<HTMLDivElement>(null);

  useScrollReveal(modulesRef, { stagger: 0.08 });
  useScrollReveal(newsFeedRef);

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

      {/* ── Row 1: My Projects + Calendar — 하단선 동기화 ── */}
      <div className="grid grid-cols-1 lg:grid-cols-[minmax(0,1fr)_360px] gap-6">
        <MyProjectsSection />
        <DashboardCalendarWidget />
      </div>

      {/* ── Row 2: News Feed + Modules ── */}
      <div className="grid grid-cols-1 lg:grid-cols-[minmax(0,1fr)_360px] gap-6">
        <div ref={newsFeedRef}>
          <NewsFeedSection />
        </div>

        {/* Modules */}
        <div>
          <h2 className="label-uppercase mb-3">Modules</h2>
          <div ref={modulesRef} className="flex flex-col gap-3">
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
                    <div className="w-10 h-10 rounded-lg bg-white/10 backdrop-blur-sm flex items-center justify-center">
                      <mod.icon className="w-5 h-5 text-white" />
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
  );
}
