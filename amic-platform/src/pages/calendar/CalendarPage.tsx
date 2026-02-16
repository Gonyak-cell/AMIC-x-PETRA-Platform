import { useState, useCallback } from "react";
import { useCalendarEvents } from "@/hooks/useCalendar";
import { CalendarFilterBar } from "@/components/calendar/CalendarFilterBar";
import { CalendarGrid } from "@/components/calendar/CalendarGrid";
import { GanttTimeline } from "@/components/calendar/GanttTimeline";
import { downloadIcs } from "@/lib/ics";
import { Skeleton, PageHero } from "@/components/ui";
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
  const { events, ganttItems, isLoading, errors } = useCalendarEvents(filter);

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
      {/* Hero Section */}
      <PageHero
        title="Calendar & Timeline"
        subtitle="Deal milestones, portfolio dates, and document timelines across modules"
        compact
      />

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

      {/* Error banners for unreachable modules */}
      {(errors.fdd || errors.kiis || errors.im) && (
        <div className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-700">
          Some modules are unreachable:{" "}
          {[
            errors.fdd && "FDD",
            errors.kiis && "KIIS",
            errors.im && "IM",
          ]
            .filter(Boolean)
            .join(", ")}
          . Their events may be missing.
        </div>
      )}

      {/* Content */}
      {isLoading ? (
        <Skeleton className="h-96 w-full rounded-lg" />
      ) : viewMode === "calendar" ? (
        <>
          <CalendarGrid year={year} month={month} events={events} />
          <div className="flex items-center gap-6 text-sm">
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-amic" />
              <span className="text-text-secondary">FDD Deadline</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-green-500" />
              <span className="text-text-secondary">KIIS Deal</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-accent" />
              <span className="text-text-secondary">IM Due Date</span>
            </div>
          </div>
        </>
      ) : (
        <GanttTimeline items={ganttItems} year={year} month={month} />
      )}
    </div>
  );
}
