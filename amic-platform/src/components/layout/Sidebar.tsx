import { useLocation, useParams, useNavigate } from "react-router-dom";
import {
  Briefcase,
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
  Newspaper,
  ShieldAlert,
  Star,
  PlusCircle,
  Layout,
  Home,
  Users,
  ClipboardList,
  Activity,
  UserSearch,
  GitCompare,
  ScrollText,
  BarChart2,
  Calendar,
  Download,
  HelpCircle,
} from "lucide-react";
import { cn } from "@/lib/cn";
import { useAuth } from "@/hooks/useAuth";
import { SidebarNavItem, SidebarSection } from "./SidebarNavItem";
import { ModuleSwitcher } from "./ModuleSwitcher";
import { Badge } from "@/components/ui";
import { SidebarFavorites } from "@/components/SidebarFavorites";

// ── FDD Navigation ──

const FDD_MAIN_NAV = [
  { to: "/fdd/deals", label: "Deals", icon: Briefcase },
];

const FDD_WORKFLOW_NAV = [
  { to: "", label: "Overview", icon: Eye, end: true },
];

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

const FDD_REPORT_NAV = [
  { to: "report", label: "Report", icon: FileOutput },
];

// ── KIIS Navigation ──

const KIIS_NAV = [
  { to: "/kiis", label: "Dashboard", icon: BarChart3 },
  { to: "/kiis/companies", label: "Companies", icon: Building2 },
  { to: "/kiis/funds", label: "Funds", icon: Wallet },
  { to: "/kiis/reits", label: "REITs", icon: Building },
  { to: "/kiis/news", label: "News & Sentiment", icon: Newspaper },
  { to: "/kiis/deals", label: "Deal Sourcing", icon: TrendingUp },
  { to: "/kiis/sanctions", label: "Sanctions", icon: ShieldAlert },
  { to: "/kiis/portfolio", label: "Portfolio", icon: Activity },
  { to: "/kiis/managers", label: "Managers", icon: UserSearch },
  { to: "/kiis/entities", label: "Entity Match", icon: GitCompare },
  { to: "/kiis/disclosures", label: "Disclosures", icon: ScrollText },
  { to: "/kiis/watchlist", label: "Watchlist", icon: Star },
];

// ── IM Navigation ──

const IM_NAV = [
  { to: "/im", label: "Projects", icon: FileText },
  { to: "/im/new", label: "New IM", icon: PlusCircle },
  { to: "/im/templates", label: "Templates", icon: Layout },
];

export interface SidebarProps {
  className?: string;
  onNavItemClick?: () => void;
}

export function Sidebar({ className, onNavItemClick }: SidebarProps) {
  const location = useLocation();
  const navigate = useNavigate();
  const { dealId } = useParams<{ dealId: string }>();
  const { user, logout, hasPermission } = useAuth();

  const isFdd = location.pathname.startsWith("/fdd");
  const isKiis = location.pathname.startsWith("/kiis");
  const isIm = location.pathname.startsWith("/im");
  const isAdmin = location.pathname.startsWith("/admin");
  const isInDealWorkspace =
    isFdd && location.pathname.startsWith("/fdd/deals/") && dealId;

  return (
    <aside
      className={cn("w-64 bg-amic min-h-screen flex flex-col", className)}
      role="navigation"
      aria-label="Main navigation"
    >
      {/* Logo */}
      <div className="px-5 py-6 border-b border-white/10">
        <div className="text-white font-heading font-bold text-lg">
          AMIC x PETRA Platform
        </div>
      </div>

      {/* Home Link + Portal Nav */}
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
      </div>

      {/* Module Switcher */}
      <div className="border-t border-white/10">
        <ModuleSwitcher />
      </div>

      {/* Module-Specific Navigation */}
      <div className="flex-1 overflow-y-auto py-2 px-3">
        {/* FDD Navigation */}
        {isFdd && (
          <>
            <nav className="space-y-1" aria-label="FDD navigation">
              {FDD_MAIN_NAV.map((item) => (
                <SidebarNavItem
                  key={item.to}
                  to={item.to}
                  label={item.label}
                  icon={item.icon}
                  onClick={onNavItemClick}
                />
              ))}
            </nav>

            {isInDealWorkspace && (
              <>
                <SidebarSection title="Workflow">
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
                <SidebarSection title="Setup">
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
                <SidebarSection title="Analysis">
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
                <SidebarSection title="Report">
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
          </>
        )}

        {/* KIIS Navigation */}
        {isKiis && (
          <nav className="space-y-1" aria-label="KIIS navigation">
            {KIIS_NAV.map((item) => (
              <SidebarNavItem
                key={item.to}
                to={item.to}
                label={item.label}
                icon={item.icon}
                onClick={onNavItemClick}
              />
            ))}
          </nav>
        )}

        {/* IM Navigation */}
        {isIm && (
          <nav className="space-y-1" aria-label="IM navigation">
            {IM_NAV.map((item) => (
              <SidebarNavItem
                key={item.to}
                to={item.to}
                label={item.label}
                icon={item.icon}
                onClick={onNavItemClick}
              />
            ))}
          </nav>
        )}

        {/* Favorites & Recent */}
        <SidebarFavorites onNavItemClick={onNavItemClick} />

        {/* Admin Navigation */}
        {(isAdmin || hasPermission("user:manage") || hasPermission("audit:view")) && (
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
            <div className="w-10 h-10 bg-white/20 rounded-full flex items-center justify-center">
              <span className="text-white font-medium text-sm">
                {user.display_name?.charAt(0).toUpperCase() || "U"}
              </span>
            </div>
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
            onClick={logout}
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
