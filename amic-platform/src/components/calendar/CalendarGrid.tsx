import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { ChevronRight, ArrowLeft } from "lucide-react";
import { Badge } from "@/components/ui";
import { cn } from "@/lib/cn";
import { PHASE_CONFIG } from "@/modules/ma/constants";
import type { CalendarEvent, CalendarEventModule } from "@/types/calendar";

const DAY_NAMES = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

const MODULE_COLORS: Record<CalendarEventModule, string> = {
  ma: "bg-accent",
};

const MODULE_BADGE: Record<CalendarEventModule, "info" | "success" | "warning"> = {
  ma: "success",
};

interface CalendarGridProps {
  year: number;
  month: number;
  events: CalendarEvent[];
}

interface EventGroup {
  entityId: string;
  entityPath: string;
  label: string;
  module: CalendarEventModule;
  phase: string;
  phaseLabel: string;
  phaseOrder: number;
  events: CalendarEvent[];
}

export function CalendarGrid({ year, month, events }: CalendarGridProps) {
  const navigate = useNavigate();
  const [selectedDay, setSelectedDay] = useState<number | null>(null);
  const [selectedEntityId, setSelectedEntityId] = useState<string | null>(null);

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

  // 선택된 프로젝트의 이벤트가 있는 날짜 Set
  const highlightedDays = useMemo<Set<number>>(() => {
    if (!selectedEntityId) return new Set();
    const set = new Set<number>();
    for (const event of events) {
      if (event.entityId === selectedEntityId) {
        const d = new Date(event.date);
        if (d.getFullYear() === year && d.getMonth() === month) {
          set.add(d.getDate());
        }
      }
    }
    return set;
  }, [selectedEntityId, events, year, month]);

  // 사이드바에 표시할 이벤트 결정
  const sidebarEvents = useMemo<CalendarEvent[]>(() => {
    if (selectedEntityId) {
      return events.filter((ev) => ev.entityId === selectedEntityId);
    }
    if (selectedDay) {
      return eventsByDay.get(selectedDay) ?? [];
    }
    return [];
  }, [selectedEntityId, selectedDay, events, eventsByDay]);

  // 같은 entityId를 가진 이벤트들을 프로젝트 단위로 그룹핑
  const groupedEvents = useMemo<EventGroup[]>(() => {
    const map = new Map<string, EventGroup>();
    for (const ev of sidebarEvents) {
      if (!map.has(ev.entityId)) {
        const label = ev.title.split(" — ")[0] || ev.title;
        map.set(ev.entityId, {
          entityId: ev.entityId,
          entityPath: ev.entityPath,
          label,
          module: ev.module,
          phase: ev.phase ?? "",
          phaseLabel: ev.phaseLabel ?? "",
          phaseOrder: ev.phaseOrder ?? 1,
          events: [],
        });
      }
      map.get(ev.entityId)!.events.push(ev);
    }
    return Array.from(map.values());
  }, [sidebarEvents]);

  const handleProjectClick = (entityId: string) => {
    setSelectedEntityId(entityId);
    setSelectedDay(null);
  };

  const handleBackToDay = () => {
    setSelectedEntityId(null);
  };

  const handleDayClick = (day: number) => {
    if (selectedEntityId) {
      setSelectedEntityId(null);
      setSelectedDay(day);
    } else {
      setSelectedDay(selectedDay === day ? null : day);
    }
  };

  const showSidebar = selectedDay !== null || selectedEntityId !== null;

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
            const isSelected = day === selectedDay && !selectedEntityId;
            const isHighlighted = highlightedDays.has(day);

            return (
              <button
                key={day}
                className={cn(
                  "bg-white h-24 p-1.5 text-left hover:bg-blue-50/50 transition-colors",
                  isSelected && "ring-2 ring-amic ring-inset",
                  isHighlighted && "bg-bg-light-green ring-1 ring-accent/30 ring-inset",
                )}
                onClick={() => handleDayClick(day)}
              >
                <span
                  className={cn(
                    "text-xs font-medium inline-flex items-center justify-center w-6 h-6 rounded-full",
                    isToday
                      ? "bg-amic text-white"
                      : isHighlighted
                        ? "text-accent font-bold"
                        : "text-text-dark",
                  )}
                >
                  {day}
                </span>
                {/* Event dots — 프로젝트(entityId)별 1개 */}
                <div className="flex flex-wrap gap-0.5 mt-1">
                  {Array.from(
                    new Map(dayEvents.map((ev) => [ev.entityId, ev])).values(),
                  )
                    .slice(0, 4)
                    .map((ev) => (
                      <span
                        key={ev.entityId}
                        className={cn(
                          "w-1.5 h-1.5 rounded-full",
                          MODULE_COLORS[ev.module],
                        )}
                        title={ev.title.split(" — ")[0]}
                      />
                    ))}
                </div>
              </button>
            );
          })}
        </div>
      </div>

      {/* Event sidebar */}
      {showSidebar && (
        <div className="w-80 shrink-0">
          {/* 사이드바 헤더 */}
          {selectedEntityId ? (
            <div className="mb-3">
              <button
                className="flex items-center gap-1 text-xs text-text-secondary hover:text-text-dark transition-colors mb-1"
                onClick={handleBackToDay}
              >
                <ArrowLeft className="w-3 h-3" />
                전체 보기
              </button>
              <h3 className="text-sm font-medium text-text-dark">
                프로젝트 마일스톤
              </h3>
            </div>
          ) : (
            <h3 className="text-sm font-medium text-text-dark mb-3">
              {new Date(year, month, selectedDay!).toLocaleDateString("en-US", {
                month: "long",
                day: "numeric",
                year: "numeric",
              })}
            </h3>
          )}

          {groupedEvents.length === 0 ? (
            <p className="text-sm text-text-secondary">No events on this day.</p>
          ) : (
            <div className="space-y-3">
              {groupedEvents.map((group) => (
                <div
                  key={group.entityId}
                  className={cn(
                    "border rounded-lg p-3 transition-colors",
                    selectedEntityId === group.entityId
                      ? "border-accent/50 bg-bg-light-green"
                      : "border-gray-border hover:border-accent/50 cursor-pointer",
                  )}
                  onClick={
                    selectedEntityId ? undefined : () => handleProjectClick(group.entityId)
                  }
                >
                  {/* 프로젝트 헤더 */}
                  <div className="flex items-center gap-2 mb-2">
                    <span className={cn("w-2 h-2 rounded-full", MODULE_COLORS[group.module])} />
                    <Badge variant={MODULE_BADGE[group.module]} className="text-xs">
                      {group.module.toUpperCase()}
                    </Badge>
                    <span className="text-sm font-medium text-text-dark truncate">
                      {group.label}
                    </span>
                  </div>

                  {/* 이벤트 목록 */}
                  <div className="space-y-1 mb-3">
                    {group.events.map((ev) => (
                      <div key={ev.id} className="flex items-center gap-2">
                        <span className="w-1 h-1 rounded-full bg-accent/60 shrink-0" />
                        <p className="text-xs text-text-secondary">
                          {ev.type === "transaction_created" && `거래 생성 (${ev.date})`}
                          {ev.type === "target_close" && `목표 종결일 (${ev.date})`}
                          {ev.type === "phase_current" && `현재 단계: ${group.phaseLabel} (${ev.date})`}
                        </p>
                      </div>
                    ))}
                  </div>

                  {/* 7단계 마일스톤 스테퍼 */}
                  <div className="mb-3">
                    <div className="flex items-center gap-0.5">
                      {PHASE_CONFIG.map((pc, idx) => {
                        const isCompleted = pc.order < group.phaseOrder;
                        const isCurrent = pc.order === group.phaseOrder;
                        return (
                          <div key={pc.phase} className="flex items-center">
                            {idx > 0 && (
                              <div
                                className={cn(
                                  "w-2 h-0.5",
                                  isCompleted || isCurrent ? "bg-accent" : "bg-gray-200",
                                )}
                              />
                            )}
                            <div
                              className={cn(
                                "w-3 h-3 rounded-full flex items-center justify-center shrink-0",
                                isCurrent
                                  ? "bg-accent ring-2 ring-accent/30"
                                  : isCompleted
                                    ? "bg-accent"
                                    : "bg-gray-200",
                              )}
                              title={pc.label}
                            />
                          </div>
                        );
                      })}
                    </div>
                    <p className="text-xs text-text-secondary mt-1.5">
                      현재: <span className="font-medium text-text-dark">{group.phaseLabel}</span>
                      {" "}({group.phaseOrder}/7)
                    </p>
                  </div>

                  {/* 자세히 보기 */}
                  <button
                    className="flex items-center gap-1 text-xs font-medium text-amic hover:text-amic/80 transition-colors"
                    onClick={(e) => {
                      e.stopPropagation();
                      navigate(group.entityPath);
                    }}
                  >
                    자세히 보기
                    <ChevronRight className="w-3 h-3" />
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
