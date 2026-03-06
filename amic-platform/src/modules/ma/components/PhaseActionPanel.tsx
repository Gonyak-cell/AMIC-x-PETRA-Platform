import { CheckCircle, Circle } from "lucide-react";
import { usePhaseCompletion } from "@/modules/ma/hooks/useTransactions";
import { PHASE_CONFIG } from "@/modules/ma/constants";
import { Spinner } from "@/components/ui";

interface PhaseActionPanelProps {
  txnId: string;
}

export default function PhaseActionPanel({ txnId }: PhaseActionPanelProps) {
  const { data: phaseStatus, isLoading } = usePhaseCompletion(txnId);

  if (isLoading || !phaseStatus) {
    return (
      <div className="flex items-center justify-center py-4">
        <Spinner className="h-5 w-5" />
      </div>
    );
  }

  const currentConfig = PHASE_CONFIG.find(
    (p) => p.phase === phaseStatus.current_phase,
  );

  const items = phaseStatus.prerequisites;
  const metCount = items.filter((p) => p.satisfied).length;
  const totalCount = items.length;
  const pct = totalCount > 0 ? Math.round((metCount / totalCount) * 100) : 100;

  if (totalCount === 0) return null;

  return (
    <div className="rounded-xl border border-gray-border bg-white p-4">
      <div className="flex items-center gap-2 mb-2">
        <h3 className="text-sm font-heading font-semibold text-text-dark">
          현재 단계: {currentConfig?.label ?? phaseStatus.current_phase}
        </h3>
        <span className="text-xs text-text-secondary">
          {currentConfig?.description}
        </span>
      </div>

      {/* Progress bar */}
      <div className="mb-3">
        <div className="flex items-center justify-between mb-1">
          <span className="text-xs text-text-secondary">
            필수 조건 {metCount}/{totalCount}
          </span>
          <span className="text-xs font-medium text-text-dark">{pct}%</span>
        </div>
        <div className="h-1.5 w-full rounded-full bg-bg-cool overflow-hidden">
          <div
            className="h-full rounded-full bg-accent transition-all duration-500"
            style={{ width: `${pct}%` }}
          />
        </div>
      </div>

      <ul className="space-y-1">
        {items.map((req) => (
          <li key={req.field} className="flex items-center gap-2 text-xs">
            {req.satisfied ? (
              <CheckCircle size={12} className="text-accent shrink-0" />
            ) : (
              <Circle size={12} className="text-negative shrink-0" />
            )}
            <span
              className={
                req.satisfied
                  ? "text-text-secondary line-through"
                  : "text-text-dark font-medium"
              }
            >
              {req.label}
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}
