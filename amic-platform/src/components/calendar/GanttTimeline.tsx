import { useNavigate } from "react-router-dom";
import { Badge } from "@/components/ui";
import { cn } from "@/lib/cn";
import type { GanttItem, CalendarEventModule } from "@/types/calendar";

const MODULE_BAR_COLORS: Record<CalendarEventModule, string> = {
  fdd: "bg-blue-400",
  kiis: "bg-emerald-400",
  im: "bg-purple-400",
};

const MODULE_BADGE: Record<CalendarEventModule, "info" | "success" | "warning"> = {
  fdd: "info",
  kiis: "success",
  im: "warning",
};

interface GanttTimelineProps {
  items: GanttItem[];
  year: number;
  month: number;
}

export function GanttTimeline({ items, year, month }: GanttTimelineProps) {
  const navigate = useNavigate();

  // Show 6 months range centered around selected month
  const months: Array<{ year: number; month: number; label: string }> = [];
  for (let i = -1; i < 5; i++) {
    const d = new Date(year, month + i, 1);
    months.push({
      year: d.getFullYear(),
      month: d.getMonth(),
      label: d.toLocaleDateString("en-US", {
        month: "short",
        year: "2-digit",
      }),
    });
  }

  const rangeStart = new Date(months[0].year, months[0].month, 1).getTime();
  const rangeEnd = new Date(
    months[months.length - 1].year,
    months[months.length - 1].month + 1,
    0,
  ).getTime();
  const totalRange = rangeEnd - rangeStart;

  const getPosition = (dateStr: string): number => {
    const t = new Date(dateStr).getTime();
    return Math.max(0, Math.min(100, ((t - rangeStart) / totalRange) * 100));
  };

  if (items.length === 0) {
    return (
      <div className="text-center py-12 text-sm text-text-secondary">
        No timeline items for the selected filters.
      </div>
    );
  }

  return (
    <div className="space-y-0">
      {/* Month headers */}
      <div className="flex border-b border-gray-border mb-2">
        <div className="w-48 shrink-0" />
        <div className="flex-1 flex">
          {months.map((m) => (
            <div
              key={`${m.year}-${m.month}`}
              className="flex-1 text-xs text-text-secondary text-center py-2 border-l border-gray-border first:border-l-0"
            >
              {m.label}
            </div>
          ))}
        </div>
      </div>

      {/* Gantt rows */}
      {items.map((item) => {
        const left = getPosition(item.startDate);
        const right = getPosition(item.endDate);
        const width = Math.max(right - left, 1);

        return (
          <div
            key={item.id}
            className="flex items-center h-10 hover:bg-bg-cool transition-colors group"
          >
            {/* Label */}
            <div className="w-48 shrink-0 flex items-center gap-2 px-2 truncate">
              <Badge variant={MODULE_BADGE[item.module]} className="text-xs shrink-0">
                {item.module.toUpperCase()}
              </Badge>
              <button
                className="text-sm text-text-dark truncate hover:text-amic transition-colors"
                onClick={() => navigate(item.entityPath)}
                title={item.label}
              >
                {item.label}
              </button>
            </div>

            {/* Bar area */}
            <div className="flex-1 relative h-6">
              {/* Grid lines for months */}
              {months.map((m, i) => (
                <div
                  key={`grid-${m.year}-${m.month}`}
                  className="absolute top-0 bottom-0 border-l border-gray-border/50"
                  style={{ left: `${(i / months.length) * 100}%` }}
                />
              ))}

              {/* Bar */}
              <div
                className={cn(
                  "absolute top-1 h-4 rounded-sm cursor-pointer transition-opacity",
                  MODULE_BAR_COLORS[item.module],
                  "opacity-70 group-hover:opacity-100",
                )}
                style={{
                  left: `${left}%`,
                  width: `${width}%`,
                  minWidth: "4px",
                }}
                onClick={() => navigate(item.entityPath)}
                title={`${item.label}: ${item.startDate} → ${item.endDate}`}
              >
                {item.progress !== undefined && item.progress < 100 && (
                  <div
                    className="h-full bg-white/30 rounded-sm"
                    style={{ width: `${100 - item.progress}%`, marginLeft: "auto" }}
                  />
                )}
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}
