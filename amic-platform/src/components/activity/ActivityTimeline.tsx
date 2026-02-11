import { Briefcase, Building2, FileText, Shield } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { Badge } from "@/components/ui";
import type { BadgeVariant } from "@/components/ui";
import type { ActivityLogItem, ActivityModule } from "@/types/activity";

const MODULE_CONFIG: Record<
  ActivityModule,
  { icon: LucideIcon; color: string; badge: BadgeVariant }
> = {
  fdd: { icon: Briefcase, color: "bg-blue-500", badge: "info" },
  kiis: { icon: Building2, color: "bg-emerald-500", badge: "success" },
  im: { icon: FileText, color: "bg-amber-500", badge: "warning" },
  portal: { icon: Shield, color: "bg-gray-500", badge: "neutral" },
};

function formatRelativeTime(dateStr: string): string {
  const now = Date.now();
  const date = new Date(dateStr).getTime();
  const diff = now - date;
  const seconds = Math.floor(diff / 1000);
  const minutes = Math.floor(seconds / 60);
  const hours = Math.floor(minutes / 60);
  const days = Math.floor(hours / 24);

  if (seconds < 60) return "Just now";
  if (minutes < 60) return `${minutes}m ago`;
  if (hours < 24) return `${hours}h ago`;
  if (days < 7) return `${days}d ago`;
  return new Date(dateStr).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
  });
}

interface ActivityTimelineProps {
  items: ActivityLogItem[];
  compact?: boolean;
}

export function ActivityTimeline({ items, compact }: ActivityTimelineProps) {
  if (items.length === 0) {
    return (
      <div className="py-8 text-center text-text-secondary text-sm">
        No activity found
      </div>
    );
  }

  return (
    <div className="relative">
      {/* Vertical line */}
      <div className="absolute left-5 top-0 bottom-0 w-px bg-gray-border" />

      <ul className="space-y-0" role="list" aria-label="Activity timeline">
        {items.map((item) => {
          const config = MODULE_CONFIG[item.module];
          const Icon = config.icon;

          return (
            <li key={item.id} className="relative pl-12 pr-4 py-3">
              {/* Dot */}
              <div
                className={`absolute left-3 top-4 w-4 h-4 rounded-full ${config.color} flex items-center justify-center ring-4 ring-white`}
              >
                <Icon className="h-2.5 w-2.5 text-white" />
              </div>

              <div
                className={`flex items-start gap-3 ${compact ? "text-xs" : "text-sm"}`}
              >
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="font-medium text-text-dark">
                      {item.user_name}
                    </span>
                    <span className="text-text-secondary">
                      {item.description}
                    </span>
                  </div>
                  {item.entity_name && (
                    <div className="text-text-secondary mt-0.5 truncate">
                      {item.entity_type}: {item.entity_name}
                    </div>
                  )}
                </div>

                <div className="flex items-center gap-2 shrink-0">
                  <Badge variant={config.badge} className="text-xs uppercase">
                    {item.module}
                  </Badge>
                  <span className="text-text-secondary text-xs whitespace-nowrap">
                    {formatRelativeTime(item.created_at)}
                  </span>
                </div>
              </div>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
