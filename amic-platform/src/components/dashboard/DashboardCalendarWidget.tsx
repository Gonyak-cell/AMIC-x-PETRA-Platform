/** 홈 대시보드 — 홈 전용 compact calendar 위젯 */

import { useMemo } from "react";
import { useNavigate } from "react-router-dom";
import { CalendarDays, ArrowRight, CalendarClock } from "lucide-react";
import { useCalendarEvents } from "@/hooks/useCalendar";
import { cn } from "@/lib/cn";

const DAY_LABELS = ["일", "월", "화", "수", "목", "금", "토"];

function getMonthGrid(year: number, month: number) {
  const firstDay = new Date(year, month, 1).getDay();
  const daysInMonth = new Date(year, month + 1, 0).getDate();
  const cells: (number | null)[] = [];
  for (let i = 0; i < firstDay; i++) cells.push(null);
  for (let d = 1; d <= daysInMonth; d++) cells.push(d);
  return cells;
}

export default function DashboardCalendarWidget() {
  const navigate = useNavigate();
  const now = new Date();
  const year = now.getFullYear();
  const month = now.getMonth();
  const todayDate = now.getDate();
  const todayStr = now.toISOString().slice(0, 10);
  const monthStr = `${year}-${String(month + 1).padStart(2, "0")}`;

  // month는 0-based (CalendarPage와 동일 계약)
  const { events, isLoading } = useCalendarEvents({ month, year });

  const monthLabel = now.toLocaleDateString("ko-KR", {
    year: "numeric",
    month: "long",
  });

  const cells = useMemo(() => getMonthGrid(year, month), [year, month]);

  /* 이벤트가 있는 날짜 set */
  const eventDates = useMemo(() => {
    const set = new Set<number>();
    for (const ev of events) {
      if (ev.date.startsWith(monthStr)) {
        const day = parseInt(ev.date.slice(8, 10), 10);
        if (day) set.add(day);
      }
    }
    return set;
  }, [events, monthStr]);

  /* 오늘 이후 upcoming events (최대 5건) */
  const upcoming = useMemo(
    () =>
      events
        .filter((e) => e.date >= todayStr)
        .sort((a, b) => a.date.localeCompare(b.date))
        .slice(0, 5),
    [events, todayStr],
  );

  const cardShadow =
    "0px 16px 24px rgba(0,0,0,0.06), 0px 2px 6px rgba(0,0,0,0.04), 0px 0px 1px rgba(0,0,0,0.04)";

  /* ── Loading skeleton ── */
  if (isLoading) {
    return (
      <div>
        <div className="flex items-center justify-between mb-3">
          <h2 className="label-uppercase">Calendar</h2>
        </div>
        <div
          className="bg-white rounded-2xl overflow-hidden"
          style={{ boxShadow: cardShadow }}
        >
          <div className="px-5 pt-5 pb-4 space-y-3 animate-pulse">
            <div className="h-4 w-24 bg-gray-100 rounded" />
            <div className="grid grid-cols-7 gap-1">
              {Array.from({ length: 35 }).map((_, i) => (
                <div key={i} className="h-6 w-7 rounded bg-gray-50" />
              ))}
            </div>
          </div>
          <div className="border-t border-gray-100 px-5 py-2.5 animate-pulse space-y-1.5">
            {Array.from({ length: 3 }).map((_, i) => (
              <div key={i} className="h-8 bg-gray-50 rounded" />
            ))}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col">
      {/* ── Header: label + "전체 보기" ── */}
      <div className="flex items-center justify-between mb-3">
        <h2 className="label-uppercase">Calendar</h2>
        <button
          onClick={() => navigate("/calendar")}
          className="text-xs text-text-secondary hover:text-accent transition-colors flex items-center gap-1"
        >
          전체 보기
          <ArrowRight className="w-3 h-3" />
        </button>
      </div>

      {/* ── Card container (same shadow as MY PROJECTS) ── */}
      <div
        className="bg-white rounded-2xl overflow-hidden flex-1 flex flex-col"
        style={{ boxShadow: cardShadow }}
      >
        {/* Mini calendar section */}
        <div className="px-5 pt-5 pb-4">
          <p className="text-sm font-medium text-text-dark mb-1.5">
            {monthLabel}
          </p>

          <div className="grid grid-cols-7 gap-0.5 text-center">
            {DAY_LABELS.map((d) => (
              <div
                key={d}
                className="text-[10px] text-text-muted font-medium py-0.5"
              >
                {d}
              </div>
            ))}
            {cells.map((day, idx) => {
              const isToday = day === todayDate;
              const hasEvent = day !== null && eventDates.has(day);
              return (
                <div
                  key={idx}
                  className={cn(
                    "relative flex items-center justify-center h-6 text-xs rounded-md",
                    day === null && "invisible",
                    isToday && "bg-accent text-white font-semibold",
                    !isToday && hasEvent && "font-medium text-accent",
                    !isToday && !hasEvent && "text-text-secondary",
                  )}
                >
                  {day}
                  {hasEvent && !isToday && (
                    <span className="absolute bottom-0.5 left-1/2 -translate-x-1/2 w-1 h-1 rounded-full bg-accent" />
                  )}
                </div>
              );
            })}
          </div>
        </div>

        {/* Upcoming events section (separated by border) */}
        <div className="border-t border-gray-100 px-5 py-2.5 flex-1 flex flex-col">
          <h4 className="text-xs font-medium text-text-muted uppercase tracking-wide mb-1 flex items-center gap-1.5">
            <CalendarClock className="w-3.5 h-3.5" />
            다가오는 일정
          </h4>
          {upcoming.length === 0 ? (
            <div className="flex flex-col items-center py-2.5 text-text-muted">
              <CalendarDays className="w-6 h-6 mb-1 opacity-40" />
              <p className="text-xs">예정된 일정이 없습니다</p>
            </div>
          ) : (
            <ul className="space-y-0.5 max-h-[148px] overflow-y-auto">
              {upcoming.map((ev) => (
                <li key={ev.id}>
                  <button
                    className="w-full text-left px-2.5 py-1 rounded-md hover:bg-bg-cool transition-colors group"
                    onClick={() => navigate(ev.entityPath)}
                  >
                    <div className="flex items-center gap-2">
                      <span className="text-[11px] text-text-muted font-mono shrink-0 w-[72px]">
                        {ev.date}
                      </span>
                      <span className="text-xs text-text-dark truncate group-hover:text-accent transition-colors">
                        {ev.title}
                      </span>
                    </div>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  );
}
