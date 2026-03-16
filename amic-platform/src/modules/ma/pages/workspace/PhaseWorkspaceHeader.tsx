import { useState, useEffect } from "react";
import {
  ArrowLeft,
  ArrowRight,
  Play,
  Pause,
  Trash2,
  AlertTriangle,
  CheckCircle,
  Circle,
  Info,
} from "lucide-react";
import { useNavigate } from "react-router-dom";
import { Button, Badge, Spinner } from "@/components/ui";
import {
  PHASE_CONFIG,
  PHASE_TAB_MAP,
  TRANSACTION_STATUS_VARIANT,
} from "@/modules/ma/constants";
import {
  usePhaseCompletion,
  useAdvancePhase,
  useChangeStatus,
  useDeleteTransaction,
} from "@/modules/ma/hooks/useTransactions";
import type { TransactionPhase } from "@/modules/ma/types/transaction";

// ── Props ──────────────────────────────────────
interface PhaseWorkspaceHeaderProps {
  txnId: string;
  txn: { status: string; phase: string; name: string };
  canWrite: boolean;
  isClient: boolean;
}

// ── Component ──────────────────────────────────
export default function PhaseWorkspaceHeader({
  txnId,
  txn,
  canWrite,
  isClient,
}: PhaseWorkspaceHeaderProps) {
  const navigate = useNavigate();
  const { data: phaseStatus, isLoading } = usePhaseCompletion(txnId);
  const advancePhase = useAdvancePhase(txnId);
  const changeStatus = useChangeStatus(txnId);
  const deleteTxn = useDeleteTransaction();

  const [acks, setAcks] = useState<Record<string, boolean>>({});

  // phase가 바뀌면 acks 초기화
  useEffect(() => {
    setAcks({});
  }, [phaseStatus?.current_phase]);

  const navigateToPhase = (phase: string) => {
    const defaultTab = PHASE_TAB_MAP[phase as TransactionPhase];
    const tabPath = defaultTab === "overview" ? "" : `/${defaultTab}`;
    navigate(`/ma/transactions/${txnId}${tabPath}`, { replace: true });
  };

  const currentConfig = PHASE_CONFIG.find((p) => p.phase === txn.phase);

  const items = phaseStatus?.prerequisites ?? [];
  const metCount = items.filter((p) => p.satisfied).length;
  const totalCount = items.length;
  const pct = totalCount > 0 ? Math.round((metCount / totalCount) * 100) : 100;

  const hasPendingAcks =
    (phaseStatus?.pending_acknowledgements?.length ?? 0) > 0 &&
    !phaseStatus?.pending_acknowledgements.every((f) => acks[f]);

  return (
    <div className="rounded-xl border border-gray-border bg-white overflow-hidden">
      {/* ── 상단 행: 네비 + 단계 정보 + CTA ── */}
      <div className="flex items-center gap-3 px-4 py-3 flex-wrap">
        {/* 목록 버튼 */}
        <Button
          variant="ghost"
          icon={ArrowLeft}
          onClick={() => navigate("/ma/transactions")}
          className="text-text-secondary"
        >
          목록
        </Button>

        {/* 단계명 + 상태 */}
        <div className="flex items-center gap-2">
          <span className="text-sm font-heading font-semibold text-text-dark">
            {currentConfig?.label ?? txn.phase}
          </span>
          <Badge variant={TRANSACTION_STATUS_VARIANT[txn.status]}>
            {txn.status}
          </Badge>
        </div>

        {/* 진행률 (필수 조건이 있을 때) */}
        {!isLoading && totalCount > 0 && (
          <div className="flex items-center gap-2">
            <div className="h-1.5 w-24 rounded-full bg-bg-cool overflow-hidden">
              <div
                className="h-full rounded-full bg-accent transition-all duration-500"
                style={{ width: `${pct}%` }}
              />
            </div>
            <span className="text-xs text-text-secondary">
              {metCount}/{totalCount}
            </span>
          </div>
        )}

        {/* CTA 버튼 (우측 정렬) */}
        <div className="ml-auto flex items-center gap-2 flex-wrap">
          {/* DRAFT → 시작 */}
          {canWrite && txn.status === "DRAFT" && (
            <Button
              icon={Play}
              onClick={() => changeStatus.mutate({ to_status: "ACTIVE" })}
              loading={changeStatus.isPending}
            >
              시작
            </Button>
          )}

          {/* ACTIVE → 이전/다음/보류 */}
          {canWrite && txn.status === "ACTIVE" && (
            <>
              {phaseStatus?.previous_phase && (
                <Button
                  variant="ghost"
                  icon={ArrowLeft}
                  onClick={() =>
                    advancePhase.mutate(
                      { to_phase: phaseStatus.previous_phase! },
                      { onSuccess: (u) => navigateToPhase(u.phase) },
                    )
                  }
                  loading={advancePhase.isPending}
                >
                  {PHASE_CONFIG.find(
                    (p) => p.phase === phaseStatus.previous_phase,
                  )?.label ?? "이전"}{" "}
                  단계로
                </Button>
              )}

              {phaseStatus &&
                !phaseStatus.can_advance &&
                phaseStatus.blocking_reasons?.length > 0 && (
                  <span className="text-xs text-text-secondary px-1">
                    {phaseStatus.blocking_reasons.join(" · ")}
                  </span>
                )}

              {phaseStatus?.can_advance && phaseStatus.next_phase && (
                <Button
                  icon={ArrowRight}
                  onClick={() =>
                    advancePhase.mutate(
                      {
                        to_phase: phaseStatus.next_phase!,
                        acknowledgements: acks,
                      },
                      { onSuccess: (u) => navigateToPhase(u.phase) },
                    )
                  }
                  loading={advancePhase.isPending}
                  disabled={hasPendingAcks}
                >
                  {PHASE_CONFIG.find((p) => p.phase === phaseStatus.next_phase)
                    ?.label ?? "다음"}{" "}
                  단계로
                </Button>
              )}

              <Button
                variant="ghost"
                icon={Pause}
                onClick={() => changeStatus.mutate({ to_status: "ON_HOLD" })}
                loading={changeStatus.isPending}
              >
                보류
              </Button>
            </>
          )}

          {/* ON_HOLD → 재개 */}
          {canWrite && txn.status === "ON_HOLD" && (
            <Button
              icon={Play}
              onClick={() => changeStatus.mutate({ to_status: "ACTIVE" })}
              loading={changeStatus.isPending}
            >
              재개
            </Button>
          )}

          {/* 삭제 */}
          {canWrite && !isClient && (
            <Button
              variant="ghost"
              icon={Trash2}
              onClick={() => {
                if (confirm("이 거래를 삭제하시겠습니까?")) {
                  deleteTxn.mutate(txnId, {
                    onSuccess: () => navigate("/ma/transactions"),
                  });
                }
              }}
              loading={deleteTxn.isPending}
              className="text-text-secondary hover:text-negative"
            >
              삭제
            </Button>
          )}
        </div>
      </div>

      {/* ── Gate summary ── */}
      {phaseStatus?.gate_summary && (
        <div className="flex items-start gap-1.5 mx-4 mb-3 rounded-lg bg-bg-cool px-3 py-2">
          <Info size={12} className="text-text-secondary shrink-0 mt-0.5" />
          <span className="text-xs text-text-secondary">
            {phaseStatus.gate_summary}
          </span>
        </div>
      )}

      {/* ── 필수 조건 목록 ── */}
      {isLoading ? (
        <div className="flex justify-center py-3">
          <Spinner className="h-4 w-4" />
        </div>
      ) : totalCount > 0 ? (
        <div className="border-t border-gray-border px-4 py-3">
          <ul className="space-y-1">
            {items.map((req) => (
              <li key={req.field} className="flex items-center gap-2 text-xs">
                {req.requires_acknowledgement ? (
                  <label className="flex items-center gap-2 cursor-pointer w-full">
                    <input
                      type="checkbox"
                      checked={!!acks[req.field]}
                      onChange={(e) =>
                        setAcks((prev) => ({
                          ...prev,
                          [req.field]: e.target.checked,
                        }))
                      }
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

          {/* Acknowledgement 미완료 경고 */}
          {phaseStatus?.requires_user_acknowledgement && hasPendingAcks && (
            <div className="flex items-start gap-1.5 mt-3 rounded-lg bg-warning/5 border border-warning/20 px-3 py-2">
              <AlertTriangle
                size={12}
                className="text-warning shrink-0 mt-0.5"
              />
              <span className="text-xs text-warning">
                단계 전환을 위해 확인이 필요한 항목이 있습니다. 위 체크박스를
                선택해 주세요.
              </span>
            </div>
          )}
        </div>
      ) : null}
    </div>
  );
}
