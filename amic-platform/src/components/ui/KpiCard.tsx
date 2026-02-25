import type { LucideIcon } from "lucide-react";
import { TrendingUp, TrendingDown, Minus } from "lucide-react";
import { cn } from "@/lib/cn";

export interface KpiCardProps {
  /** KPI name — accepts either `label` or `title` */
  label?: string;
  title?: string;
  value: string;
  trend?: "up" | "down" | "flat";
  trendValue?: string;
  variant?: "default" | "positive" | "negative" | "caution" | "danger" | "good" | "bad" | "warning";
  subtitle?: string;
  icon?: LucideIcon;
  hoverLift?: boolean;
  generous?: boolean;
  className?: string;
}

const variantStyles = {
  default: "border-gray-border border-t-2 border-t-amic/10",
  positive: "border-positive/30 bg-light-green/40",
  negative: "border-negative/30 bg-red-50/30",
  caution: "border-caution/30 bg-amber-50/30",
  // 별칭
  danger: "border-negative/30 bg-red-50/30",
  good: "border-positive/30 bg-light-green/40",
  bad: "border-negative/30 bg-red-50/30",
  warning: "border-caution/30 bg-amber-50/30",
};

const trendColors = {
  up: "text-positive",
  down: "text-negative",
  flat: "text-text-secondary",
};

const TrendIcons = {
  up: TrendingUp,
  down: TrendingDown,
  flat: Minus,
};

export function KpiCard({
  label,
  title,
  value,
  trend,
  trendValue,
  variant = "default",
  subtitle,
  icon: Icon,
  hoverLift = false,
  generous = false,
  className,
}: KpiCardProps) {
  const displayLabel = label ?? title ?? "";
  const TrendIcon = trend ? TrendIcons[trend] : null;

  return (
    <div
      className={cn(
        "bg-white rounded-dr border shadow-dr-sm transition-all duration-300",
        generous ? "p-7" : "p-4",
        hoverLift && "hover-glow",
        variantStyles[variant],
        className
      )}
    >
      {/* 라벨 + 아이콘 */}
      <div className="flex items-center gap-2 mb-2">
        {Icon && <Icon className="h-4 w-4 text-text-secondary" />}
        <span className="text-kpi-label text-text-secondary">{displayLabel}</span>
      </div>

      {/* KPI 값 (IBM Plex Mono) */}
      <div className="font-mono text-kpi-value text-text-dark tabular-nums overflow-hidden text-ellipsis whitespace-nowrap">
        {value}
      </div>

      {/* 트렌드 */}
      {(trend || subtitle) && (
        <div className="mt-2 flex items-center gap-1.5">
          {TrendIcon && trendValue && (
            <>
              <TrendIcon className={cn("h-3.5 w-3.5", trendColors[trend!])} />
              <span className={cn("text-xs font-medium", trendColors[trend!])}>
                {trendValue}
              </span>
            </>
          )}
          {subtitle && (
            <span className="text-xs text-text-secondary">{subtitle}</span>
          )}
        </div>
      )}
    </div>
  );
}
