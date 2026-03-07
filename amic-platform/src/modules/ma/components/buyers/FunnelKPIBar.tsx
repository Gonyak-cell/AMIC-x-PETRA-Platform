import type { BuyerCandidate } from "@/modules/ma/types/buyer";

interface FunnelKPIBarProps {
  buyers: BuyerCandidate[];
}

const NDA_AND_AFTER = new Set([
  "NDA_SIGNED",
  "CIM_SENT",
  "INTEREST_CONFIRMED",
  "IOI_RECEIVED",
  "IOI_ACCEPTED",
  "DD_GRANTED",
  "DD_IN_PROGRESS",
  "LOI_RECEIVED",
  "LOI_ACCEPTED",
  "SELECTED",
  "BID_SUBMITTED",
]);

const CIM_AND_AFTER = new Set([
  "CIM_SENT",
  "INTEREST_CONFIRMED",
  "IOI_RECEIVED",
  "IOI_ACCEPTED",
  "DD_GRANTED",
  "DD_IN_PROGRESS",
  "LOI_RECEIVED",
  "LOI_ACCEPTED",
  "SELECTED",
  "BID_SUBMITTED",
]);

const DD_STATUSES = new Set([
  "DD_GRANTED",
  "DD_IN_PROGRESS",
  "LOI_RECEIVED",
  "LOI_ACCEPTED",
  "SELECTED",
]);

export default function FunnelKPIBar({ buyers }: FunnelKPIBarProps) {
  const steps = [
    {
      label: "Long List",
      count: buyers.length,
    },
    {
      label: "Short List",
      count: buyers.filter((b) => b.is_short_listed).length,
    },
    {
      label: "NDA 체결",
      count: buyers.filter((b) => NDA_AND_AFTER.has(b.status)).length,
    },
    {
      label: "IM 발송",
      count: buyers.filter((b) => CIM_AND_AFTER.has(b.status)).length,
    },
    {
      label: "DD 진행",
      count: buyers.filter((b) => DD_STATUSES.has(b.status)).length,
    },
  ];

  return (
    <div className="flex items-center gap-1 font-body">
      {steps.map((step, idx) => {
        const prev = idx > 0 ? steps[idx - 1].count : null;
        const rate =
          prev != null && prev > 0
            ? Math.round((step.count / prev) * 100)
            : null;
        const active = step.count > 0;

        return (
          <div key={step.label} className="flex items-center gap-1">
            {/* 연결선 (첫 번째 제외) */}
            {idx > 0 && <div className="h-px w-8 bg-gray-200" />}

            {/* 단계 */}
            <div className="flex flex-col items-center gap-1 min-w-[64px]">
              {/* 원형 숫자 */}
              <div
                className={`flex items-center justify-center w-9 h-9 rounded-full text-sm font-semibold ${
                  active
                    ? "bg-accent text-white"
                    : "bg-gray-100 text-text-muted"
                }`}
              >
                {step.count}
              </div>

              {/* 라벨 */}
              <span
                className={`text-xs whitespace-nowrap ${
                  active ? "text-text-body font-medium" : "text-text-muted"
                }`}
              >
                {step.label}
              </span>

              {/* 전환율 (Short List 제외 — 패널 내부에 표시) */}
              {rate != null && step.label !== "Short List" && (
                <span className="text-[10px] text-text-secondary">{rate}%</span>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}
