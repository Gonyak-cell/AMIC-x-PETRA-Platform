/**
 * Chart Components Barrel Export
 *
 * AMIC x PETRA Platform 스타일 Recharts 기반 차트 컴포넌트
 */

// Colors & Constants
export {
  CHART_COLORS,
  CATEGORY_COLORS,
  getWaterfallColor,
  getValueColor,
  type WaterfallItemType,
} from "./chartColors";

// Common Components
export { ChartTooltip, type ChartTooltipProps } from "./ChartTooltip";

// Chart Components
export {
  FinancialBarChart,
  type FinancialBarChartProps,
  type BarChartDataPoint,
  type ColorScheme,
} from "./FinancialBarChart";

export {
  TrendLineChart,
  type TrendLineChartProps,
  type TrendDataPoint,
} from "./TrendLineChart";

export {
  WaterfallChart,
  type WaterfallChartProps,
  type WaterfallDataPoint,
  transformQoEToWaterfall,
  transformNetDebtToWaterfall,
} from "./WaterfallChart";
