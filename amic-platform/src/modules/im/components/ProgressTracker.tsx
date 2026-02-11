import { Check, AlertCircle, Loader2 } from "lucide-react";
import { cn } from "@/lib/cn";
import type { DocumentStatus } from "@/modules/im/types/document";

interface Stage {
  key: DocumentStatus;
  label: string;
}

const STAGES: Stage[] = [
  { key: "PENDING", label: "Pending" },
  { key: "COLLECTING", label: "Data Collection" },
  { key: "ANALYZING", label: "Analysis" },
  { key: "GENERATING", label: "Content Gen" },
  { key: "RENDERING", label: "Rendering" },
  { key: "COMPLETED", label: "Complete" },
];

const STATUS_ORDER: Record<DocumentStatus, number> = {
  PENDING: 0,
  COLLECTING: 1,
  ANALYZING: 2,
  GENERATING: 3,
  RENDERING: 4,
  COMPLETED: 5,
  FAILED: -1,
};

interface ProgressTrackerProps {
  status: DocumentStatus;
  progressPct: number;
}

export function ProgressTracker({
  status,
  progressPct,
}: ProgressTrackerProps) {
  const currentIndex = STATUS_ORDER[status];
  const isFailed = status === "FAILED";

  return (
    <div className="space-y-4">
      {/* Progress bar */}
      <div className="flex items-center justify-between text-sm">
        <span className="text-text-secondary">Progress</span>
        <span className="font-medium text-text-dark">{progressPct}%</span>
      </div>
      <div className="w-full bg-bg-cool rounded-full h-2">
        <div
          className={cn(
            "h-2 rounded-full transition-all duration-500",
            isFailed ? "bg-negative" : "bg-amic",
          )}
          style={{ width: `${progressPct}%` }}
        />
      </div>

      {/* Stage indicators */}
      <div className="flex items-center justify-between">
        {STAGES.map((stage, index) => {
          const isCompleted = !isFailed && currentIndex > index;
          const isCurrent = !isFailed && currentIndex === index;
          const isFailedStage = isFailed && index === 0;

          return (
            <div key={stage.key} className="flex flex-col items-center flex-1">
              {/* Connector line + circle */}
              <div className="flex items-center w-full">
                {index > 0 && (
                  <div
                    className={cn(
                      "flex-1 h-0.5",
                      isCompleted || isCurrent
                        ? "bg-amic"
                        : isFailed
                          ? "bg-negative/30"
                          : "bg-gray-200",
                    )}
                  />
                )}
                <div
                  className={cn(
                    "w-8 h-8 rounded-full flex items-center justify-center text-xs font-medium flex-shrink-0",
                    isCompleted && "bg-amic text-white",
                    isCurrent && "bg-amic/20 text-amic ring-2 ring-amic",
                    isFailedStage && "bg-negative/20 text-negative ring-2 ring-negative",
                    !isCompleted && !isCurrent && !isFailedStage && "bg-gray-100 text-text-secondary",
                  )}
                >
                  {isCompleted ? (
                    <Check className="h-4 w-4" />
                  ) : isCurrent ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : isFailedStage ? (
                    <AlertCircle className="h-4 w-4" />
                  ) : (
                    index + 1
                  )}
                </div>
                {index < STAGES.length - 1 && (
                  <div
                    className={cn(
                      "flex-1 h-0.5",
                      isCompleted ? "bg-amic" : "bg-gray-200",
                    )}
                  />
                )}
              </div>
              {/* Label */}
              <span
                className={cn(
                  "text-xs mt-2 text-center",
                  isCompleted || isCurrent
                    ? "text-text-dark font-medium"
                    : "text-text-secondary",
                )}
              >
                {stage.label}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
