import { ChevronLeft, ChevronRight, Download } from "lucide-react";
import { Button } from "@/components/ui";
import type { CalendarEventModule, CalendarViewMode } from "@/types/calendar";

const MODULES: Array<{ value: CalendarEventModule; label: string }> = [
  { value: "fdd", label: "FDD" },
  { value: "kiis", label: "KIIS" },
  { value: "im", label: "IM" },
];

const MONTH_NAMES = [
  "January", "February", "March", "April", "May", "June",
  "July", "August", "September", "October", "November", "December",
];

interface CalendarFilterBarProps {
  year: number;
  month: number;
  modules: CalendarEventModule[];
  viewMode: CalendarViewMode;
  onPrevMonth: () => void;
  onNextMonth: () => void;
  onToday: () => void;
  onToggleModule: (mod: CalendarEventModule) => void;
  onViewModeChange: (mode: CalendarViewMode) => void;
  onExportIcs: () => void;
}

export function CalendarFilterBar({
  year,
  month,
  modules,
  viewMode,
  onPrevMonth,
  onNextMonth,
  onToday,
  onToggleModule,
  onViewModeChange,
  onExportIcs,
}: CalendarFilterBarProps) {
  return (
    <div className="flex flex-wrap items-center gap-4">
      {/* Month navigation */}
      <div className="flex items-center gap-2">
        <Button variant="ghost" size="sm" onClick={onPrevMonth} aria-label="Previous month">
          <ChevronLeft className="h-4 w-4" />
        </Button>
        <span className="font-heading font-semibold text-text-dark min-w-[160px] text-center">
          {MONTH_NAMES[month]} {year}
        </span>
        <Button variant="ghost" size="sm" onClick={onNextMonth} aria-label="Next month">
          <ChevronRight className="h-4 w-4" />
        </Button>
        <Button variant="ghost" size="sm" onClick={onToday}>
          Today
        </Button>
      </div>

      {/* Module toggles */}
      <div className="flex gap-1">
        {MODULES.map((m) => (
          <Button
            key={m.value}
            variant={modules.includes(m.value) ? "primary" : "ghost"}
            size="sm"
            onClick={() => onToggleModule(m.value)}
          >
            {m.label}
          </Button>
        ))}
      </div>

      {/* View mode toggle */}
      <div className="flex gap-1 ml-auto">
        <Button
          variant={viewMode === "calendar" ? "primary" : "ghost"}
          size="sm"
          onClick={() => onViewModeChange("calendar")}
        >
          Calendar
        </Button>
        <Button
          variant={viewMode === "gantt" ? "primary" : "ghost"}
          size="sm"
          onClick={() => onViewModeChange("gantt")}
        >
          Gantt
        </Button>
        <Button variant="ghost" size="sm" icon={Download} onClick={onExportIcs}>
          .ics
        </Button>
      </div>
    </div>
  );
}
