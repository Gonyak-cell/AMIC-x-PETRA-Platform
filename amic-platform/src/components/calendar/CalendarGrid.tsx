import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Badge } from "@/components/ui";
import { cn } from "@/lib/cn";
import type { CalendarEvent, CalendarEventModule } from "@/types/calendar";

const DAY_NAMES = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

const MODULE_COLORS: Record<CalendarEventModule, string> = {
  fdd: "bg-blue-500",
  kiis: "bg-emerald-500",
  im: "bg-purple-500",
};

const MODULE_BADGE: Record<CalendarEventModule, "info" | "success" | "warning"> = {
  fdd: "info",
  kiis: "success",
  im: "warning",
};

interface CalendarGridProps {
  year: number;
  month: number;
  events: CalendarEvent[];
}

export function CalendarGrid({ year, month, events }: CalendarGridProps) {
  const navigate = useNavigate();
  const [selectedDay, setSelectedDay] = useState<number | null>(null);

  const { days, startOffset } = useMemo(() => {
    const daysInMonth = new Date(year, month + 1, 0).getDate();
    const firstDayOfWeek = new Date(year, month, 1).getDay();
    return {
      days: Array.from({ length: daysInMonth }, (_, i) => i + 1),
      startOffset: firstDayOfWeek,
    };
  }, [year, month]);

  const eventsByDay = useMemo(() => {
    const map = new Map<number, CalendarEvent[]>();
    for (const event of events) {
      const d = new Date(event.date);
      if (d.getFullYear() === year && d.getMonth() === month) {
        const day = d.getDate();
        if (!map.has(day)) map.set(day, []);
        map.get(day)!.push(event);
      }
    }
    return map;
  }, [events, year, month]);

  const today = new Date();
  const isCurrentMonth =
    today.getFullYear() === year && today.getMonth() === month;
  const todayDate = today.getDate();

  const selectedEvents = selectedDay ? (eventsByDay.get(selectedDay) ?? []) : [];

  return (
    <div className="flex gap-6">
      {/* Grid */}
      <div className="flex-1">
        {/* Day headers */}
        <div className="grid grid-cols-7 gap-px mb-1">
          {DAY_NAMES.map((d) => (
            <div
              key={d}
              className="text-xs font-medium text-text-secondary text-center py-2"
            >
              {d}
            </div>
          ))}
        </div>

        {/* Date cells */}
        <div className="grid grid-cols-7 gap-px bg-gray-border rounded-lg overflow-hidden">
          {/* Empty cells for offset */}
          {Array.from({ length: startOffset }).map((_, i) => (
            <div key={`empty-${i}`} className="bg-bg-cool h-24" />
          ))}

          {days.map((day) => {
            const dayEvents = eventsByDay.get(day) ?? [];
            const isToday = isCurrentMonth && day === todayDate;
            const isSelected = day === selectedDay;

            return (
              <button
                key={day}
                className={cn(
                  "bg-white h-24 p-1.5 text-left hover:bg-blue-50/50 transition-colors",
                  isSelected && "ring-2 ring-amic ring-inset",
                )}
                onClick={() => setSelectedDay(isSelected ? null : day)}
              >
                <span
                  className={cn(
                    "text-xs font-medium inline-flex items-center justify-center w-6 h-6 rounded-full",
                    isToday
                      ? "bg-amic text-white"
                      : "text-text-dark",
                  )}
                >
                  {day}
                </span>
                {/* Event dots */}
                <div className="flex flex-wrap gap-0.5 mt-1">
                  {dayEvents.slice(0, 4).map((ev) => (
                    <span
                      key={ev.id}
                      className={cn(
                        "w-1.5 h-1.5 rounded-full",
                        MODULE_COLORS[ev.module],
                      )}
                      title={ev.title}
                    />
                  ))}
                  {dayEvents.length > 4 && (
                    <span className="text-[10px] text-text-secondary">
                      +{dayEvents.length - 4}
                    </span>
                  )}
                </div>
              </button>
            );
          })}
        </div>
      </div>

      {/* Event sidebar */}
      {selectedDay !== null && (
        <div className="w-72 shrink-0">
          <h3 className="text-sm font-medium text-text-dark mb-3">
            {new Date(year, month, selectedDay).toLocaleDateString("en-US", {
              month: "long",
              day: "numeric",
              year: "numeric",
            })}
          </h3>
          {selectedEvents.length === 0 ? (
            <p className="text-sm text-text-secondary">No events on this day.</p>
          ) : (
            <div className="space-y-2">
              {selectedEvents.map((ev) => (
                <button
                  key={ev.id}
                  className="w-full text-left p-3 border border-gray-border rounded-lg hover:bg-bg-cool transition-colors"
                  onClick={() => navigate(ev.entityPath)}
                >
                  <div className="flex items-center gap-2 mb-1">
                    <span
                      className={cn(
                        "w-2 h-2 rounded-full",
                        MODULE_COLORS[ev.module],
                      )}
                    />
                    <Badge variant={MODULE_BADGE[ev.module]} className="text-xs">
                      {ev.module.toUpperCase()}
                    </Badge>
                  </div>
                  <p className="text-sm text-text-dark">{ev.title}</p>
                  <p className="text-xs text-text-secondary mt-0.5">
                    {ev.type.replace(/_/g, " ")}
                  </p>
                </button>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
