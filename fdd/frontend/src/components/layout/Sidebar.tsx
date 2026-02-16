import { useLocation, useParams } from "react-router-dom";
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
} from "lucide-react";
import { cn } from "@/lib/cn";
import { useAuth } from "@/hooks/useAuth";
import { SidebarNavItem, SidebarSection } from "./SidebarNavItem";
import { Badge } from "@/components/ui";

const MAIN_NAV = [
  { to: "/deals", label: "Deals", icon: Briefcase },
];

const WORKFLOW_NAV = [
  { to: "", label: "Overview", icon: Eye, end: true },
];

const SETUP_NAV = [
  { to: "setup", label: "Deal Setup", icon: Settings },
  { to: "vdr", label: "VDR", icon: FolderOpen },
  { to: "uploads", label: "Uploads", icon: Upload },
];

const ANALYSIS_NAV = [
  { to: "definitions", label: "Definitions", icon: FileText },
  { to: "mapping", label: "Mapping", icon: GitMerge },
  { to: "qoe", label: "QoE Bridge", icon: TrendingUp },
  { to: "nwc", label: "Net Working Capital", icon: Wallet },
  { to: "netdebt", label: "Net Debt", icon: Landmark },
  { to: "issues", label: "Issues", icon: AlertTriangle },
];

const REPORT_NAV = [
  { to: "report", label: "Report", icon: FileOutput },
];

export interface SidebarProps {
  className?: string;
  onNavItemClick?: () => void;
}

export function Sidebar({ className, onNavItemClick }: SidebarProps) {
  const location = useLocation();
  const { dealId } = useParams<{ dealId: string }>();
  const { user, logout } = useAuth();

  const isInDealWorkspace = location.pathname.startsWith("/deals/") && dealId;

  return (
    <aside
      className={cn(
        "w-64 bg-amic min-h-screen flex flex-col",
        className
      )}
      role="navigation"
      aria-label="Main navigation"
    >
      {/* Logo */}
      <div className="px-5 py-6 border-b border-white/10">
        <div className="text-white font-heading font-bold text-lg">
          AMIC 법무법인 아믹
        </div>
        <div className="text-white/60 text-sm mt-1">Auto FDD</div>
      </div>

      {/* Main Navigation */}
      <div className="flex-1 overflow-y-auto py-4 px-3">
        <nav className="space-y-1" aria-label="Primary navigation">
          {MAIN_NAV.map((item) => (
            <SidebarNavItem
              key={item.to}
              to={item.to}
              label={item.label}
              icon={item.icon}
              onClick={onNavItemClick}
            />
          ))}
        </nav>

        {/* Deal Workspace Navigation */}
        {isInDealWorkspace && (
          <>
            <SidebarSection title="Workflow">
              {WORKFLOW_NAV.map((item) => (
                <SidebarNavItem
                  key={item.to}
                  to={`/deals/${dealId}/${item.to}`}
                  label={item.label}
                  icon={item.icon}
                  end={item.end}
                  onClick={onNavItemClick}
                />
              ))}
            </SidebarSection>
            <SidebarSection title="Setup">
              {SETUP_NAV.map((item) => (
                <SidebarNavItem
                  key={item.to}
                  to={`/deals/${dealId}/${item.to}`}
                  label={item.label}
                  icon={item.icon}
                  onClick={onNavItemClick}
                />
              ))}
            </SidebarSection>
            <SidebarSection title="Analysis">
              {ANALYSIS_NAV.map((item) => (
                <SidebarNavItem
                  key={item.to}
                  to={`/deals/${dealId}/${item.to}`}
                  label={item.label}
                  icon={item.icon}
                  onClick={onNavItemClick}
                />
              ))}
            </SidebarSection>
            <SidebarSection title="Report">
              {REPORT_NAV.map((item) => (
                <SidebarNavItem
                  key={item.to}
                  to={`/deals/${dealId}/${item.to}`}
                  label={item.label}
                  icon={item.icon}
                  onClick={onNavItemClick}
                />
              ))}
            </SidebarSection>
          </>
        )}
      </div>

      {/* User Info + Logout */}
      {user && (
        <div className="border-t border-white/10 px-4 py-4">
          <div className="flex items-center gap-3 mb-3">
            <div className="w-10 h-10 bg-white/20 rounded-full flex items-center justify-center">
              <span className="text-white font-medium text-sm">
                {user.display_name?.charAt(0).toUpperCase() || "U"}
              </span>
            </div>
            <div className="flex-1 min-w-0">
              <div className="text-white text-sm font-medium truncate">
                {user.display_name}
              </div>
              <Badge variant="neutral" className="mt-0.5 text-xs">
                {user.role}
              </Badge>
            </div>
          </div>
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
