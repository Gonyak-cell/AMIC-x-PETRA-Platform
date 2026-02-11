import { TrendLineChart } from "@/components/charts";
import type { YearlyTrend } from "@/modules/kiis/types/deal";
import { formatCompact } from "@/lib/format";

interface DealTrendChartProps {
  data: YearlyTrend[];
  height?: number;
}

export default function DealTrendChart({
  data,
  height = 300,
}: DealTrendChartProps) {
  const chartData = data.map((d) => ({
    period: String(d.year),
    value: d.deal_count,
    secondary: d.total_amount != null ? Number(d.total_amount) : undefined,
    displayValue: `${d.deal_count} deals / ${formatCompact(d.total_amount)}`,
  }));

  return (
    <TrendLineChart
      data={chartData}
      height={height}
      secondaryLabel="Total Amount"
    />
  );
}
