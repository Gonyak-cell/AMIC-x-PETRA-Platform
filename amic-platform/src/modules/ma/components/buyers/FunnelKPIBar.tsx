import { useMemo } from "react";
import type { BuyerCandidate } from "@/modules/ma/types/buyer";
import {
  FUNNEL_NDA_AND_AFTER,
  FUNNEL_CIM_AND_AFTER,
  FUNNEL_DD_AND_AFTER,
} from "@/modules/ma/constants";

interface FunnelKPIBarProps {
  buyers: BuyerCandidate[];
}

export default function FunnelKPIBar({ buyers }: FunnelKPIBarProps) {
  const steps = useMemo(() => {
    let shortList = 0;
    let nda = 0;
    let cim = 0;
    let dd = 0;
    for (const b of buyers) {
      if (b.is_short_listed) shortList++;
      if (FUNNEL_NDA_AND_AFTER.has(b.status)) nda++;
      if (FUNNEL_CIM_AND_AFTER.has(b.status)) cim++;
      if (FUNNEL_DD_AND_AFTER.has(b.status)) dd++;
    }
    return [
      { label: "Long List", count: buyers.length },
      { label: "Short List", count: shortList },
      { label: "NDA 체결", count: nda },
      { label: "IM 발송", count: cim },
      { label: "DD 진행", count: dd },
    ];
  }, [buyers]);

  return (
    <div className="flex items-center gap-1 font-body overflow-x-auto" role="group" aria-label="매수자 퍼널 현황">
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
                aria-label={`${step.label} ${step.count}명`}
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
                <span className="text-[10px] text-text-secondary" aria-label={`전환율 ${rate}%`}>{rate}%</span>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}
