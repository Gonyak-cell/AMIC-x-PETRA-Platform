import { useMemo } from "react";
import { cn } from "@/lib/cn";
import type { BuyerCandidate } from "@/modules/ma/types/buyer";
import {
  FUNNEL_NDA_AND_AFTER,
  FUNNEL_CIM_AND_AFTER,
  FUNNEL_DD_AND_AFTER,
  isShortListed,
} from "@/modules/ma/constants";

interface FunnelNavProps {
  buyers: BuyerCandidate[];
  activeStep: "long-list" | "short-list";
  onStepChange: (step: "long-list" | "short-list") => void;
}

type StepId = "long-list" | "short-list" | "nda" | "im" | "dd";

interface FunnelStep {
  id: StepId;
  label: string;
  count: number;
  clickable: boolean;
}

export default function FunnelNav({
  buyers,
  activeStep,
  onStepChange,
}: FunnelNavProps) {
  const steps = useMemo((): FunnelStep[] => {
    let shortList = 0;
    let nda = 0;
    let cim = 0;
    let dd = 0;
    for (const b of buyers) {
      if (isShortListed(b)) shortList++;
      if (FUNNEL_NDA_AND_AFTER.has(b.status)) nda++;
      if (FUNNEL_CIM_AND_AFTER.has(b.status)) cim++;
      if (FUNNEL_DD_AND_AFTER.has(b.status)) dd++;
    }
    return [
      {
        id: "long-list",
        label: "Long List",
        count: buyers.length,
        clickable: true,
      },
      {
        id: "short-list",
        label: "Short List",
        count: shortList,
        clickable: true,
      },
      { id: "nda", label: "NDA 체결", count: nda, clickable: false },
      { id: "im", label: "IM 발송", count: cim, clickable: false },
      { id: "dd", label: "DD 진행", count: dd, clickable: false },
    ];
  }, [buyers]);

  return (
    <div
      className="flex items-end gap-1 font-body overflow-x-auto border-b border-gray-200"
      role="tablist"
      aria-label="매수자 퍼널 네비게이션"
    >
      {steps.map((step, idx) => {
        const isActive =
          step.id === activeStep &&
          (step.id === "long-list" || step.id === "short-list");
        const isDisabled = !step.clickable;

        return (
          <div key={step.id} className="flex items-end">
            {/* 연결선 */}
            {idx > 0 && (
              <div className="h-px w-6 bg-gray-200 mb-4 flex-shrink-0" />
            )}

            {/* 단계 탭 */}
            <button
              type="button"
              role="tab"
              aria-selected={isActive}
              aria-disabled={isDisabled}
              tabIndex={isDisabled ? -1 : 0}
              onClick={() => {
                if (
                  step.clickable &&
                  (step.id === "long-list" || step.id === "short-list")
                ) {
                  onStepChange(step.id);
                }
              }}
              className={cn(
                "flex flex-col items-center gap-0.5 px-4 py-2 min-w-[72px] transition-all border-b-2 -mb-px",
                isActive
                  ? "border-accent text-accent font-medium"
                  : "border-transparent",
                step.clickable
                  ? "cursor-pointer hover:bg-gray-50 hover:text-accent"
                  : "cursor-default opacity-50",
              )}
            >
              <span className="text-lg font-bold leading-tight tabular-nums">
                {step.count}
              </span>
              <span className="text-xs whitespace-nowrap">{step.label}</span>
            </button>
          </div>
        );
      })}
    </div>
  );
}
