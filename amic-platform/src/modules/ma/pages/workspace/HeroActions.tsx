import { ArrowLeft, ArrowRight, Play, Pause, Trash2 } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { Button } from "@/components/ui";
import { PHASE_CONFIG, PHASE_TAB_MAP } from "@/modules/ma/constants";
import type { TransactionPhase } from "@/modules/ma/types/transaction";
import type { PhaseCompletionStatus } from "@/modules/ma/types/workflow";
import type { UseMutationResult } from "@tanstack/react-query";

// ── Props ──────────────────────────────────────
interface HeroActionsProps {
  txnId: string;
  txn: { status: string };
  canWrite: boolean;
  isClient: boolean;
  phaseStatus: PhaseCompletionStatus | undefined;
  acknowledgements: Record<string, boolean>;
  advancePhase: UseMutationResult<
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    any,
    Error,
    { to_phase: string; acknowledgements?: Record<string, boolean> }
  >;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  changeStatus: UseMutationResult<any, Error, { to_status: string }>;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  deleteTxn: UseMutationResult<any, Error, string>;
}

export default function HeroActions({
  txnId,
  txn,
  canWrite,
  isClient,
  phaseStatus,
  acknowledgements,
  advancePhase,
  changeStatus,
  deleteTxn,
}: HeroActionsProps) {
  const navigate = useNavigate();

  const navigateToPhase = (phase: string) => {
    const defaultTab = PHASE_TAB_MAP[phase as TransactionPhase];
    const tabPath = defaultTab === "overview" ? "" : `/${defaultTab}`;
    navigate(`/ma/transactions/${txnId}${tabPath}`, { replace: true });
  };

  return (
    <div className="flex flex-wrap gap-2">
      <Button
        variant="ghost"
        icon={ArrowLeft}
        onClick={() => navigate("/ma/transactions")}
        className="!text-white/80 hover:!text-white hover:!bg-white/10"
      >
        목록
      </Button>

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

      {/* ACTIVE → 롤백 / 전진 / 보류 */}
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
              className="!text-white/80 hover:!text-white hover:!bg-white/10"
            >
              {PHASE_CONFIG.find((p) => p.phase === phaseStatus.previous_phase)
                ?.label ?? "이전"}{" "}
              단계로
            </Button>
          )}

          {phaseStatus &&
            !phaseStatus.can_advance &&
            phaseStatus.blocking_reasons?.length > 0 && (
              <span className="text-xs text-white/60 px-2">
                {phaseStatus.blocking_reasons.join(" · ")}
              </span>
            )}

          {phaseStatus?.can_advance && phaseStatus.next_phase && (
            <Button
              icon={ArrowRight}
              onClick={() =>
                advancePhase.mutate(
                  { to_phase: phaseStatus.next_phase!, acknowledgements },
                  { onSuccess: (u) => navigateToPhase(u.phase) },
                )
              }
              loading={advancePhase.isPending}
              disabled={
                (phaseStatus.pending_acknowledgements?.length ?? 0) > 0 &&
                !phaseStatus.pending_acknowledgements.every(
                  (f) => acknowledgements[f],
                )
              }
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
            className="!text-white/80 hover:!text-white hover:!bg-white/10"
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
          className="!text-white/60 hover:!text-negative hover:!bg-white/10"
        >
          삭제
        </Button>
      )}
    </div>
  );
}
