import {
  PieChart,
  Pie,
  Cell,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";
import { cn } from "@/lib/cn";
import { CHART_COLORS, CATEGORY_COLORS } from "@/components/charts/chartColors";
import type { SectorAllocationPoint } from "@/modules/kiis/types/gpResearch";

const DONUT_COLORS = [
  CATEGORY_COLORS[0], // amic
  CATEGORY_COLORS[1], // accent
  CATEGORY_COLORS[2], // blue
  CATEGORY_COLORS[3], // caution
  CATEGORY_COLORS[4], // secondary
  "#8B5CF6", // purple
  "#EC4899", // pink
];

interface DonutChartProps {
  data: SectorAllocationPoint[];
  height?: number;
  className?: string;
  "aria-label"?: string;
}

export function DonutChart({
  data,
  height = 300,
  className,
  "aria-label": ariaLabel,
}: DonutChartProps) {
  const total = data.reduce((sum, d) => sum + d.value, 0);

  return (
    <div
      className={cn("w-full", className)}
      role="img"
      aria-label={ariaLabel ?? "섹터별 투자 비중 차트"}
    >
      <ResponsiveContainer width="100%" height={height}>
        <PieChart>
          <Pie
            data={data}
            cx="50%"
            cy="50%"
            innerRadius={65}
            outerRadius={100}
            dataKey="value"
            nameKey="sector"
            paddingAngle={2}
            stroke="none"
          >
            {data.map((_, index) => (
              <Cell
                key={`cell-${index}`}
                fill={DONUT_COLORS[index % DONUT_COLORS.length]}
              />
            ))}
          </Pie>
          {/* 중앙 라벨 */}
          <text
            x="50%"
            y="48%"
            textAnchor="middle"
            dominantBaseline="central"
            className="fill-text-dark"
            style={{ fontSize: 20, fontWeight: 700 }}
          >
            {total >= 10000
              ? `${(total / 10000).toFixed(1)}조`
              : `${total.toLocaleString()}억`}
          </text>
          <text
            x="50%"
            y="58%"
            textAnchor="middle"
            dominantBaseline="central"
            className="fill-text-secondary"
            style={{ fontSize: 11 }}
          >
            Total AUM
          </text>
          <Tooltip
            contentStyle={{
              background: CHART_COLORS.tooltipBg,
              border: `1px solid ${CHART_COLORS.tooltipBorder}`,
              borderRadius: 8,
              fontSize: 13,
            }}
            formatter={(value: number | undefined) => [
              `${(value ?? 0).toLocaleString()}억 (${(((value ?? 0) / total) * 100).toFixed(1)}%)`,
              "투자 금액",
            ]}
          />
          <Legend
            layout="vertical"
            align="right"
            verticalAlign="middle"
            wrapperStyle={{ fontSize: 12, lineHeight: "22px" }}
            formatter={(value: string) => (
              <span className="text-text-body text-xs">{value}</span>
            )}
          />
        </PieChart>
      </ResponsiveContainer>
    </div>
  );
}
