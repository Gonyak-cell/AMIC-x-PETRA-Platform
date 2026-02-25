import { cn } from "@/lib/cn";
import type { CategorySummary, ChecklistStatusType } from "@/modules/im/types/checklist";
import { CHECKLIST_CATEGORY_LABEL, CHECKLIST_STATUS_LABEL } from "@/modules/im/types/checklist";

// ── Status badge colors ─────────────────────────────────────

const STATUS_COLORS: Record<ChecklistStatusType, string> = {
  EXTRACTING: "bg-blue-100 text-blue-700",
  REVIEW: "bg-amber-100 text-amber-700",
  CONFIRMED: "bg-emerald-100 text-emerald-700",
  GENERATING: "bg-violet-100 text-violet-700",
  COMPLETED: "bg-positive/10 text-positive",
  FAILED: "bg-negative/10 text-negative",
};

// ── Component Props ─────────────────────────────────────────

export interface ChecklistProgressBarProps {
  status: ChecklistStatusType;
  totalItems: number;
  confirmedItems: number;
  missingItems: number;
  completionPct: number;
  categories?: CategorySummary[];
  className?: string;
}

/**
 * Full-width progress bar with status badge, overall %, and optional category breakdown.
 */
export function ChecklistProgressBar({
  status,
  totalItems,
  confirmedItems,
  missingItems,
  completionPct,
  categories,
  className,
}: ChecklistProgressBarProps) {
  const pct = Math.min(100, Math.max(0, completionPct));

  return (
    <div className={cn("space-y-4", className)}>
      {/* Top row: status badge + numbers */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <span
            className={cn(
              "inline-flex items-center px-2.5 py-1 text-xs font-semibold rounded-full",
              STATUS_COLORS[status],
            )}
          >
            {CHECKLIST_STATUS_LABEL[status]}
          </span>
          <span className="text-sm text-text-dark font-medium">
            {confirmedItems} / {totalItems} confirmed
          </span>
        </div>
        {missingItems > 0 && (
          <span className="text-xs text-negative font-medium">
            {missingItems} missing
          </span>
        )}
      </div>

      {/* Overall progress bar */}
      <div
        className="relative h-2.5 bg-gray-100 rounded-full overflow-hidden"
        role="progressbar"
        aria-valuenow={pct}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label={`Checklist completion: ${pct.toFixed(0)}%`}
      >
        <div
          className="absolute inset-y-0 left-0 rounded-full bg-gradient-to-r from-amic to-accent transition-all duration-500"
          style={{ width: `${pct}%` }}
        />
      </div>
      <div className="flex items-center justify-between text-xs text-text-secondary">
        <span>{pct.toFixed(0)}% complete</span>
        <span>{totalItems} total items</span>
      </div>

      {/* Category breakdown (optional) */}
      {categories && categories.length > 0 && (
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3 pt-2">
          {categories.map((cat) => {
            const catPct = Math.min(100, Math.max(0, cat.completion_pct));
            const label =
              CHECKLIST_CATEGORY_LABEL[cat.category as keyof typeof CHECKLIST_CATEGORY_LABEL] ??
              cat.category;
            return (
              <div
                key={cat.category}
                className="space-y-1.5 p-2.5 rounded-lg bg-bg-cool"
              >
                <div className="flex items-center justify-between">
                  <span className="text-xs font-medium text-text-dark">
                    {label}
                  </span>
                  <span className="text-[10px] text-text-secondary">
                    {cat.confirmed}/{cat.total}
                  </span>
                </div>
                <div className="h-1.5 bg-gray-200 rounded-full overflow-hidden">
                  <div
                    className={cn(
                      "h-full rounded-full transition-all duration-300",
                      catPct === 100
                        ? "bg-positive"
                        : cat.missing > 0
                          ? "bg-amber-400"
                          : "bg-accent",
                    )}
                    style={{ width: `${catPct}%` }}
                  />
                </div>
                {cat.missing > 0 && (
                  <span className="text-[10px] text-negative">
                    {cat.missing} missing
                  </span>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
