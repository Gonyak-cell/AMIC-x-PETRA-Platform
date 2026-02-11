import { useState, useCallback } from "react";
import { useCalendarEvents } from "@/hooks/useCalendar";
import { CalendarFilterBar } from "@/components/calendar/CalendarFilterBar";
import { CalendarGrid } from "@/components/calendar/CalendarGrid";
import { GanttTimeline } from "@/components/calendar/GanttTimeline";
import { downloadIcs } from "@/lib/ics";
import { Skeleton } from "@/components/ui";
import type { CalendarEventModule, CalendarViewMode } from "@/types/calendar";

export default function CalendarPage() {
  const now = new Date();
  const [year, setYear] = useState(now.getFullYear());
  const [month, setMonth] = useState(now.getMonth());
  const [modules, setModules] = useState<CalendarEventModule[]>([
    "fdd",
    "kiis",
    "im",
  ]);
  const [viewMode, setViewMode] = useState<CalendarViewMode>("calendar");

  const filter = { modules, month, year };
  const { events, ganttItems, isLoading } = useCalendarEvents(filter);

  const handlePrevMonth = useCallback(() => {
    setMonth((prev) => {
      if (prev === 0) {
        setYear((y) => y - 1);
        return 11;
      }
      return prev - 1;
    });
  }, []);

  const handleNextMonth = useCallback(() => {
    setMonth((prev) => {
      if (prev === 11) {
        setYear((y) => y + 1);
        return 0;
      }
      return prev + 1;
    });
  }, []);

  const handleToday = useCallback(() => {
    const today = new Date();
    setYear(today.getFullYear());
    setMonth(today.getMonth());
  }, []);

  const handleToggleModule = useCallback((mod: CalendarEventModule) => {
    setModules((prev) =>
      prev.includes(mod) ? prev.filter((m) => m !== mod) : [...prev, mod],
    );
  }, []);

  const handleExportIcs = useCallback(() => {
    downloadIcs(events, `amic-calendar-${year}-${String(month + 1).padStart(2, "0")}.ics`);
  }, [events, year, month]);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-heading font-bold text-text-dark">
          Calendar & Timeline
        </h1>
        <p className="text-sm text-text-secondary mt-1">
          Deal milestones, portfolio dates, and document timelines across modules
        </p>
      </div>

      {/* Filter bar */}
      <CalendarFilterBar
        year={year}
        month={month}
        modules={modules}
        viewMode={viewMode}
        onPrevMonth={handlePrevMonth}
        onNextMonth={handleNextMonth}
        onToday={handleToday}
        onToggleModule={handleToggleModule}
        onViewModeChange={setViewMode}
        onExportIcs={handleExportIcs}
      />

      {/* Content */}
      {isLoading ? (
        <Skeleton className="h-96 w-full rounded-lg" />
      ) : viewMode === "calendar" ? (
        <CalendarGrid year={year} month={month} events={events} />
      ) : (
        <GanttTimeline items={ganttItems} year={year} month={month} />
      )}
    </div>
  );
}
