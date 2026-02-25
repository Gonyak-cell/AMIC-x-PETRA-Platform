import { cn } from "@/lib/cn";
import type { ConditionMatchLevel } from "@/modules/ma/types/meeting_log";

const MATCH_CONFIG: Record<ConditionMatchLevel, { label: string; color: string; bg: string }> = {
  FULL_MATCH: { label: "완전 부합", color: "text-green-700", bg: "bg-green-50 border-green-200" },
  PARTIAL_MATCH: { label: "부분 부합", color: "text-yellow-700", bg: "bg-yellow-50 border-yellow-200" },
  MISMATCH: { label: "불일치", color: "text-red-700", bg: "bg-red-50 border-red-200" },
  NOT_ASSESSED: { label: "미평가", color: "text-gray-500", bg: "bg-gray-50 border-gray-200" },
};

interface ConditionAssessmentProps {
  conditionMatch: ConditionMatchLevel | null;
  conditionNotes: string | null;
  className?: string;
}

export default function ConditionAssessment({
  conditionMatch,
  conditionNotes,
  className,
}: ConditionAssessmentProps) {
  if (!conditionMatch) return null;
  const cfg = MATCH_CONFIG[conditionMatch];
  return (
    <div className={cn("rounded-lg border p-3", cfg.bg, className)}>
      <div className="flex items-center gap-2 mb-1">
        <span className={cn("text-sm font-semibold", cfg.color)}>{cfg.label}</span>
      </div>
      {conditionNotes && (
        <p className="text-xs text-text-secondary mt-1 whitespace-pre-wrap">{conditionNotes}</p>
      )}
    </div>
  );
}
