import { useMemo } from "react";
import { Calendar, Diamond, Flag } from "lucide-react";
import { Badge } from "@/components/ui/Badge";
import { Skeleton } from "@/components/ui/Skeleton";
import type { NegotiationGanttData, NegotiationGanttItem } from "@/modules/ma/types/negotiation_workspace";

interface ContractNegotiationGanttProps {
  data: NegotiationGanttData | null;
  isLoading: boolean;
  onContractClick: (contractId: string) => void;
  selectedContractId: string | null;
}

// ── Helpers ──────────────────────────────────────────────

const DAY_MS = 86_400_000;

function parseDate(s: string): number {
  // ISO datetime 또는 date-only 모두 처리
  return new Date(s.length <= 10 ? s + "T00:00:00" : s).getTime();
}

function daysBetween(a: string, b: string): number {
  return Math.round((parseDate(b) - parseDate(a)) / DAY_MS);
}

function todayStr(): string {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

function formatDate(s: string): string {
  const d = new Date(s.length <= 10 ? s + "T00:00:00" : s);
  return `${d.getFullYear()}.${String(d.getMonth() + 1).padStart(2, "0")}.${String(d.getDate()).padStart(2, "0")}`;
}

const CONTRACT_COLORS: Record<string, string> = {
  SPA: "#0091DA",
  SHA: "#6366F1",
  BTA: "#F59E0B",
  SSA: "#10B981",
  NDA: "#8B5CF6",
  LOI: "#EC4899",
  OTHER: "#6B7280",
};

// ── Component ────────────────────────────────────────────

export function ContractNegotiationGantt({
  data,
  isLoading,
  onContractClick,
  selectedContractId,
}: ContractNegotiationGanttProps) {
  const today = todayStr();

  const computed = useMemo(() => {
    if (!data || data.items.length === 0) return null;

    const allDates: string[] = [today];
    if (data.transaction_start_date) allDates.push(data.transaction_start_date);
    if (data.target_close_date) allDates.push(data.target_close_date);

    for (const item of data.items) {
      if (item.first_markup_at) allDates.push(item.first_markup_at);
      if (item.latest_markup_at) allDates.push(item.latest_markup_at);
      if (item.created_at) allDates.push(item.created_at);
    }

    const timestamps = allDates.map(parseDate);
    const minTs = Math.min(...timestamps);
    const maxTs = Math.max(...timestamps);

    const startTs = minTs - 14 * DAY_MS;
    const endTs = maxTs + 30 * DAY_MS;
    const start = new Date(startTs).toISOString().slice(0, 10);
    const end = new Date(endTs).toISOString().slice(0, 10);
    const totalDays = Math.max(daysBetween(start, end), 1);

    // 월 눈금
    const monthTicks: { label: string; offset: number }[] = [];
    const d = new Date(parseDate(start));
    d.setDate(1);
    d.setMonth(d.getMonth() + 1);
    while (d.getTime() <= parseDate(end)) {
      const ds = d.toISOString().slice(0, 10);
      monthTicks.push({
        label: `${d.getFullYear()}.${String(d.getMonth() + 1).padStart(2, "0")}`,
        offset: daysBetween(start, ds),
      });
      d.setMonth(d.getMonth() + 1);
    }

    // 계약별 바
    const bars = data.items.map((item) => {
      const barStart = item.created_at ?? item.first_markup_at;
      const barEnd = item.latest_markup_at ?? barStart;
      return {
        ...item,
        startOffset: barStart ? daysBetween(start, barStart) : null,
        endOffset: barEnd ? daysBetween(start, barEnd) : null,
      };
    });

    const todayOffset = daysBetween(start, today);
    const targetOffset = data.target_close_date
      ? daysBetween(start, data.target_close_date)
      : null;

    return { start, end, totalDays, monthTicks, bars, todayOffset, targetOffset };
  }, [data, today]);

  if (isLoading) {
    return (
      <div className="space-y-2 p-4">
        <Skeleton className="h-4 w-48" />
        <Skeleton className="h-32 w-full" />
      </div>
    );
  }

  if (!computed || !data || data.items.length === 0) {
    return (
      <div className="flex items-center justify-center py-6">
        <p className="text-xs text-text-muted">Gantt 데이터가 없습니다.</p>
      </div>
    );
  }

  const ROW_HEIGHT = 36;
  const LABEL_WIDTH = 140;
  const CHART_PADDING_TOP = 28;
  const CHART_HEIGHT = CHART_PADDING_TOP + computed.bars.length * ROW_HEIGHT + 16;

  const toX = (dayOffset: number) => `${(dayOffset / computed.totalDays) * 100}%`;

  return (
    <div className="space-y-2">
      {/* Legend */}
      <div className="flex items-center gap-3 px-1 text-[10px] text-text-muted">
        {Object.entries(CONTRACT_COLORS)
          .filter(([type]) => computed.bars.some((b) => b.contract_type === type))
          .map(([type, color]) => (
            <span key={type} className="flex items-center gap-1">
              <span className="h-2.5 w-2.5 rounded-sm" style={{ backgroundColor: color }} />
              {type}
            </span>
          ))}
        {data.target_close_date && (
          <span className="flex items-center gap-1">
            <Flag size={10} className="text-red-500" />
            목표: {formatDate(data.target_close_date)}
          </span>
        )}
        <span className="ml-auto flex items-center gap-1">
          <Calendar size={10} />
          오늘: {formatDate(today)}
        </span>
      </div>

      {/* Chart */}
      <div className="relative overflow-x-auto rounded-lg border border-gray-border bg-white">
        <div className="flex min-w-[600px]">
          {/* Labels */}
          <div className="flex-none" style={{ width: LABEL_WIDTH }}>
            <div style={{ height: CHART_PADDING_TOP }} className="border-b border-gray-border" />
            {computed.bars.map((bar) => (
              <button
                key={bar.contract_id}
                onClick={() => onContractClick(bar.contract_id)}
                className={`flex w-full items-center gap-1.5 border-b border-gray-100 px-3 text-left transition-colors ${
                  selectedContractId === bar.contract_id
                    ? "bg-primary-50"
                    : "hover:bg-gray-50"
                }`}
                style={{ height: ROW_HEIGHT }}
              >
                <span
                  className="h-2 w-2 shrink-0 rounded-sm"
                  style={{ backgroundColor: CONTRACT_COLORS[bar.contract_type] ?? CONTRACT_COLORS.OTHER }}
                />
                <span className="truncate text-xs font-medium text-text-dark">{bar.title}</span>
                {bar.open_issues > 0 && (
                  <Badge variant="error" className="ml-auto text-[9px]">{bar.open_issues}</Badge>
                )}
              </button>
            ))}
          </div>

          {/* Bars Area */}
          <div className="relative flex-1" style={{ height: CHART_HEIGHT }}>
            {/* Month grid */}
            {computed.monthTicks.map((tick) => (
              <div
                key={tick.label}
                className="absolute top-0 border-l border-gray-200"
                style={{ left: toX(tick.offset), height: "100%" }}
              >
                <span className="absolute left-1 text-[9px] text-text-muted whitespace-nowrap" style={{ lineHeight: `${CHART_PADDING_TOP}px` }}>
                  {tick.label}
                </span>
              </div>
            ))}

            {/* Today line */}
            <div
              className="absolute top-0 z-10 w-px bg-blue-500"
              style={{ left: toX(computed.todayOffset), height: "100%" }}
            >
              <span className="absolute -left-3 text-[8px] font-semibold text-blue-600" style={{ lineHeight: `${CHART_PADDING_TOP}px` }}>
                Today
              </span>
            </div>

            {/* Target close date */}
            {computed.targetOffset != null && (
              <div
                className="absolute top-0 z-10"
                style={{
                  left: toX(computed.targetOffset),
                  height: "100%",
                  borderLeft: "2px dashed #BC2C1A",
                }}
              >
                <Diamond className="absolute -left-[5px] h-2.5 w-2.5 fill-red-600 text-red-600" style={{ top: CHART_PADDING_TOP - 6 }} />
              </div>
            )}

            {/* Contract bars */}
            {computed.bars.map((bar, idx) => {
              if (bar.startOffset == null) return null;
              const width = Math.max((bar.endOffset ?? bar.startOffset) - bar.startOffset, 2);
              const y = CHART_PADDING_TOP + idx * ROW_HEIGHT + 8;
              const barHeight = ROW_HEIGHT - 16;
              const color = CONTRACT_COLORS[bar.contract_type] ?? CONTRACT_COLORS.OTHER;

              return (
                <button
                  key={bar.contract_id}
                  onClick={() => onContractClick(bar.contract_id)}
                  className="absolute rounded transition-opacity hover:opacity-80"
                  style={{
                    left: toX(bar.startOffset),
                    width: toX(width),
                    top: y,
                    height: barHeight,
                    backgroundColor: color,
                    minWidth: 6,
                  }}
                  title={`${bar.title} — ${bar.total_markups}회 마크업, ${bar.open_issues}건 미해결`}
                >
                  {/* 마크업 수 표시 */}
                  {bar.total_markups > 0 && width > 20 && (
                    <span className="absolute inset-0 flex items-center justify-center text-[9px] font-bold text-white">
                      {bar.total_markups}
                    </span>
                  )}
                </button>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}
