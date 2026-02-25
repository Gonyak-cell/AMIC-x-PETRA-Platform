import { Search } from "lucide-react";
import { NotificationBell } from "@/components/notifications/NotificationBell";

interface DesktopHeaderProps {
  onSearchClick: () => void;
}

export function DesktopHeader({ onSearchClick }: DesktopHeaderProps) {
  return (
    <div className="hidden md:flex sticky top-0 z-30 items-center justify-end gap-3 max-w-7xl mx-auto px-6 pt-5 pb-4 bg-white/80 backdrop-blur-md border-b border-gray-border/50">
      {/* Search Trigger */}
      <button
        onClick={onSearchClick}
        className="flex items-center gap-2 w-80 lg:w-96 px-4 py-2 text-sm text-text-secondary bg-white border border-gray-border rounded-dr shadow-dr-sm hover:border-amic/30 hover:text-text-dark transition-colors"
        aria-label="Open search"
      >
        <Search className="h-4 w-4 flex-shrink-0" />
        <span className="flex-1 text-left">Search deals, companies, projects...</span>
        <kbd className="ml-auto px-1.5 py-0.5 text-[10px] bg-bg-cool border border-gray-border rounded flex-shrink-0">
          Ctrl+K
        </kbd>
      </button>

      {/* Notification Bell */}
      <NotificationBell />
    </div>
  );
}
