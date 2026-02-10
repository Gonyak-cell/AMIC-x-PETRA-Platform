import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
  Area,
  ComposedChart,
  Legend,
} from "recharts";
import { formatCompact, formatDate } from "@/lib/format";
import { cn } from "@/lib/cn";
import { ChartTooltip } from "./ChartTooltip";
import { CHART_COLORS } from "./chartColors";

export interface TrendDataPoint {
  period: string;
  value: number;
  displayValue?: string;
  secondary?: number;
  secondaryDisplay?: string;
}

export interface TrendLineChartProps {
  data: TrendDataPoint[];
  height?: number;
  showGrid?: boolean;
  showDots?: boolean;
  showArea?: boolean;
  currency?: string;
  /** 목표선 (예: Target NWC) */
  target?: number;
  targetLabel?: string;
  lineColor?: string;
  secondaryLineColor?: string;
  /** 보조 라인 레이블 */
  secondaryLabel?: string;
  animate?: boolean;
  className?: string;
  "aria-label"?: string;
}

/**
 * TrendLineChart - 시계열 추이 차트
 *
 * 용도:
 * - NWC 월별 추이 시각화 (monthly_trend)
 * - Current Assets, Current Liabilities, NWC 다중 라인
 */
export function TrendLineChart({
  data,
  height = 300,
  showGrid = true,
  showDots = true,
  showArea = false,
  currency = "KRW",
  target,
  targetLabel,
  lineColor = CHART_COLORS.primary,
  secondaryLineColor = CHART_COLORS.positive,
  secondaryLabel,
  animate = true,
  className,
  "aria-label": ariaLabel,
}: TrendLineChartProps) {
  // 보조 데이터가 있는지 확인
  const hasSecondary = data.some((d) => d.secondary !== undefined);

  // 기간 포맷터
  const formatPeriod = (period: string) => {
    // YYYY-MM 형식이면 월별 포맷 적용
    if (/^\d{4}-\d{2}$/.test(period)) {
      return formatDate(period + "-01", "month");
    }
    return period;
  };

  // 영역 채우기 사용 시 ComposedChart 사용
  const ChartComponent = showArea ? ComposedChart : LineChart;

  return (
    <div
      className={cn("w-full", className)}
      role="img"
      aria-label={ariaLabel ?? "Trend line chart"}
    >
      <ResponsiveContainer width="100%" height={height}>
        <ChartComponent
          data={data}
          margin={{ top: 20, right: 30, left: 20, bottom: 5 }}
        >
          {showGrid && (
            <CartesianGrid
              strokeDasharray="3 3"
              stroke={CHART_COLORS.gridColor}
            />
          )}

          <XAxis
            dataKey="period"
            tickFormatter={formatPeriod}
            tick={{ fill: CHART_COLORS.axisColor, fontSize: 12 }}
            axisLine={{ stroke: CHART_COLORS.gridColor }}
            tickLine={false}
          />

          <YAxis
            tickFormatter={(v) => formatCompact(v)}
            tick={{
              fill: CHART_COLORS.axisColor,
              fontSize: 12,
              fontFamily: "'IBM Plex Mono', monospace",
            }}
            axisLine={{ stroke: CHART_COLORS.gridColor }}
            tickLine={{ stroke: CHART_COLORS.gridColor }}
          />

          <Tooltip
            content={<ChartTooltip currency={currency} />}
            cursor={{ stroke: CHART_COLORS.gridColor, strokeDasharray: "3 3" }}
          />

          {(hasSecondary || target !== undefined) && (
            <Legend
              wrapperStyle={{ fontSize: 12, color: CHART_COLORS.axisColor }}
            />
          )}

          {/* 목표선 (Reference Line) */}
          {target !== undefined && (
            <ReferenceLine
              y={target}
              stroke={CHART_COLORS.caution}
              strokeDasharray="5 5"
              strokeWidth={2}
              label={{
                value: targetLabel ?? `Target: ${formatCompact(target)}`,
                position: "insideTopRight",
                fill: CHART_COLORS.caution,
                fontSize: 11,
              }}
            />
          )}

          {/* 영역 채우기 (선택) */}
          {showArea && (
            <Area
              type="monotone"
              dataKey="value"
              stroke={lineColor}
              fill={lineColor}
              fillOpacity={0.1}
              isAnimationActive={animate}
            />
          )}

          {/* 주요 라인 */}
          <Line
            type="monotone"
            dataKey="value"
            name="Value"
            stroke={lineColor}
            strokeWidth={2}
            dot={
              showDots
                ? {
                    fill: lineColor,
                    stroke: "#fff",
                    strokeWidth: 2,
                    r: 4,
                  }
                : false
            }
            activeDot={{
              r: 6,
              fill: lineColor,
              stroke: "#fff",
              strokeWidth: 2,
            }}
            isAnimationActive={animate}
            animationDuration={500}
          />

          {/* 보조 라인 */}
          {hasSecondary && (
            <Line
              type="monotone"
              dataKey="secondary"
              name={secondaryLabel ?? "Secondary"}
              stroke={secondaryLineColor}
              strokeWidth={2}
              strokeDasharray="5 5"
              dot={
                showDots
                  ? {
                      fill: secondaryLineColor,
                      stroke: "#fff",
                      strokeWidth: 2,
                      r: 3,
                    }
                  : false
              }
              isAnimationActive={animate}
              animationDuration={500}
            />
          )}
        </ChartComponent>
      </ResponsiveContainer>
    </div>
  );
}
