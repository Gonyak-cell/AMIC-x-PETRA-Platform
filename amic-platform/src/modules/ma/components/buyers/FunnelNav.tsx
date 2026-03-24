import { cn } from "@/lib/cn";

export type FunnelStepId = "long-list" | "nda" | "short-list" | "im" | "dd";

export interface FunnelStep {
  id: FunnelStepId;
  label: string;
  count: number;
  clickable: boolean;
}

interface FunnelNavProps {
  steps: FunnelStep[];
  activeStep: FunnelStepId;
  onStepChange: (step: FunnelStepId) => void;
}

export default function FunnelNav({
  steps,
  activeStep,
  onStepChange,
}: FunnelNavProps) {
  return (
    <div
      className="flex items-end gap-1 overflow-x-auto border-b border-gray-200 font-body"
      role="tablist"
      aria-label="매수자 퍼널 네비게이션"
    >
      {steps.map((step, idx) => {
        const isActive = step.id === activeStep;
        const isDisabled = !step.clickable;

        return (
          <div key={step.id} className="flex items-end">
            {idx > 0 && (
              <div className="mb-4 h-px w-6 flex-shrink-0 bg-gray-200" />
            )}

            <button
              type="button"
              role="tab"
              aria-selected={isActive}
              aria-disabled={isDisabled}
              tabIndex={isDisabled ? -1 : 0}
              onClick={() => {
                if (step.clickable) {
                  onStepChange(step.id);
                }
              }}
              className={cn(
                "flex min-w-[72px] flex-col items-center gap-0.5 border-b-2 px-4 py-2 transition-all -mb-px",
                isActive
                  ? "border-accent font-medium text-accent"
                  : "border-transparent",
                step.clickable
                  ? "cursor-pointer hover:bg-gray-50 hover:text-accent"
                  : "cursor-default opacity-50",
              )}
            >
              <span className="text-lg font-bold leading-tight tabular-nums">
                {step.count}
              </span>
              <span className="whitespace-nowrap text-xs">{step.label}</span>
            </button>
          </div>
        );
      })}
    </div>
  );
}
