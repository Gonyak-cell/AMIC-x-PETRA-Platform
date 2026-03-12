import { useState, useEffect } from "react";
import { AlertTriangle, CheckCircle, Circle, Info } from "lucide-react";
import { usePhaseCompletion } from "@/modules/ma/hooks/useTransactions";
import { PHASE_CONFIG } from "@/modules/ma/constants";
import { Spinner } from "@/components/ui";

interface PhaseActionPanelProps {
  txnId: string;
  onAcknowledgementsChange?: (acks: Record<string, boolean>) => void;
}

export default function PhaseActionPanel({
  txnId,
  onAcknowledgementsChange,
}: PhaseActionPanelProps) {
  const { data: phaseStatus, isLoading } = usePhaseCompletion(txnId);
  const [acks, setAcks] = useState<Record<string, boolean>>({});

  // acknowledgement 항목이 바뀌면 상위에 알림
  useEffect(() => {
    onAcknowledgementsChange?.(acks);
  }, [acks, onAcknowledgementsChange]);

  // phase가 바뀌면 acks 초기화
  useEffect(() => {
    setAcks({});
  }, [phaseStatus?.current_phase]);

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

  const handleAck = (field: string, checked: boolean) => {
    setAcks((prev) => ({ ...prev, [field]: checked }));
  };

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

      {/* Gate summary */}
      {phaseStatus.gate_summary && (
        <div className="flex items-start gap-1.5 mb-3 rounded-lg bg-bg-cool px-3 py-2">
          <Info size={12} className="text-text-secondary shrink-0 mt-0.5" />
          <span className="text-xs text-text-secondary">
            {phaseStatus.gate_summary}
          </span>
        </div>
      )}

      {/* Progress bar */}
      {totalCount > 0 && (
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
      )}

      {totalCount > 0 ? (
        <ul className="space-y-1">
          {items.map((req) => (
            <li key={req.field} className="flex items-center gap-2 text-xs">
              {req.requires_acknowledgement ? (
                <label className="flex items-center gap-2 cursor-pointer w-full">
                  <input
                    type="checkbox"
                    checked={!!acks[req.field]}
                    onChange={(e) => handleAck(req.field, e.target.checked)}
                    className="h-3 w-3 rounded border-warning text-warning accent-warning"
                  />
                  <AlertTriangle
                    size={12}
                    className="text-warning shrink-0"
                  />
                  <span className="text-text-dark font-medium">
                    {req.label}
                  </span>
                  {req.current_value && (
                    <span className="text-warning ml-auto">
                      {req.current_value}
                    </span>
                  )}
                </label>
              ) : (
                <>
                  {req.satisfied ? (
                    <CheckCircle
                      size={12}
                      className="text-accent shrink-0"
                    />
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
                  {req.current_value && (
                    <span className="text-text-secondary ml-auto">
                      {req.current_value}
                      {req.target_value ? ` / ${req.target_value}` : ""}
                    </span>
                  )}
                </>
              )}
            </li>
          ))}
        </ul>
      ) : (
        <p className="text-xs text-text-secondary">
          다음 단계 전환 조건이 없습니다.
        </p>
      )}
    </div>
  );
}
