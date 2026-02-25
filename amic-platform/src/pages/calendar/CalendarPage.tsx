import { useState, useCallback } from "react";
import { useCalendarEvents } from "@/hooks/useCalendar";
import { CalendarFilterBar } from "@/components/calendar/CalendarFilterBar";
import { CalendarGrid } from "@/components/calendar/CalendarGrid";
import { GanttTimeline } from "@/components/calendar/GanttTimeline";
import { downloadIcs } from "@/lib/ics";
import { Skeleton, PageHero } from "@/components/ui";
import type { CalendarViewMode } from "@/types/calendar";
import heroImg from "@/assets/images/heroes/forestgp-background.jpg";

export default function CalendarPage() {
  const now = new Date();
  const [year, setYear] = useState(now.getFullYear());
  const [month, setMonth] = useState(now.getMonth());
  const [viewMode, setViewMode] = useState<CalendarViewMode>("calendar");

  const filter = { month, year };
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

  const handleExportIcs = useCallback(() => {
    downloadIcs(events, `amic-calendar-${year}-${String(month + 1).padStart(2, "0")}.ics`);
  }, [events, year, month]);

  return (
    <div className="space-y-6">
      {/* Hero Section */}
      <PageHero
        title="Calendar & Timeline"
        subtitle="M&A Pipeline milestones and transaction progress"
        backgroundImage={heroImg}
        backgroundOpacity={0.35}
        backgroundPosition="bottom"
        compact
      />

      {/* Filter bar */}
      <CalendarFilterBar
        year={year}
        month={month}
        viewMode={viewMode}
        onPrevMonth={handlePrevMonth}
        onNextMonth={handleNextMonth}
        onToday={handleToday}
        onViewModeChange={setViewMode}
        onExportIcs={handleExportIcs}
      />

      {/* Error banner */}
      {errors.ma && (
        <div className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-700">
          M&A Pipeline 서비스에 연결할 수 없습니다. 이벤트가 표시되지 않을 수 있습니다.
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
              <div className="w-3 h-3 rounded-full bg-accent" />
              <span className="text-text-secondary">M&A Transaction</span>
            </div>
          </div>
        </>
      ) : (
        <GanttTimeline items={ganttItems} year={year} month={month} />
      )}
    </div>
  );
}
