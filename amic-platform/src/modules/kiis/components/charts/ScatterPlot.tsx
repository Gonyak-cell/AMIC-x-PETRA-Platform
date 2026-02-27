import {
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  ZAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
} from "recharts";
import { cn } from "@/lib/cn";
import { CHART_COLORS, CATEGORY_COLORS } from "@/components/charts/chartColors";
import type { IRRScatterPoint } from "@/modules/kiis/types/gpResearch";

interface ScatterPlotProps {
  data: IRRScatterPoint[];
  height?: number;
  className?: string;
  "aria-label"?: string;
}

export function ScatterPlot({
  data,
  height = 280,
  className,
  "aria-label": ariaLabel,
}: ScatterPlotProps) {
  const avgIrr =
    data.length > 0
      ? data.reduce((sum, d) => sum + d.grossIrr, 0) / data.length
      : 0;

  return (
    <div
      className={cn("w-full", className)}
      role="img"
      aria-label={ariaLabel ?? "개별 펀드 Gross IRR 산점도"}
    >
      <ResponsiveContainer width="100%" height={height}>
        <ScatterChart margin={{ top: 8, right: 16, bottom: 0, left: 0 }}>
          <CartesianGrid
            strokeDasharray="3 3"
            stroke={CHART_COLORS.gridColor}
          />
          <XAxis
            dataKey="fundSize"
            name="펀드 규모"
            unit="억"
            tick={{ fontSize: 11, fill: CHART_COLORS.axisColor }}
            tickLine={false}
            axisLine={{ stroke: CHART_COLORS.gridColor }}
            label={{
              value: "펀드 규모 (억 원)",
              position: "insideBottom",
              offset: -2,
              style: { fontSize: 11, fill: CHART_COLORS.axisColor },
            }}
          />
          <YAxis
            dataKey="grossIrr"
            name="Gross IRR"
            unit="%"
            tick={{ fontSize: 11, fill: CHART_COLORS.axisColor }}
            tickLine={false}
            axisLine={false}
            label={{
              value: "Gross IRR (%)",
              angle: -90,
              position: "insideLeft",
              offset: 10,
              style: { fontSize: 11, fill: CHART_COLORS.axisColor },
            }}
          />
          <ZAxis dataKey="vintage" range={[80, 200]} name="Vintage" />
          <ReferenceLine
            y={avgIrr}
            stroke={CHART_COLORS.caution}
            strokeDasharray="4 4"
            strokeWidth={1.5}
            label={{
              value: `Avg ${avgIrr.toFixed(1)}%`,
              position: "right",
              style: { fontSize: 11, fill: CHART_COLORS.caution },
            }}
          />
          <Tooltip
            contentStyle={{
              background: CHART_COLORS.tooltipBg,
              border: `1px solid ${CHART_COLORS.tooltipBorder}`,
              borderRadius: 8,
              fontSize: 13,
            }}
            formatter={(value: number, name: string) => {
              if (name === "Gross IRR") return [`${value.toFixed(1)}%`, name];
              if (name === "펀드 규모")
                return [`${value.toLocaleString()}억`, name];
              return [value, name];
            }}
            labelFormatter={(
              _: unknown,
              payload: Array<{ payload?: IRRScatterPoint }>,
            ) => {
              const item = payload?.[0]?.payload;
              return item ? `${item.fundName} (${item.vintage})` : "";
            }}
          />
          <Scatter
            data={data}
            fill={CATEGORY_COLORS[2]}
            fillOpacity={0.8}
            strokeWidth={1}
            stroke={CATEGORY_COLORS[0]}
          />
        </ScatterChart>
      </ResponsiveContainer>
    </div>
  );
}
