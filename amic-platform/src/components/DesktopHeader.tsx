import { useNavigate } from "react-router-dom";
import { Search, Handshake, FileText } from "lucide-react";
import { NotificationBell } from "@/components/notifications/NotificationBell";

const QUICK_ACTIONS = [
  { label: "New Transaction", to: "/ma/transactions/new", icon: Handshake },
  { label: "New Document", to: "/docs/new", icon: FileText },
  { label: "Search Company", to: "/kiis/companies", icon: Search },
] as const;

interface DesktopHeaderProps {
  onSearchClick: () => void;
}

export function DesktopHeader({ onSearchClick }: DesktopHeaderProps) {
  const navigate = useNavigate();

  return (
    <div className="hidden md:flex sticky top-0 z-30 items-center justify-end gap-3 max-w-7xl mx-auto px-6 pt-5 pb-4 bg-white/80 backdrop-blur-md border-b border-gray-border/50">
      {/* Search Trigger */}
      <button
        onClick={onSearchClick}
        className="flex items-center gap-2 w-80 lg:w-96 h-10 px-4 text-sm text-text-secondary bg-white border border-gray-border rounded-dr shadow-dr-sm hover:border-amic/30 hover:text-text-dark transition-colors"
        aria-label="Open search"
      >
        <Search className="h-4 w-4 flex-shrink-0" />
        <span className="flex-1 text-left">
          Search deals, companies, projects...
        </span>
        <kbd className="ml-auto px-1.5 py-0.5 text-[10px] bg-bg-cool border border-gray-border rounded flex-shrink-0">
          Ctrl+K
        </kbd>
      </button>

      {/* Quick Actions */}
      <div className="flex items-center gap-1">
        {QUICK_ACTIONS.map((action) => (
          <button
            key={action.to}
            onClick={() => navigate(action.to)}
            className="group relative flex items-center justify-center w-10 h-10 rounded-lg text-accent hover:bg-accent/10 hover:text-accent/80 transition-colors"
            title={action.label}
          >
            <action.icon className="w-6 h-6" strokeWidth={1.8} />
            {/* Tooltip */}
            <span className="absolute -bottom-8 left-1/2 -translate-x-1/2 whitespace-nowrap text-[11px] text-white bg-gray-800 rounded px-2 py-0.5 opacity-0 group-hover:opacity-100 pointer-events-none transition-opacity z-10">
              {action.label}
            </span>
          </button>
        ))}
      </div>

      {/* Divider */}
      <div className="w-px h-5 bg-gray-border" />

      {/* Notification Bell */}
      <NotificationBell />
    </div>
  );
}
