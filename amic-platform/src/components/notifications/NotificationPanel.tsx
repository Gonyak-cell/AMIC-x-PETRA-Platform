import { useNavigate } from "react-router-dom";
import {
  Briefcase,
  FileText,
  Newspaper,
  Shield,
  CheckCheck,
} from "lucide-react";
import { cn } from "@/lib/cn";
import { useNotifications } from "@/hooks/useNotifications";
import { Badge } from "@/components/ui";
import type { NotificationModule } from "@/types/notification";

const MODULE_ICONS: Record<NotificationModule, typeof Briefcase> = {
  fdd: Briefcase,
  kiis: Newspaper,
  im: FileText,
  portal: Shield,
};

const MODULE_BADGE_VARIANTS: Record<NotificationModule, "info" | "success" | "warning" | "neutral"> = {
  fdd: "info",
  kiis: "success",
  im: "warning",
  portal: "neutral",
};

function formatRelativeTime(dateStr: string): string {
  const now = Date.now();
  const date = new Date(dateStr).getTime();
  const diff = now - date;
  const minutes = Math.floor(diff / 60_000);

  if (minutes < 1) return "Just now";
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

interface NotificationPanelProps {
  open: boolean;
  onClose: () => void;
}

export function NotificationPanel({ open, onClose }: NotificationPanelProps) {
  const navigate = useNavigate();
  const { notifications, markAsRead, markAllAsRead } = useNotifications();

  if (!open) return null;

  return (
    <div
      className="absolute right-0 top-full mt-2 w-80 bg-white rounded-xl border border-gray-border shadow-xl z-50"
      role="region"
      aria-label="Notifications"
    >
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-border">
        <h3 className="text-sm font-heading font-semibold text-text-dark">
          Notifications
        </h3>
        {notifications.length > 0 && (
          <button
            onClick={() => markAllAsRead()}
            className="flex items-center gap-1 text-xs text-text-secondary hover:text-amic transition-colors"
          >
            <CheckCheck className="h-3.5 w-3.5" />
            Mark all read
          </button>
        )}
      </div>

      {/* Notification List */}
      <div className="max-h-96 overflow-y-auto">
        {notifications.length === 0 ? (
          <div className="p-6 text-center text-sm text-text-secondary">
            No notifications yet
          </div>
        ) : (
          notifications.map((notification) => {
            const Icon = MODULE_ICONS[notification.module];
            return (
              <button
                key={notification.id}
                onClick={() => {
                  if (!notification.is_read) markAsRead(notification.id);
                  if (notification.link) {
                    navigate(notification.link);
                    onClose();
                  }
                }}
                className={cn(
                  "flex items-start gap-3 w-full px-4 py-3 text-left transition-colors border-b border-gray-border last:border-b-0",
                  notification.is_read
                    ? "bg-white hover:bg-bg-cool"
                    : "bg-blue-50/50 hover:bg-blue-50",
                )}
              >
                <div className="mt-0.5 flex-shrink-0">
                  <Icon className="h-4 w-4 text-text-secondary" />
                </div>
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2 mb-0.5">
                    <span className="text-sm font-medium text-text-dark truncate">
                      {notification.title}
                    </span>
                    {!notification.is_read && (
                      <span className="h-2 w-2 rounded-full bg-amic flex-shrink-0" />
                    )}
                  </div>
                  <p className="text-xs text-text-secondary line-clamp-2">
                    {notification.message}
                  </p>
                  <div className="flex items-center gap-2 mt-1">
                    <Badge variant={MODULE_BADGE_VARIANTS[notification.module]}>
                      {notification.module.toUpperCase()}
                    </Badge>
                    <span className="text-[10px] text-text-secondary">
                      {formatRelativeTime(notification.created_at)}
                    </span>
                  </div>
                </div>
              </button>
            );
          })
        )}
      </div>
    </div>
  );
}
