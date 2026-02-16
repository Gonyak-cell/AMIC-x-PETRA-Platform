/**
 * AMIC 스타일 차트 컬러 팔레트
 * Tailwind config와 일치하는 색상 상수
 */
export const CHART_COLORS = {
  // Primary
  primary: "#0F3A32", // amic (dark teal)
  primaryLight: "#0B2D27", // amic-700

  // Semantic (Waterfall)
  positive: "#26C260", // 증가, add-back (accent green)
  negative: "#BC2C1A", // 감소, deduction (red)
  caution: "#EF6C00", // 경고, pending (amber)

  // Waterfall Specific
  waterfallTotal: "#0F3A32", // 시작/종료 합계
  waterfallIncrease: "#26C260", // Add-backs
  waterfallDecrease: "#BC2C1A", // Deductions
  waterfallIntermediate: "#F4F6F8", // 중간 소계

  // Grid & Axis
  gridColor: "#E0E0E0", // gray-border
  axisColor: "#777777", // text-secondary

  // Tooltip
  tooltipBg: "#FFFFFF",
  tooltipBorder: "#E0E0E0",
} as const;

/**
 * 다중 카테고리용 색상 배열
 * 순서대로 할당됨
 */
export const CATEGORY_COLORS = [
  "#0F3A32", // amic
  "#26C260", // accent
  "#0091DA", // info blue
  "#EF6C00", // caution
  "#777777", // secondary
] as const;

/**
 * WaterfallItemType에 따른 색상 반환
 */
export type WaterfallItemType =
  | "start"
  | "increase"
  | "decrease"
  | "subtotal"
  | "total";

export function getWaterfallColor(type: WaterfallItemType): string {
  switch (type) {
    case "start":
    case "total":
      return CHART_COLORS.waterfallTotal;
    case "increase":
      return CHART_COLORS.waterfallIncrease;
    case "decrease":
      return CHART_COLORS.waterfallDecrease;
    case "subtotal":
      return CHART_COLORS.waterfallIntermediate;
    default:
      return CHART_COLORS.primary;
  }
}

/**
 * 값의 부호에 따른 색상 반환
 */
export function getValueColor(value: number): string {
  if (value > 0) return CHART_COLORS.positive;
  if (value < 0) return CHART_COLORS.negative;
  return CHART_COLORS.axisColor;
}
