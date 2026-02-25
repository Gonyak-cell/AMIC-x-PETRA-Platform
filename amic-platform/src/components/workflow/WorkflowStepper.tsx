import { Check, Circle } from "lucide-react";
import { cn } from "@/lib/cn";
import type { DealPhase } from "@/modules/fdd/types/deal";

interface StepConfig {
  phase: DealPhase;
  label: string;
  description: string;
}

const STEPS: StepConfig[] = [
  { phase: "MOU", label: "MoU 체결", description: "딜 설정 및 팀 구성" },
  { phase: "VDR_SETUP", label: "VDR 개설", description: "데이터룸 폴더 구조 생성" },
  { phase: "DATA_UPLOAD", label: "자료 업로드", description: "재무 자료 업로드" },
  { phase: "ANALYSIS", label: "자료 검토", description: "분석 수행 및 검토" },
  { phase: "CHECKLIST_REVIEW", label: "체크리스트", description: "자동 분석 결과 검수" },
  { phase: "REPORTING", label: "보고서 작성", description: "최종 보고서 생성" },
];

interface WorkflowStepperProps {
  currentPhase: DealPhase;
  className?: string;
}

export default function WorkflowStepper({ currentPhase, className }: WorkflowStepperProps) {
  const currentIndex = STEPS.findIndex((s) => s.phase === currentPhase);

  return (
    <div className={cn("flex items-start gap-0", className)}>
      {STEPS.map((step, index) => {
        const isCompleted = index < currentIndex;
        const isCurrent = index === currentIndex;

        return (
          <div key={step.phase} className="flex-1 flex flex-col items-center relative">
            {/* Connector line */}
            {index > 0 && (
              <div
                className={cn(
                  "absolute top-4 right-1/2 w-full h-0.5 -translate-y-1/2",
                  isCompleted ? "bg-positive" : "bg-gray-200"
                )}
              />
            )}

            {/* Step circle */}
            <div
              className={cn(
                "relative z-10 w-8 h-8 rounded-full flex items-center justify-center",
                isCompleted && "bg-positive text-white",
                isCurrent && "bg-blue-600 text-white",
                !isCompleted && !isCurrent && "bg-gray-200 text-text-secondary"
              )}
            >
              {isCompleted ? (
                <Check className="h-4 w-4" />
              ) : (
                <Circle className="h-4 w-4" />
              )}
            </div>

            {/* Label */}
            <span
              className={cn(
                "mt-2 text-xs font-medium text-center",
                isCurrent ? "text-blue-600" : isCompleted ? "text-positive" : "text-text-secondary"
              )}
            >
              {step.label}
            </span>

            {/* Description */}
            <span className="mt-0.5 text-[10px] text-text-secondary text-center hidden sm:block">
              {step.description}
            </span>
          </div>
        );
      })}
    </div>
  );
}
