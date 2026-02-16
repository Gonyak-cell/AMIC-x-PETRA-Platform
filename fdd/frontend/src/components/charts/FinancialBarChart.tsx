import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
  Legend,
} from "recharts";
import { formatCompact } from "@/lib/format";
import { cn } from "@/lib/cn";
import { ChartTooltip } from "./ChartTooltip";
import { CHART_COLORS, CATEGORY_COLORS, getValueColor } from "./chartColors";

export interface BarChartDataPoint {
  name: string;
  value: number;
  displayValue?: string;
  fill?: string;
}

export type ColorScheme = "default" | "positive-negative" | "categorical";

export interface FinancialBarChartProps {
  data: BarChartDataPoint[];
  height?: number;
  showGrid?: boolean;
  showLegend?: boolean;
  currency?: string;
  colorScheme?: ColorScheme;
  orientation?: "vertical" | "horizontal";
  barSize?: number;
  animate?: boolean;
  className?: string;
  "aria-label"?: string;
}

/**
 * FinancialBarChart - 카테고리 비교 차트
 *
 * 용도:
 * - QoE 조정 카테고리별 합계 비교
 * - Peg 시나리오 비교 (LTM Average, TTM, Last Month 등)
 * - 일반적인 카테고리 비교
 */
export function FinancialBarChart({
  data,
  height = 300,
  showGrid = true,
  showLegend = false,
  currency = "KRW",
  colorScheme = "default",
  orientation = "vertical",
  barSize = 40,
  animate = true,
  className,
  "aria-label": ariaLabel,
}: FinancialBarChartProps) {
  const isHorizontal = orientation === "horizontal";

  /**
   * 색상 결정 로직
   */
  const getBarColor = (entry: BarChartDataPoint, index: number): string => {
    // 명시적 fill이 있으면 우선 적용
    if (entry.fill) return entry.fill;

    switch (colorScheme) {
      case "positive-negative":
        return getValueColor(entry.value);
      case "categorical":
        return CATEGORY_COLORS[index % CATEGORY_COLORS.length];
      case "default":
      default:
        return CHART_COLORS.primary;
    }
  };

  // Recharts는 가로 막대 차트를 위해 layout="vertical" 사용
  const chartLayout = isHorizontal ? "vertical" : "horizontal";

  return (
    <div
      className={cn("w-full", className)}
      role="img"
      aria-label={ariaLabel ?? "Financial bar chart"}
    >
      <ResponsiveContainer width="100%" height={height}>
        <BarChart
          data={data}
          layout={chartLayout}
          margin={{ top: 20, right: 30, left: 20, bottom: 5 }}
        >
          {showGrid && (
            <CartesianGrid
              strokeDasharray="3 3"
              stroke={CHART_COLORS.gridColor}
              vertical={!isHorizontal}
              horizontal={isHorizontal}
            />
          )}

          {isHorizontal ? (
            <>
              <XAxis
                type="number"
                tickFormatter={(v) => formatCompact(v)}
                tick={{ fill: CHART_COLORS.axisColor, fontSize: 12 }}
                axisLine={{ stroke: CHART_COLORS.gridColor }}
                tickLine={{ stroke: CHART_COLORS.gridColor }}
              />
              <YAxis
                type="category"
                dataKey="name"
                width={100}
                tick={{ fill: CHART_COLORS.axisColor, fontSize: 12 }}
                axisLine={{ stroke: CHART_COLORS.gridColor }}
                tickLine={false}
              />
            </>
          ) : (
            <>
              <XAxis
                dataKey="name"
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
            </>
          )}

          <Tooltip
            content={<ChartTooltip currency={currency} />}
            cursor={{ fill: "rgba(0, 0, 0, 0.05)" }}
          />

          {showLegend && <Legend />}

          <Bar
            dataKey="value"
            barSize={barSize}
            isAnimationActive={animate}
            animationDuration={500}
            radius={[4, 4, 0, 0]}
          >
            {data.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={getBarColor(entry, index)} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
