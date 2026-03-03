/**
 * AMIC x PETRA Excalidraw 브랜드 팔레트
 *
 * Excalidraw 다이어그램에서 사용하는 AMIC 브랜드 색상 정의.
 * chart_engine/config.py ChartColorConfig와 동일한 색상 체계.
 */

/** 시맨틱 목적별 fill/stroke 쌍 */
export const AMIC_EXCALIDRAW_PALETTE = {
  primary: { fill: "#E6FDD6", stroke: "#0F3A32" },
  secondary: { fill: "#d1fae5", stroke: "#1C8F57" },
  accent: { fill: "#bbf7d0", stroke: "#26C260" },
  fresh: { fill: "#f0fdf4", stroke: "#A3E96B" },
  caution: { fill: "#fef3c7", stroke: "#EF6C00" },
  negative: { fill: "#fecaca", stroke: "#BC2C1A" },
  neutral: { fill: "#F4F6F8", stroke: "#6B7280" },
  info: { fill: "#dbeafe", stroke: "#0091DA" },
} as const;

/** 텍스트 계층 색상 */
export const AMIC_TEXT_COLORS = {
  title: "#0F3A32",
  subtitle: "#1C8F57",
  body: "#374151",
  secondary: "#6B7280",
  onDark: "#FFFFFF",
  onLight: "#0F3A32",
} as const;

/** 라인/화살표 색상 */
export const AMIC_LINE_COLORS = {
  primary: "#0F3A32",
  secondary: "#6B7280",
  accent: "#26C260",
  majorStake: "#0F3A32",
  minorStake: "#9CA3AF",
} as const;

/** 캔버스 배경 */
export const EXCALIDRAW_BG = "#ffffff" as const;

/** 엔티티 타입별 색상 매핑 (주주관계도, 거래구조도) */
export const ENTITY_COLORS = {
  company: AMIC_EXCALIDRAW_PALETTE.primary,
  person: AMIC_EXCALIDRAW_PALETTE.secondary,
  fund: AMIC_EXCALIDRAW_PALETTE.accent,
  buyer: AMIC_EXCALIDRAW_PALETTE.info,
  seller: AMIC_EXCALIDRAW_PALETTE.caution,
  target: AMIC_EXCALIDRAW_PALETTE.primary,
  spv: AMIC_EXCALIDRAW_PALETTE.neutral,
} as const;

export type EntityType = keyof typeof ENTITY_COLORS;
