import { Check } from "lucide-react";
import { MARKETING_STAGES, MARKETING_STAGE_LABELS } from "@/modules/ma/constants";
import type { BuyerStageSummary } from "@/modules/ma/types/marketing_log";



interface MarketingStageTrackerProps {
  summary: BuyerStageSummary;
  compact?: boolean;
}

export default function MarketingStageTracker({
  summary,
  compact = false,
}: MarketingStageTrackerProps) {
  const completedCount = MARKETING_STAGES.filter((s) => summary.stages[s] != null).length;

  if (compact) {
    return (
      <div className="flex items-center gap-1">
        {MARKETING_STAGES.map((stage) => {
          const done = summary.stages[stage] != null;
          return (
            <div
              key={stage}
              role="img"
              className={`h-2 w-2 rounded-full ${done ? "bg-accent" : "bg-gray-200"}`}
              title={`${MARKETING_STAGE_LABELS[stage]}: ${done ? summary.stages[stage] : "미완료"}`}
              aria-label={`${MARKETING_STAGE_LABELS[stage]}: ${done ? summary.stages[stage] : "미완료"}`}
            />
          );
        })}
        <span className="ml-1 text-xs text-text-muted">
          {completedCount}/{MARKETING_STAGES.length}
        </span>
      </div>
    );
  }

  return (
    <div className="flex items-center gap-0.5">
      {MARKETING_STAGES.map((stage, idx) => {
        const done = summary.stages[stage] != null;
        const dateStr = summary.stages[stage];
        return (
          <div key={stage} className="flex items-center">
            {idx > 0 && (
              <div
                className={`h-px w-4 ${done ? "bg-accent" : "bg-gray-200"}`}
              />
            )}
            <div className="flex flex-col items-center">
              <div
                className={`flex h-6 w-6 items-center justify-center rounded-full text-xs ${
                  done
                    ? "bg-accent text-white"
                    : "border border-gray-300 bg-white text-text-muted"
                }`}
                title={MARKETING_STAGE_LABELS[stage]}
              >
                {done ? <Check className="h-3.5 w-3.5" /> : idx + 1}
              </div>
              <span className="mt-1 text-[10px] text-text-muted leading-tight text-center max-w-[56px]">
                {MARKETING_STAGE_LABELS[stage]}
              </span>
              {dateStr && (
                <span className="text-[9px] text-accent font-medium">
                  {dateStr}
                </span>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}
