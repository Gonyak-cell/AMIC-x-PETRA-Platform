import { Search } from "lucide-react";
import { NotificationBell } from "@/components/notifications/NotificationBell";

interface DesktopHeaderProps {
  onSearchClick: () => void;
}

export function DesktopHeader({ onSearchClick }: DesktopHeaderProps) {
  return (
    <div className="hidden md:flex items-center justify-end gap-2 max-w-7xl mx-auto px-6 pt-4 pb-1">
      {/* Search Trigger */}
      <button
        onClick={onSearchClick}
        className="flex items-center gap-2 px-3 py-1.5 text-sm text-text-secondary bg-white border border-gray-border rounded-lg hover:border-amic/30 hover:text-text-dark transition-colors"
        aria-label="Open search"
      >
        <Search className="h-4 w-4" />
        <span>Search...</span>
        <kbd className="ml-2 px-1.5 py-0.5 text-[10px] bg-bg-cool border border-gray-border rounded">
          Ctrl+K
        </kbd>
      </button>

      {/* Notification Bell */}
      <NotificationBell />
    </div>
  );
}
