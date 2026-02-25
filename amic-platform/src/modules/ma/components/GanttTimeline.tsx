/**
 * M&A 딜 전용 간트 타임라인 컴포넌트
 * 7-phase 워크플로우를 수평 바 차트로 시각화
 */
import { useMemo } from "react";
import { Calendar, Diamond, Flag } from "lucide-react";
import { CHART_COLORS } from "@/components/charts/chartColors";
import type { GanttResponse, GanttPhaseBar, GanttMilestone } from "@/modules/ma/types/timeline";

interface GanttTimelineProps {
  data: GanttResponse;
}

// ── Helpers ──────────────────────────────────────────────

const DAY_MS = 86_400_000;

function parseDate(s: string): number {
  return new Date(s + "T00:00:00").getTime();
}

function formatDate(s: string): string {
  const d = new Date(s + "T00:00:00");
  return `${d.getFullYear()}.${String(d.getMonth() + 1).padStart(2, "0")}.${String(d.getDate()).padStart(2, "0")}`;
}

function daysBetween(a: string, b: string): number {
  return Math.round((parseDate(b) - parseDate(a)) / DAY_MS);
}

function todayStr(): string {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

// ── Phase Color ──────────────────────────────────────────

const PHASE_COLORS: Record<string, string> = {
  completed: CHART_COLORS.positive,
  active: "#0091DA",
  upcoming: "#D1D5DB",
};

// ── Component ────────────────────────────────────────────

export function GanttTimeline({ data }: GanttTimelineProps) {
  const today = todayStr();

  const { timelineStart, timelineEnd, totalDays, phases, todayOffset, targetOffset, milestoneOffsets } =
    useMemo(() => {
      // 타임라인 범위 계산
      const allDates: string[] = [data.deal_start_date, today];
      for (const p of data.phases) {
        if (p.start_date) allDates.push(p.start_date);
        if (p.end_date) allDates.push(p.end_date);
      }
      for (const m of data.milestones) {
        allDates.push(m.date);
      }
      if (data.target_close_date) allDates.push(data.target_close_date);

      const timestamps = allDates.map(parseDate);
      const minTs = Math.min(...timestamps);
      const maxTs = Math.max(...timestamps);

      // 좌우 여유 14일
      const startTs = minTs - 14 * DAY_MS;
      const endTs = maxTs + 30 * DAY_MS;
      const start = new Date(startTs).toISOString().slice(0, 10);
      const end = new Date(endTs).toISOString().slice(0, 10);
      const total = Math.max(daysBetween(start, end), 1);

      // phase 오프셋 계산
      const phasesWithOffset = data.phases.map((p: GanttPhaseBar) => {
        const s = p.start_date ? daysBetween(start, p.start_date) : null;
        const e = p.end_date
          ? daysBetween(start, p.end_date)
          : p.status === "active"
            ? daysBetween(start, today)
            : null;
        return { ...p, startOffset: s, endOffset: e };
      });

      const tOffset = daysBetween(start, today);
      const targetOff = data.target_close_date
        ? daysBetween(start, data.target_close_date)
        : null;

      const msOffsets = data.milestones.map((m: GanttMilestone) => ({
        ...m,
        offset: daysBetween(start, m.date),
      }));

      return {
        timelineStart: start,
        timelineEnd: end,
        totalDays: total,
        phases: phasesWithOffset,
        todayOffset: tOffset,
        targetOffset: targetOff,
        milestoneOffsets: msOffsets,
      };
    }, [data, today]);

  // 월 눈금 계산
  const monthTicks = useMemo(() => {
    const ticks: { label: string; offset: number }[] = [];
    const start = parseDate(timelineStart);
    const end = parseDate(timelineEnd);
    const d = new Date(start);
    d.setDate(1);
    d.setMonth(d.getMonth() + 1);

    while (d.getTime() <= end) {
      const ds = d.toISOString().slice(0, 10);
      const offset = daysBetween(timelineStart, ds);
      const label = `${d.getFullYear()}.${String(d.getMonth() + 1).padStart(2, "0")}`;
      ticks.push({ label, offset });
      d.setMonth(d.getMonth() + 1);
    }
    return ticks;
  }, [timelineStart, timelineEnd]);

  // Layout constants
  const ROW_HEIGHT = 40;
  const LABEL_WIDTH = 100;
  const CHART_PADDING_TOP = 32;
  const CHART_HEIGHT = CHART_PADDING_TOP + data.phases.length * ROW_HEIGHT + 40;

  const toX = (dayOffset: number) => `${(dayOffset / totalDays) * 100}%`;

  return (
    <div className="space-y-4">
      {/* Legend */}
      <div className="flex items-center gap-4 text-xs text-text-muted">
        <span className="flex items-center gap-1.5">
          <span className="w-3 h-3 rounded-sm" style={{ backgroundColor: PHASE_COLORS.completed }} />
          완료
        </span>
        <span className="flex items-center gap-1.5">
          <span className="w-3 h-3 rounded-sm" style={{ backgroundColor: PHASE_COLORS.active }} />
          진행 중
        </span>
        <span className="flex items-center gap-1.5">
          <span className="w-3 h-3 rounded-sm border border-gray-300" style={{ backgroundColor: PHASE_COLORS.upcoming }} />
          예정
        </span>
        {data.target_close_date && (
          <span className="flex items-center gap-1.5">
            <Flag size={12} className="text-negative" />
            목표 완료일: {formatDate(data.target_close_date)}
          </span>
        )}
        <span className="flex items-center gap-1.5 ml-auto">
          <Calendar size={12} />
          오늘: {formatDate(today)}
        </span>
      </div>

      {/* Chart */}
      <div className="relative overflow-x-auto border border-gray-border rounded-lg bg-white">
        <div className="flex min-w-[700px]">
          {/* Phase Labels */}
          <div className="flex-none" style={{ width: LABEL_WIDTH }}>
            <div style={{ height: CHART_PADDING_TOP }} className="border-b border-gray-border" />
            {phases.map((p) => (
              <div
                key={p.phase}
                className="flex items-center px-3 text-xs font-medium border-b border-gray-100 text-text-dark"
                style={{ height: ROW_HEIGHT }}
              >
                <span className="truncate">{p.label}</span>
              </div>
            ))}
          </div>

          {/* Bars Area */}
          <div className="flex-1 relative" style={{ height: CHART_HEIGHT }}>
            {/* Month grid lines + labels */}
            {monthTicks.map((tick) => (
              <div
                key={tick.label}
                className="absolute top-0 border-l border-gray-200"
                style={{
                  left: toX(tick.offset),
                  height: "100%",
                }}
              >
                <span className="absolute -top-0 left-1 text-[10px] text-text-muted whitespace-nowrap leading-[32px]">
                  {tick.label}
                </span>
              </div>
            ))}

            {/* Today line */}
            <div
              className="absolute top-0 w-px bg-blue-500 z-10"
              style={{ left: toX(todayOffset), height: "100%" }}
            >
              <span className="absolute -top-0 -left-3 text-[9px] text-blue-600 font-semibold leading-[32px]">
                Today
              </span>
            </div>

            {/* Target close date line */}
            {targetOffset != null && (
              <div
                className="absolute top-0 w-px z-10"
                style={{
                  left: toX(targetOffset),
                  height: "100%",
                  borderLeft: "2px dashed #BC2C1A",
                }}
              />
            )}

            {/* Phase bars */}
            {phases.map((p, idx) => {
              if (p.startOffset == null) return null;
              const barWidth = p.endOffset != null ? p.endOffset - p.startOffset : 0;
              if (barWidth <= 0 && p.status !== "active") return null;

              const minBarWidth = Math.max(barWidth, 2);
              const top = CHART_PADDING_TOP + idx * ROW_HEIGHT + 8;
              const barHeight = ROW_HEIGHT - 16;

              return (
                <div
                  key={p.phase}
                  className="absolute rounded group"
                  style={{
                    left: toX(p.startOffset),
                    width: toX(minBarWidth),
                    top,
                    height: barHeight,
                    backgroundColor: PHASE_COLORS[p.status],
                    opacity: p.status === "upcoming" ? 0.5 : 1,
                  }}
                >
                  {/* Active pulse animation */}
                  {p.status === "active" && (
                    <div
                      className="absolute inset-0 rounded animate-pulse"
                      style={{ backgroundColor: PHASE_COLORS.active, opacity: 0.3 }}
                    />
                  )}

                  {/* Tooltip on hover */}
                  <div className="hidden group-hover:block absolute -top-10 left-0 z-20 bg-white border border-gray-border shadow-md rounded px-2 py-1 text-xs whitespace-nowrap">
                    <span className="font-medium">{p.label}</span>
                    <span className="text-text-muted ml-2">
                      {p.start_date ? formatDate(p.start_date) : "?"}
                      {" → "}
                      {p.end_date ? formatDate(p.end_date) : "진행 중"}
                    </span>
                    {p.start_date && p.end_date && (
                      <span className="text-text-muted ml-1">
                        ({daysBetween(p.start_date, p.end_date)}일)
                      </span>
                    )}
                  </div>
                </div>
              );
            })}

            {/* Milestones */}
            {milestoneOffsets.map((m, idx) => {
              const top = CHART_PADDING_TOP + data.phases.length * ROW_HEIGHT + 4;
              return (
                <div
                  key={`${m.date}-${idx}`}
                  className="absolute z-10 group"
                  style={{ left: toX(m.offset), top }}
                >
                  <Diamond size={14} className="text-amber-500 fill-amber-400 -ml-[7px]" />
                  <div className="hidden group-hover:block absolute -top-8 left-0 z-20 bg-white border border-gray-border shadow-md rounded px-2 py-1 text-xs whitespace-nowrap">
                    <span className="font-medium">{m.label}</span>
                    <span className="text-text-muted ml-2">{formatDate(m.date)}</span>
                  </div>
                </div>
              );
            })}

            {/* Row separator lines */}
            {phases.map((_, idx) => (
              <div
                key={idx}
                className="absolute w-full border-b border-gray-100"
                style={{ top: CHART_PADDING_TOP + (idx + 1) * ROW_HEIGHT }}
              />
            ))}
          </div>
        </div>
      </div>

      {/* Phase Duration Summary */}
      <div className="grid grid-cols-7 gap-2">
        {phases.map((p) => {
          const days = p.start_date && p.end_date ? daysBetween(p.start_date, p.end_date) : null;
          const activeDays = p.start_date && p.status === "active" ? daysBetween(p.start_date, today) : null;
          return (
            <div
              key={p.phase}
              className="rounded-lg border border-gray-border p-2 text-center"
              style={{
                borderLeftColor: PHASE_COLORS[p.status],
                borderLeftWidth: 3,
              }}
            >
              <div className="text-[10px] text-text-muted">{p.label}</div>
              <div className="text-sm font-semibold mt-0.5">
                {days != null
                  ? `${days}일`
                  : activeDays != null
                    ? `${activeDays}일~`
                    : "—"}
              </div>
              <div className="text-[10px] text-text-muted mt-0.5">
                {p.status === "completed" ? "완료" : p.status === "active" ? "진행 중" : "예정"}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
