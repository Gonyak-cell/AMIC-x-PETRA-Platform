import { formatAmount } from "@/lib/format";
import { CHART_COLORS } from "./chartColors";

interface TooltipPayloadItem {
  name: string;
  value: number;
  color?: string;
  dataKey?: string;
  payload: Record<string, unknown>;
}

export interface ChartTooltipProps {
  active?: boolean;
  payload?: TooltipPayloadItem[];
  label?: string;
  currency?: string;
  /** Custom value formatter */
  valueFormatter?: (value: number) => string;
}

/**
 * 공통 차트 툴팁 컴포넌트
 * Recharts의 <Tooltip content={<ChartTooltip />} /> 형태로 사용
 */
export function ChartTooltip({
  active,
  payload,
  label,
  currency = "KRW",
  valueFormatter,
}: ChartTooltipProps) {
  if (!active || !payload?.length) return null;

  const format = valueFormatter ?? ((v: number) => formatAmount(v, currency));

  return (
    <div
      className="bg-white border rounded-lg shadow-card px-3 py-2"
      style={{ borderColor: CHART_COLORS.tooltipBorder }}
    >
      {label && (
        <p className="text-text-dark font-medium text-sm mb-1">{label}</p>
      )}
      {payload.map((entry, index) => {
        // displayValue가 있으면 우선 사용
        const displayValue =
          (entry.payload.displayValue as string) ?? format(entry.value);

        return (
          <div key={index} className="flex items-center gap-2">
            {entry.color && (
              <span
                className="w-2.5 h-2.5 rounded-sm flex-shrink-0"
                style={{ backgroundColor: entry.color }}
              />
            )}
            <span className="font-mono text-sm text-text-body">
              {displayValue}
            </span>
          </div>
        );
      })}
    </div>
  );
}
