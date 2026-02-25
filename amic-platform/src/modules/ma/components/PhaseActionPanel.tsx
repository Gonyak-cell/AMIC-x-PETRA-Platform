import { CheckCircle, Circle, AlertTriangle } from "lucide-react";
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

  const requiredItems = phaseStatus.prerequisites.filter(
    (p) => p.level === "REQUIRED",
  );
  const recommendedItems = phaseStatus.prerequisites.filter(
    (p) => p.level === "RECOMMENDED",
  );
  const requiredMet = requiredItems.filter((p) => p.satisfied).length;
  const requiredTotal = requiredItems.length;
  const requiredPct =
    requiredTotal > 0 ? Math.round((requiredMet / requiredTotal) * 100) : 100;

  const totalCount = phaseStatus.prerequisites.length;
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

      {/* Progress bar — REQUIRED 기준 */}
      <div className="mb-3">
        <div className="flex items-center justify-between mb-1">
          <span className="text-xs text-text-secondary">
            필수 조건 {requiredMet}/{requiredTotal}
            {recommendedItems.length > 0 && (
              <span className="ml-2 text-text-muted">
                · 권장 {recommendedItems.filter((p) => p.satisfied).length}/
                {recommendedItems.length}
              </span>
            )}
          </span>
          <span className="text-xs font-medium text-text-dark">
            {requiredPct}%
          </span>
        </div>
        <div className="h-1.5 w-full rounded-full bg-bg-cool overflow-hidden">
          <div
            className="h-full rounded-full bg-accent transition-all duration-500"
            style={{ width: `${requiredPct}%` }}
          />
        </div>
      </div>

      {/* REQUIRED 항목 */}
      {requiredItems.length > 0 && (
        <ul className="space-y-1">
          {requiredItems.map((req) => (
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
      )}

      {/* RECOMMENDED 항목 */}
      {recommendedItems.length > 0 && (
        <>
          <div className="mt-2 mb-1 flex items-center gap-1.5">
            <AlertTriangle size={10} className="text-caution" />
            <span className="text-[10px] text-text-muted font-medium uppercase tracking-wide">
              권장 사항
            </span>
          </div>
          <ul className="space-y-1">
            {recommendedItems.map((req) => (
              <li key={req.field} className="flex items-center gap-2 text-xs">
                {req.satisfied ? (
                  <CheckCircle size={12} className="text-accent shrink-0" />
                ) : (
                  <Circle size={12} className="text-caution shrink-0" />
                )}
                <span
                  className={
                    req.satisfied
                      ? "text-text-secondary line-through"
                      : "text-text-secondary"
                  }
                >
                  {req.label}
                  {!req.satisfied && (
                    <span className="ml-1 text-text-muted">(권장)</span>
                  )}
                </span>
              </li>
            ))}
          </ul>
        </>
      )}
    </div>
  );
}
