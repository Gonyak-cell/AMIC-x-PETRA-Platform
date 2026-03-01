import { useLocation, useParams, useNavigate } from "react-router-dom";
import {
  Eye,
  Settings,
  FolderOpen,
  FileText,
  Upload,
  GitMerge,
  TrendingUp,
  Wallet,
  Landmark,
  AlertTriangle,
  FileOutput,
  LogOut,
  BarChart3,
  Building2,
  Building,
  PlusCircle,
  Home,
  Users,
  ClipboardCheck,
  ClipboardList,
  Activity,
  BarChart2,
  Calendar,
  Download,
  HelpCircle,
  Handshake,
  Search,
  Scale,
  BookOpen,
  SearchCheck,
  Gavel,
  FileSignature,
  CalendarClock,
  ListChecks,
  FolderLock,
  Megaphone,
  Archive,
  CheckCircle2,
  Shield,
  Calculator,
  FileStack,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { cn } from "@/lib/cn";
import { useAuth } from "@/hooks/useAuth";
import { useTransaction } from "@/modules/ma/hooks/useTransactions";
import { PHASE_CONFIG } from "@/modules/ma/constants";
import {
  SidebarNavItem,
  SidebarPhaseItem,
  SidebarSection,
} from "./SidebarNavItem";
import { SidebarModuleGroup } from "./SidebarModuleGroup";
import { Badge } from "@/components/ui";
import { SidebarFavorites } from "@/components/SidebarFavorites";
import { HealthIndicator } from "@/components/layout/HealthIndicator";
import { getMemberPhoto } from "@/lib/member-photos";
import amicPetraLogoUrl from "@/assets/logos/AMIC_n_PETRA_Main_Simple.svg";

// ── FDD Navigation ──

const FDD_WORKFLOW_NAV = [{ to: "", label: "Overview", icon: Eye, end: true }];

const FDD_SETUP_NAV = [
  { to: "setup", label: "Deal Setup", icon: Settings },
  { to: "vdr", label: "VDR", icon: FolderOpen },
  { to: "uploads", label: "Uploads", icon: Upload },
];

const FDD_ANALYSIS_NAV = [
  { to: "definitions", label: "Definitions", icon: FileText },
  { to: "mapping", label: "Mapping", icon: GitMerge },
  { to: "qoe", label: "QoE Bridge", icon: TrendingUp },
  { to: "nwc", label: "Net Working Capital", icon: Wallet },
  { to: "netdebt", label: "Net Debt", icon: Landmark },
  { to: "issues", label: "Issues", icon: AlertTriangle },
];

const FDD_REPORT_NAV = [{ to: "report", label: "Report", icon: FileOutput }];

// ── KIIS Navigation ──

const KIIS_RESEARCH = [
  { to: "/kiis/gp", label: "GP", icon: Wallet },
  { to: "/kiis/funds", label: "Fund", icon: Building2 },
  { to: "/kiis/reits", label: "REITs", icon: Building },
];

// ── M&A Navigation ──

const MA_PIPELINE_NAV = [
  { to: "/ma/transactions", label: "Pipeline", icon: Handshake, end: true },
  { to: "/ma/transactions/new", label: "New Transaction", icon: PlusCircle },
];

const MA_WORKFLOW_NAV = [
  { phase: "ENGAGEMENT", to: "engagement", label: "① 수임", icon: Handshake },
  {
    phase: "PREPARATION",
    to: "marketing-materials",
    label: "② 준비",
    icon: ClipboardList,
  },
  { phase: "MARKETING", to: "buyers", label: "③ 마케팅", icon: Megaphone },
  { phase: "BIDDING", to: "bids", label: "④ 입찰", icon: Search },
  { phase: "MOU_SIGNED", to: "contracts", label: "⑤ MOU", icon: FileText },
  {
    phase: "MAIN_DUE_DILIGENCE",
    to: "dd-checklist",
    label: "⑥ 본실사",
    icon: Search,
  },
  { phase: "NEGOTIATION", to: "contracts", label: "⑦ 협상", icon: Scale },
  { phase: "CLOSING", to: "closing", label: "⑧ Closing", icon: CheckCircle2 },
  { phase: "POST_CLOSING", to: "pmi", label: "⑨ Post-Close", icon: Archive },
] as const;

const MA_TOOLS_NAV = [
  { to: "vdr", label: "VDR", icon: FolderLock },
  { to: "timeline", label: "타임라인", icon: Activity },
  { to: "risks", label: "리스크", icon: AlertTriangle },
  { to: "compliance", label: "컴플라이언스", icon: Shield },
  { to: "notes-approvals", label: "노트/승인", icon: FileText },
];

// ── VDR Navigation ──

const VDR_NAV = [{ to: "/vdr", label: "VDR Overview", icon: FolderLock }];

// ── Docs (Deal Document Studio) Navigation ──

const DOCS_HOME_NAV = [{ to: "/docs", label: "Studio Home", icon: FileText }];

const DOCS_MARKETING_NAV = [
  { to: "/docs/marketing", label: "Overview", icon: FileText, end: true },
  { to: "/docs/new/teaser", label: "TM", icon: FileText },
  { to: "/docs/new/im", label: "IM", icon: BookOpen },
];

const DOCS_LEGAL_NAV = [
  { to: "/docs/legal", label: "Overview", icon: Scale, end: true },
  { to: "/docs/legal/mou", label: "MOU", icon: Handshake },
  { to: "/docs/legal/contracts", label: "Deal Contracts", icon: FileSignature },
];

const DOCS_DD_NAV: Array<{
  to: string;
  label: string;
  icon: LucideIcon;
  end?: boolean;
  comingSoon?: boolean;
}> = [
  { to: "/docs/dd", label: "Overview", icon: SearchCheck, end: true },
  { to: "/docs/dd/fdd", label: "FDD", icon: BarChart2 },
  { to: "/docs/dd/ldd", label: "LDD", icon: Gavel },
  { to: "/docs/dd/tdd", label: "TDD", icon: Calculator, comingSoon: true },
];

const DOCS_CHECKLIST_NAV = [
  {
    to: "/docs/checklists",
    label: "Overview",
    icon: ClipboardCheck,
    end: true,
  },
  {
    to: "/docs/checklists/closing",
    label: "Closing Checklist",
    icon: ListChecks,
  },
  {
    to: "/docs/checklists/timeline",
    label: "Deal Timeline",
    icon: CalendarClock,
  },
];

export interface SidebarProps {
  className?: string;
  onNavItemClick?: () => void;
}

export function Sidebar({ className, onNavItemClick }: SidebarProps) {
  const location = useLocation();
  const navigate = useNavigate();
  const { dealId } = useParams<{ dealId: string }>();
  const { user, logout, hasPermission, isClient } = useAuth();

  const isFdd = location.pathname.startsWith("/fdd");
  const isKiis = location.pathname.startsWith("/kiis");
  const isDocs =
    location.pathname.startsWith("/docs") ||
    location.pathname.startsWith("/im") ||
    isFdd;
  const isVdr = location.pathname.startsWith("/vdr");
  const isMa = location.pathname.startsWith("/ma");
  const isAdmin = location.pathname.startsWith("/admin");
  const isInDealWorkspace =
    isFdd && location.pathname.startsWith("/fdd/deals/") && dealId;

  // MA 워크스페이스 감지: /ma/transactions/:txnId (new 제외)
  const maTxnMatch = location.pathname.match(/^\/ma\/transactions\/([^/]+)/);
  const maTxnId = maTxnMatch?.[1];
  const isInMaWorkspace = isMa && !!maTxnId && maTxnId !== "new";

  // MA 현재 거래의 phase 정보 (React Query 캐시 공유)
  const { data: maTxn } = useTransaction(isInMaWorkspace ? maTxnId! : "");
  const currentPhase = maTxn?.phase;
  const currentPhaseIdx = PHASE_CONFIG.findIndex(
    (p) => p.phase === currentPhase,
  );

  return (
    <aside
      className={cn(
        "w-64 bg-gradient-to-b from-amic-800 via-amic to-amic-700 min-h-screen flex flex-col shadow-sidebar",
        className,
      )}
      role="navigation"
      aria-label="Main navigation"
    >
      {/* Logo */}
      <div className="relative bg-white px-4 pt-5 pb-4">
        <img
          src={amicPetraLogoUrl}
          alt="AMIC x PETRABRIDGE PARTNERS"
          className="h-10 w-auto mx-auto"
        />
      </div>
      {/* Gradient Divider */}
      <div className="h-px bg-gradient-to-r from-transparent via-white/10 to-transparent" />

      {/* Home Link + Portal Nav (hidden for CLIENT) */}
      {!isClient && (
        <div className="px-3 pt-3 pb-1 space-y-1">
          <SidebarNavItem
            to="/"
            label="Home"
            icon={Home}
            end
            onClick={onNavItemClick}
          />
          <SidebarNavItem
            to="/calendar"
            label="Calendar"
            icon={Calendar}
            onClick={onNavItemClick}
          />
          <SidebarNavItem
            to="/exports"
            label="Exports"
            icon={Download}
            onClick={onNavItemClick}
          />
          <SidebarNavItem
            to="/team"
            label="Team"
            icon={Users}
            onClick={onNavItemClick}
          />
        </div>
      )}

      {/* Module separator (hidden for CLIENT) */}
      {!isClient && (
        <div className="h-px mx-3 bg-gradient-to-r from-transparent via-white/10 to-transparent" />
      )}

      {/* Module Navigation — all modules rendered, each with collapsible group */}
      <div className="flex-1 overflow-y-auto py-2 px-3">
        {/* MODULES label */}
        {!isClient && (
          <h3 className="px-4 mb-2 mt-2 text-[10px] font-semibold text-white/30 uppercase tracking-[0.15em]">
            Modules
          </h3>
        )}

        {/* ── M&A Deals ── */}
        {(!isClient || isMa) && (
          <SidebarModuleGroup
            id="ma"
            label="M&A Deals"
            icon={Handshake}
            basePath="/ma/transactions"
            isActive={isMa}
            storageKey="module-ma"
            defaultOpen={isMa}
            onNavItemClick={onNavItemClick}
          >
            <nav className="space-y-1" aria-label="M&A navigation">
              {MA_PIPELINE_NAV.filter(
                (item) => !isClient || item.to !== "/ma/transactions/new",
              ).map((item) => (
                <SidebarNavItem
                  key={item.to}
                  to={item.to}
                  label={item.label}
                  icon={item.icon}
                  end={(item as { end?: boolean }).end}
                  onClick={onNavItemClick}
                />
              ))}
            </nav>

            {!isClient && (
              <>
                <SidebarSection
                  title="Workspace"
                  collapsible
                  defaultOpen
                  storageKey="ma-workspace"
                  className="mt-3"
                >
                  <SidebarNavItem
                    to={isInMaWorkspace ? `/ma/transactions/${maTxnId}/` : "#"}
                    label="Overview"
                    icon={Eye}
                    end
                    disabled={!isInMaWorkspace}
                    onClick={onNavItemClick}
                  />
                </SidebarSection>

                <SidebarSection
                  title="Workflow"
                  collapsible
                  defaultOpen
                  storageKey="ma-workflow"
                  className="mt-3"
                >
                  {MA_WORKFLOW_NAV.map((item) => {
                    const itemIdx = PHASE_CONFIG.findIndex(
                      (p) => p.phase === item.phase,
                    );
                    const status: "done" | "current" | "future" =
                      !isInMaWorkspace || currentPhaseIdx < 0
                        ? "future"
                        : itemIdx < currentPhaseIdx
                          ? "done"
                          : itemIdx === currentPhaseIdx
                            ? "current"
                            : "future";

                    return (
                      <SidebarPhaseItem
                        key={item.phase}
                        to={
                          isInMaWorkspace
                            ? `/ma/transactions/${maTxnId}/${item.to}?viewPhase=${item.phase}`
                            : "#"
                        }
                        label={item.label}
                        icon={item.icon}
                        status={!isInMaWorkspace ? "future" : status}
                        onClick={onNavItemClick}
                      />
                    );
                  })}
                </SidebarSection>

                <SidebarSection
                  title="Tools"
                  collapsible
                  defaultOpen
                  storageKey="ma-tools"
                  className="mt-3"
                >
                  {MA_TOOLS_NAV.map((item) => (
                    <SidebarNavItem
                      key={item.to}
                      to={
                        isInMaWorkspace
                          ? `/ma/transactions/${maTxnId}/${item.to}`
                          : "#"
                      }
                      label={item.label}
                      icon={item.icon}
                      disabled={!isInMaWorkspace}
                      onClick={onNavItemClick}
                    />
                  ))}
                </SidebarSection>
              </>
            )}
          </SidebarModuleGroup>
        )}

        {/* ── VDR ── */}
        {!isClient && (
          <SidebarModuleGroup
            id="vdr"
            label="VDR"
            icon={FolderLock}
            basePath="/vdr"
            isActive={isVdr}
            storageKey="module-vdr"
            defaultOpen={isVdr}
            onNavItemClick={onNavItemClick}
          >
            <nav className="space-y-1" aria-label="VDR navigation">
              {VDR_NAV.map((item) => (
                <SidebarNavItem
                  key={item.to}
                  to={item.to}
                  label={item.label}
                  icon={item.icon}
                  end
                  onClick={onNavItemClick}
                />
              ))}
            </nav>
          </SidebarModuleGroup>
        )}

        {/* ── Deal Doc Studio ── */}
        {!isClient && (
          <SidebarModuleGroup
            id="docs"
            label="Deal Doc Studio"
            icon={FileStack}
            basePath="/docs"
            isActive={isDocs}
            storageKey="module-docs"
            defaultOpen={isDocs}
            onNavItemClick={onNavItemClick}
          >
            <nav
              className="space-y-1"
              aria-label="Deal Document Studio navigation"
            >
              {DOCS_HOME_NAV.map((item) => (
                <SidebarNavItem
                  key={item.to}
                  to={item.to}
                  label={item.label}
                  icon={item.icon}
                  end
                  onClick={onNavItemClick}
                />
              ))}
            </nav>

            <SidebarSection
              title="Marketing"
              collapsible
              defaultOpen
              storageKey="docs-marketing"
              className="mt-3"
            >
              {DOCS_MARKETING_NAV.map((item) => (
                <SidebarNavItem
                  key={item.to}
                  to={item.to}
                  label={item.label}
                  icon={item.icon}
                  end={item.end}
                  onClick={onNavItemClick}
                />
              ))}
            </SidebarSection>

            <SidebarSection
              title="Legal"
              collapsible
              defaultOpen
              storageKey="docs-legal"
              className="mt-3"
            >
              {DOCS_LEGAL_NAV.map((item) => (
                <SidebarNavItem
                  key={item.to}
                  to={item.to}
                  label={item.label}
                  icon={item.icon}
                  end={item.end}
                  onClick={onNavItemClick}
                />
              ))}
            </SidebarSection>

            <SidebarSection
              title="Due Diligence"
              collapsible
              defaultOpen
              storageKey="docs-dd"
              className="mt-3"
            >
              {DOCS_DD_NAV.map((item) => (
                <SidebarNavItem
                  key={item.to}
                  to={item.to}
                  label={item.label}
                  icon={item.icon}
                  end={item.end}
                  comingSoon={item.comingSoon}
                  onClick={onNavItemClick}
                />
              ))}
            </SidebarSection>

            {isFdd && isInDealWorkspace && (
              <>
                <SidebarSection title="FDD Workflow" className="mt-3">
                  {FDD_WORKFLOW_NAV.map((item) => (
                    <SidebarNavItem
                      key={item.to}
                      to={`/fdd/deals/${dealId}/${item.to}`}
                      label={item.label}
                      icon={item.icon}
                      end={item.end}
                      onClick={onNavItemClick}
                    />
                  ))}
                </SidebarSection>
                <SidebarSection
                  title="Setup"
                  collapsible
                  defaultOpen
                  storageKey="fdd-setup"
                  className="mt-3"
                >
                  {FDD_SETUP_NAV.map((item) => (
                    <SidebarNavItem
                      key={item.to}
                      to={`/fdd/deals/${dealId}/${item.to}`}
                      label={item.label}
                      icon={item.icon}
                      onClick={onNavItemClick}
                    />
                  ))}
                </SidebarSection>
                <SidebarSection
                  title="Analysis"
                  collapsible
                  defaultOpen
                  storageKey="fdd-analysis"
                  className="mt-3"
                >
                  {FDD_ANALYSIS_NAV.map((item) => (
                    <SidebarNavItem
                      key={item.to}
                      to={`/fdd/deals/${dealId}/${item.to}`}
                      label={item.label}
                      icon={item.icon}
                      onClick={onNavItemClick}
                    />
                  ))}
                </SidebarSection>
                <SidebarSection
                  title="Report"
                  collapsible
                  defaultOpen
                  storageKey="fdd-report"
                  className="mt-3"
                >
                  {FDD_REPORT_NAV.map((item) => (
                    <SidebarNavItem
                      key={item.to}
                      to={`/fdd/deals/${dealId}/${item.to}`}
                      label={item.label}
                      icon={item.icon}
                      onClick={onNavItemClick}
                    />
                  ))}
                </SidebarSection>
              </>
            )}

            <SidebarSection
              title="Checklist & Timeline"
              collapsible
              defaultOpen
              storageKey="docs-checklist"
              className="mt-3"
            >
              {DOCS_CHECKLIST_NAV.map((item, idx) => (
                <SidebarNavItem
                  key={`${item.to}-${idx}`}
                  to={item.to}
                  label={item.label}
                  icon={item.icon}
                  end={item.end}
                  onClick={onNavItemClick}
                />
              ))}
            </SidebarSection>
          </SidebarModuleGroup>
        )}

        {/* ── KIIS ── */}
        {!isClient && (
          <SidebarModuleGroup
            id="kiis"
            label="KIIS"
            icon={BarChart3}
            basePath="/kiis"
            isActive={isKiis}
            storageKey="module-kiis"
            defaultOpen={isKiis}
            onNavItemClick={onNavItemClick}
          >
            <SidebarSection
              title="Research"
              collapsible
              defaultOpen
              storageKey="kiis-research"
              className="mt-3"
            >
              {KIIS_RESEARCH.map((item) => (
                <SidebarNavItem
                  key={item.to}
                  to={item.to}
                  label={item.label}
                  icon={item.icon}
                  onClick={onNavItemClick}
                />
              ))}
            </SidebarSection>
          </SidebarModuleGroup>
        )}

        {/* Favorites & Recent (hidden for CLIENT) */}
        {!isClient && <SidebarFavorites onNavItemClick={onNavItemClick} />}

        {/* Admin Navigation (hidden for CLIENT) */}
        {!isClient &&
          (isAdmin ||
            hasPermission("user:manage") ||
            hasPermission("audit:view")) && (
            <>
              <div className="h-px mx-1 my-2 bg-gradient-to-r from-transparent via-white/10 to-transparent" />
              <SidebarSection title="Admin">
                {hasPermission("user:manage") && (
                  <SidebarNavItem
                    to="/admin/users"
                    label="Users"
                    icon={Users}
                    onClick={onNavItemClick}
                  />
                )}
                {hasPermission("audit:view") && (
                  <SidebarNavItem
                    to="/admin/activity"
                    label="Activity Log"
                    icon={ClipboardList}
                    onClick={onNavItemClick}
                  />
                )}
                {hasPermission("audit:view") && (
                  <SidebarNavItem
                    to="/analytics"
                    label="Analytics"
                    icon={BarChart2}
                    onClick={onNavItemClick}
                  />
                )}
              </SidebarSection>
            </>
          )}

        {/* Help */}
        <div className="mt-2">
          <SidebarNavItem
            to="/help"
            label="Help"
            icon={HelpCircle}
            onClick={onNavItemClick}
          />
        </div>
      </div>

      {/* Health Status (admin only, hidden for CLIENT) */}
      {!isClient && <HealthIndicator />}

      {/* User Info + Logout */}
      {user && (
        <div className="border-t border-white/10 px-4 py-4">
          <button
            onClick={() => {
              navigate("/settings/profile");
              onNavItemClick?.();
            }}
            className="w-full flex items-center gap-3 mb-3 rounded-lg p-1 -m-1 hover:bg-white/5 transition-colors cursor-pointer"
            aria-label="Open profile settings"
          >
            {(() => {
              const photoUrl = getMemberPhoto(user.display_name ?? "");
              return photoUrl ? (
                <img
                  src={photoUrl}
                  alt={user.display_name ?? ""}
                  className="w-10 h-10 rounded-full object-cover ring-1 ring-accent/30 bg-amic-700"
                />
              ) : (
                <div className="w-10 h-10 bg-accent/25 rounded-full flex items-center justify-center ring-1 ring-accent/30">
                  <span className="text-white font-medium text-sm">
                    {user.display_name?.charAt(0).toUpperCase() || "U"}
                  </span>
                </div>
              );
            })()}
            <div className="flex-1 min-w-0 text-left">
              <div className="text-white text-sm font-medium truncate">
                {user.display_name}
              </div>
              <Badge variant="neutral" className="mt-0.5 text-xs">
                {user.role}
              </Badge>
            </div>
          </button>
          <button
            onClick={async () => {
              await logout();
              navigate("/login", { replace: true });
            }}
            className="w-full flex items-center gap-2 px-3 py-2 text-sm text-white/70 hover:text-white hover:bg-white/5 rounded-lg transition-colors"
          >
            <LogOut className="h-4 w-4" />
            <span>Sign Out</span>
          </button>
        </div>
      )}
    </aside>
  );
}
