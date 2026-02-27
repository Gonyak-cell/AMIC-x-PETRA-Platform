import {
  ComposedChart,
  Bar,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import { cn } from "@/lib/cn";
import { formatCompact } from "@/lib/format";
import { CHART_COLORS, CATEGORY_COLORS } from "@/components/charts/chartColors";
import type { FundHistoryPoint } from "@/modules/kiis/types/gpResearch";

interface ComboChartProps {
  data: FundHistoryPoint[];
  height?: number;
  barLabel?: string;
  lineLabel?: string;
  className?: string;
  "aria-label"?: string;
}

export function ComboChart({
  data,
  height = 300,
  barLabel = "결성액 (억)",
  lineLabel = "누적 AUM (억)",
  className,
  "aria-label": ariaLabel,
}: ComboChartProps) {
  return (
    <div
      className={cn("w-full", className)}
      role="img"
      aria-label={ariaLabel ?? "연도별 펀드 결성액 및 누적 AUM 추이"}
    >
      <ResponsiveContainer width="100%" height={height}>
        <ComposedChart
          data={data}
          margin={{ top: 8, right: 16, bottom: 0, left: 0 }}
        >
          <CartesianGrid
            strokeDasharray="3 3"
            stroke={CHART_COLORS.gridColor}
            vertical={false}
          />
          <XAxis
            dataKey="year"
            tick={{ fontSize: 12, fill: CHART_COLORS.axisColor }}
            tickLine={false}
            axisLine={{ stroke: CHART_COLORS.gridColor }}
          />
          <YAxis
            yAxisId="bar"
            orientation="left"
            tick={{ fontSize: 11, fill: CHART_COLORS.axisColor }}
            tickLine={false}
            axisLine={false}
            tickFormatter={(v: number) => formatCompact(v)}
          />
          <YAxis
            yAxisId="line"
            orientation="right"
            tick={{ fontSize: 11, fill: CHART_COLORS.axisColor }}
            tickLine={false}
            axisLine={false}
            tickFormatter={(v: number) => formatCompact(v)}
          />
          <Tooltip
            contentStyle={{
              background: CHART_COLORS.tooltipBg,
              border: `1px solid ${CHART_COLORS.tooltipBorder}`,
              borderRadius: 8,
              fontSize: 13,
            }}
            formatter={(value: number, name: string) => [
              `${value.toLocaleString()}억`,
              name,
            ]}
          />
          <Legend wrapperStyle={{ fontSize: 12, paddingTop: 8 }} />
          <Bar
            yAxisId="bar"
            dataKey="commitAmount"
            name={barLabel}
            fill={CATEGORY_COLORS[0]}
            radius={[4, 4, 0, 0]}
            barSize={32}
          />
          <Line
            yAxisId="line"
            type="monotone"
            dataKey="cumAum"
            name={lineLabel}
            stroke={CATEGORY_COLORS[1]}
            strokeWidth={2.5}
            dot={{ r: 4, fill: CATEGORY_COLORS[1], strokeWidth: 0 }}
            activeDot={{ r: 6 }}
          />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}
