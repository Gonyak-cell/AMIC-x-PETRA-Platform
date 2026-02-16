import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
  ReferenceLine,
} from "recharts";
import { formatCompact, formatAmount } from "@/lib/format";
import { cn } from "@/lib/cn";
import { CHART_COLORS, WaterfallItemType, getWaterfallColor } from "./chartColors";

export interface WaterfallDataPoint {
  name: string;
  value: number;
  displayValue?: string;
  type: WaterfallItemType;
}

export interface WaterfallChartProps {
  data: WaterfallDataPoint[];
  height?: number;
  showGrid?: boolean;
  showConnectors?: boolean;
  currency?: string;
  barWidth?: number;
  animate?: boolean;
  className?: string;
  "aria-label"?: string;
}

/**
 * 워터폴 처리된 데이터 구조
 */
interface ProcessedWaterfallData {
  name: string;
  invisibleBase: number;
  visibleValue: number;
  originalValue: number;
  displayValue: string;
  type: WaterfallItemType;
}

/**
 * Stacked Bar + Invisible Base 패턴으로 워터폴 데이터 변환
 */
function processWaterfallData(
  data: WaterfallDataPoint[],
  currency: string
): ProcessedWaterfallData[] {
  let runningTotal = 0;

  return data.map((item) => {
    const processed: ProcessedWaterfallData = {
      name: item.name,
      invisibleBase: 0,
      visibleValue: 0,
      originalValue: item.value,
      displayValue: item.displayValue ?? formatAmount(item.value, currency),
      type: item.type,
    };

    switch (item.type) {
      case "start":
        // 시작값: 바닥에서 시작
        processed.invisibleBase = 0;
        processed.visibleValue = item.value;
        runningTotal = item.value;
        break;

      case "increase":
        // 증가: 이전 합계 위에 쌓기
        processed.invisibleBase = runningTotal;
        processed.visibleValue = item.value;
        runningTotal += item.value;
        break;

      case "decrease": {
        // 감소: 이전 합계에서 아래로 내려옴
        const absValue = Math.abs(item.value);
        processed.invisibleBase = runningTotal - absValue;
        processed.visibleValue = absValue;
        runningTotal -= absValue;
        break;
      }

      case "subtotal":
      case "total":
        // 소계/합계: 바닥에서 현재 합계까지
        processed.invisibleBase = 0;
        processed.visibleValue = runningTotal;
        break;
    }

    return processed;
  });
}

/**
 * WaterfallChart 툴팁
 */
interface WaterfallTooltipProps {
  active?: boolean;
  payload?: Array<{
    payload: ProcessedWaterfallData;
  }>;
  label?: string;
}

function WaterfallTooltip({ active, payload, label }: WaterfallTooltipProps) {
  if (!active || !payload?.length) return null;

  const data = payload[0].payload;
  const color = getWaterfallColor(data.type);

  return (
    <div
      className="bg-white border rounded-lg shadow-card px-3 py-2"
      style={{ borderColor: CHART_COLORS.tooltipBorder }}
    >
      <p className="text-text-dark font-medium text-sm mb-1">{label}</p>
      <div className="flex items-center gap-2">
        <span
          className="w-2.5 h-2.5 rounded-sm flex-shrink-0"
          style={{ backgroundColor: color }}
        />
        <span className="font-mono text-sm text-text-body">
          {data.displayValue}
        </span>
      </div>
    </div>
  );
}

/**
 * WaterfallChart - 브릿지 분석 차트
 *
 * 용도:
 * - EBITDA Bridge: Reported EBITDA → Adjustments → Adjusted EBITDA
 * - Net Debt Bridge: Gross Debt → Cash → Net Debt → Debt-Like → Adjusted Net Debt
 *
 * 구현 패턴: Stacked Bar + Invisible Base
 * - invisibleBase: 투명 바 (위치 조정용)
 * - visibleValue: 실제 보이는 바
 */
export function WaterfallChart({
  data,
  height = 400,
  showGrid = true,
  showConnectors = true,
  currency = "KRW",
  barWidth = 60,
  animate = true,
  className,
  "aria-label": ariaLabel,
}: WaterfallChartProps) {
  const processedData = processWaterfallData(data, currency);

  return (
    <div
      className={cn("w-full", className)}
      role="img"
      aria-label={ariaLabel ?? "Waterfall bridge chart"}
    >
      <ResponsiveContainer width="100%" height={height}>
        <BarChart
          data={processedData}
          margin={{ top: 20, right: 30, left: 20, bottom: 40 }}
        >
          {showGrid && (
            <CartesianGrid
              strokeDasharray="3 3"
              stroke={CHART_COLORS.gridColor}
              vertical={false}
            />
          )}

          <XAxis
            dataKey="name"
            tick={{ fill: CHART_COLORS.axisColor, fontSize: 11 }}
            axisLine={{ stroke: CHART_COLORS.gridColor }}
            tickLine={false}
            interval={0}
            angle={-20}
            textAnchor="end"
            height={60}
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

          {/* 0선 표시 */}
          {showConnectors && (
            <ReferenceLine y={0} stroke={CHART_COLORS.axisColor} />
          )}

          <Tooltip content={<WaterfallTooltip />} cursor={false} />

          {/* 투명 베이스 바 (스택 하단) */}
          <Bar
            dataKey="invisibleBase"
            stackId="waterfall"
            fill="transparent"
            isAnimationActive={false}
          />

          {/* 실제 보이는 바 (스택 상단) */}
          <Bar
            dataKey="visibleValue"
            stackId="waterfall"
            barSize={barWidth}
            isAnimationActive={animate}
            animationDuration={500}
            radius={[4, 4, 0, 0]}
          >
            {processedData.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={getWaterfallColor(entry.type)} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

// ─────────────────────────────────────────────────────────
// 데이터 변환 헬퍼 (페이지에서 사용)
// ─────────────────────────────────────────────────────────

/**
 * QoE 데이터 → Waterfall 변환
 */
export function transformQoEToWaterfall(
  reportedEbitda: number | string,
  adjustments: Array<{
    description: string;
    amount: number | string;
    status: string;
  }>,
  adjustedEbitda: number | string
): WaterfallDataPoint[] {
  const approved = adjustments.filter((a) => a.status === "APPROVED");

  return [
    {
      name: "Reported EBITDA",
      value: Number(reportedEbitda),
      type: "start",
    },
    ...approved.map((adj) => {
      const amount = Number(adj.amount);
      return {
        name: adj.description.length > 15 ? adj.description.slice(0, 15) + "..." : adj.description,
        value: amount,
        type: (amount >= 0 ? "increase" : "decrease") as WaterfallItemType,
      };
    }),
    {
      name: "Adjusted EBITDA",
      value: Number(adjustedEbitda),
      type: "total",
    },
  ];
}

/**
 * Net Debt 데이터 → Waterfall 변환
 */
export function transformNetDebtToWaterfall(
  grossDebt: number | string,
  cash: number | string,
  netDebt: number | string,
  debtLikeItems?: Array<{ name: string; amount: number | string }>,
  adjustedNetDebt?: number | string
): WaterfallDataPoint[] {
  const result: WaterfallDataPoint[] = [
    {
      name: "Gross Debt",
      value: Number(grossDebt),
      type: "start",
    },
    {
      name: "Cash & Equivalents",
      value: -Math.abs(Number(cash)), // 현금은 부채에서 차감
      type: "decrease",
    },
    {
      name: "Net Debt",
      value: Number(netDebt),
      type: "subtotal",
    },
  ];

  // Debt-like 항목 추가
  if (debtLikeItems && debtLikeItems.length > 0) {
    debtLikeItems.forEach((item) => {
      const amount = Number(item.amount);
      result.push({
        name: item.name.length > 15 ? item.name.slice(0, 15) + "..." : item.name,
        value: amount,
        type: amount >= 0 ? "increase" : "decrease",
      });
    });

    if (adjustedNetDebt !== undefined) {
      result.push({
        name: "Adjusted Net Debt",
        value: Number(adjustedNetDebt),
        type: "total",
      });
    }
  }

  return result;
}
