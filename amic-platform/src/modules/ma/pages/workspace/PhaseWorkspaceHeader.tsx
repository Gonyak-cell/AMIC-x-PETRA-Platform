import { ArrowLeft, ArrowRight, Pause, Play, Trash2, Upload } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { Badge, Button } from "@/components/ui";
import { cn } from "@/lib/cn";
import {
  PHASE_CONFIG,
  PHASE_TAB_MAP,
  TRANSACTION_STATUS_VARIANT,
} from "@/modules/ma/constants";
import {
  useAdvancePhase,
  useChangeStatus,
  useDeleteTransaction,
  usePhaseCompletion,
} from "@/modules/ma/hooks/useTransactions";
import type { TransactionPhase } from "@/modules/ma/types/transaction";

interface PhaseWorkspaceHeaderProps {
  txnId: string;
  txn: { status: string; phase: string; name: string };
  canWrite: boolean;
  isClient: boolean;
  activeTab: string;
  onOpenVdrUpload: () => void;
  surface?: "page" | "hero";
}

export default function PhaseWorkspaceHeader({
  txnId,
  txn,
  canWrite,
  isClient,
  activeTab,
  onOpenVdrUpload,
  surface = "page",
}: PhaseWorkspaceHeaderProps) {
  const navigate = useNavigate();
  const { data: phaseStatus } = usePhaseCompletion(txnId);
  const advancePhase = useAdvancePhase(txnId);
  const changeStatus = useChangeStatus(txnId);
  const deleteTxn = useDeleteTransaction();
  const isHero = surface === "hero";

  const heroGhostButtonClass =
    "text-white/80 hover:text-white hover:bg-white/10 focus:ring-white/25 focus:ring-offset-0";
  const heroOutlineButtonClass =
    "border-white/20 bg-white/[0.08] text-white hover:border-white/35 hover:bg-white/[0.14] focus:ring-white/25 focus:ring-offset-0";
  const heroPrimaryButtonClass =
    "bg-accent text-white hover:bg-accent-hover focus:ring-accent focus:ring-offset-0 shadow-none";

  const navigateToPhase = (phase: string) => {
    const defaultTab = PHASE_TAB_MAP[phase as TransactionPhase];
    const tabPath = defaultTab === "overview" ? "" : `/${defaultTab}`;
    navigate(`/ma/transactions/${txnId}${tabPath}`, { replace: true });
  };

  const currentConfig = PHASE_CONFIG.find((phase) => phase.phase === txn.phase);
  const previousPhaseLabel = phaseStatus?.previous_phase
    ? PHASE_CONFIG.find((phase) => phase.phase === phaseStatus.previous_phase)
        ?.label ?? "이전"
    : null;
  const nextPhaseLabel = phaseStatus?.next_phase
    ? PHASE_CONFIG.find((phase) => phase.phase === phaseStatus.next_phase)?.label ??
      "다음"
    : null;

  return (
    <div
      className={cn(
        "overflow-hidden",
        isHero
          ? "rounded-2xl border border-white/15 bg-white/[0.08] backdrop-blur-xl shadow-[0_18px_40px_rgba(7,26,18,0.16)]"
          : "rounded-xl border border-gray-border bg-white",
      )}
    >
      <div
        className={cn(
          "flex flex-wrap items-center gap-3",
          isHero ? "px-4 py-4 sm:px-5" : "px-4 py-3",
        )}
      >
        <Button
          variant="ghost"
          size={isHero ? "sm" : "md"}
          icon={ArrowLeft}
          onClick={() => navigate("/ma/transactions")}
          className={cn(isHero ? heroGhostButtonClass : "text-text-secondary")}
        >
          목록
        </Button>

        <div className="flex items-center gap-2">
          <span
            className={cn(
              "text-sm font-heading font-semibold",
              isHero ? "text-white" : "text-text-dark",
            )}
          >
            {currentConfig?.label ?? txn.phase}
          </span>
          <Badge
            variant={TRANSACTION_STATUS_VARIANT[txn.status]}
            pill
            className={cn(
              isHero && "border border-white/15 bg-white/12 text-white",
            )}
          >
            {txn.status}
          </Badge>
        </div>

        <div className="ml-auto flex flex-wrap items-center gap-2">
          {canWrite && activeTab !== "vdr" && (
            <Button
              variant="secondary"
              size={isHero ? "sm" : "md"}
              icon={Upload}
              onClick={onOpenVdrUpload}
              className={cn(isHero && heroOutlineButtonClass)}
            >
              Upload to VDR
            </Button>
          )}

          {canWrite && txn.status === "DRAFT" && (
            <Button
              size={isHero ? "sm" : "md"}
              icon={Play}
              onClick={() => changeStatus.mutate({ to_status: "ACTIVE" })}
              loading={changeStatus.isPending}
              className={cn(isHero && heroPrimaryButtonClass)}
            >
              시작
            </Button>
          )}

          {canWrite && txn.status === "ACTIVE" && (
            <>
              {phaseStatus?.previous_phase && (
                <Button
                  variant="ghost"
                  size={isHero ? "sm" : "md"}
                  icon={ArrowLeft}
                  onClick={() =>
                    advancePhase.mutate(
                      { to_phase: phaseStatus.previous_phase! },
                      { onSuccess: (updated) => navigateToPhase(updated.phase) },
                    )
                  }
                  loading={advancePhase.isPending}
                  className={cn(isHero && heroGhostButtonClass)}
                >
                  {`${previousPhaseLabel ?? "이전"} 단계로`}
                </Button>
              )}

              {phaseStatus?.can_advance && phaseStatus.next_phase && (
                <Button
                  size={isHero ? "sm" : "md"}
                  icon={ArrowRight}
                  onClick={() =>
                    advancePhase.mutate(
                      { to_phase: phaseStatus.next_phase! },
                      { onSuccess: (updated) => navigateToPhase(updated.phase) },
                    )
                  }
                  loading={advancePhase.isPending}
                  className={cn(isHero && heroPrimaryButtonClass)}
                >
                  {`${nextPhaseLabel ?? "다음"} 단계로`}
                </Button>
              )}

              <Button
                variant="ghost"
                size={isHero ? "sm" : "md"}
                icon={Pause}
                onClick={() => changeStatus.mutate({ to_status: "ON_HOLD" })}
                loading={changeStatus.isPending}
                className={cn(isHero ? heroGhostButtonClass : undefined)}
              >
                보류
              </Button>
            </>
          )}

          {canWrite && txn.status === "ON_HOLD" && (
            <Button
              size={isHero ? "sm" : "md"}
              icon={Play}
              onClick={() => changeStatus.mutate({ to_status: "ACTIVE" })}
              loading={changeStatus.isPending}
              className={cn(isHero && heroPrimaryButtonClass)}
            >
              재개
            </Button>
          )}

          {canWrite && !isClient && (
            <Button
              variant="ghost"
              size={isHero ? "sm" : "md"}
              icon={Trash2}
              onClick={() => {
                if (confirm("이 거래를 삭제하시겠습니까?")) {
                  deleteTxn.mutate(txnId, {
                    onSuccess: () => navigate("/ma/transactions"),
                  });
                }
              }}
              loading={deleteTxn.isPending}
              className={cn(
                isHero
                  ? "text-white/72 hover:bg-white/10 hover:text-white focus:ring-white/25 focus:ring-offset-0"
                  : "text-text-secondary hover:text-negative",
              )}
            >
              삭제
            </Button>
          )}
        </div>
      </div>
    </div>
  );
}
