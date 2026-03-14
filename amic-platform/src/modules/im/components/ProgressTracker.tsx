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
  AWAITING_UPLOAD: -2,
  PENDING: 0,
  COLLECTING: 1,
  ANALYZING: 2,
  GENERATING: 3,
  RENDERING: 4,
  COMPLETED: 5,
  QUALITY_CONDITIONAL: 5,
  QUALITY_FAILED: 5,
  FAILED: -1,
};

/** Each stage's starting progress percentage — used to infer which stage failed. */
const PROGRESS_STAGE_MAP = [0, 20, 40, 55, 80, 100];

function getFailedStageIndex(progressPct: number): number {
  const pct =
    Number.isFinite(progressPct) && progressPct >= 0 ? progressPct : 0;
  for (let i = PROGRESS_STAGE_MAP.length - 1; i >= 0; i--) {
    if (pct >= PROGRESS_STAGE_MAP[i]) return i;
  }
  return 0;
}

interface ProgressTrackerProps {
  status: DocumentStatus;
  progressPct: number;
}

export function ProgressTracker({ status, progressPct }: ProgressTrackerProps) {
  const safePct =
    Number.isFinite(progressPct) && progressPct >= 0
      ? Math.min(progressPct, 100)
      : 0;
  const currentIndex = STATUS_ORDER[status];
  const isFailed = status === "FAILED";
  const failedAtIndex = isFailed ? getFailedStageIndex(safePct) : -1;

  return (
    <div className="space-y-4">
      {/* Progress bar */}
      <div className="flex items-center justify-between text-sm">
        <span className="text-text-secondary">Progress</span>
        <span className="font-medium text-text-dark">{safePct}%</span>
      </div>
      <div
        className="w-full bg-bg-cool rounded-full h-2"
        role="progressbar"
        aria-valuenow={safePct}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label={`Document generation progress: ${safePct}%${isFailed ? " (failed)" : ""}`}
      >
        <div
          className={cn(
            "h-2 rounded-full transition-all duration-500",
            isFailed ? "bg-negative" : "bg-amic",
          )}
          style={{ width: `${safePct}%` }}
        />
      </div>

      {/* Stage indicators */}
      <div className="flex items-center justify-between">
        {STAGES.map((stage, index) => {
          const isCompleted = !isFailed
            ? currentIndex > index
            : index < failedAtIndex;
          const isCurrent = !isFailed && currentIndex === index;
          const isFailedStage = isFailed && index === failedAtIndex;

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
                        : isFailedStage
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
                    isFailedStage &&
                      "bg-negative/20 text-negative ring-2 ring-negative",
                    !isCompleted &&
                      !isCurrent &&
                      !isFailedStage &&
                      "bg-gray-100 text-text-secondary",
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
                    : isFailedStage
                      ? "text-negative font-medium"
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
