import { Fragment } from "react";
import { CheckCircle } from "lucide-react";
import { PHASE_CONFIG, PHASE_MILESTONES } from "@/modules/ma/constants";
import type { TransactionPhase } from "@/modules/ma/types/transaction";

interface PipelineFlowProps {
  currentPhase: TransactionPhase;
  onPhaseClick: (phase: TransactionPhase) => void;
}

export default function PipelineFlow({
  currentPhase,
  onPhaseClick,
}: PipelineFlowProps) {
  const currentIdx = Math.max(
    0,
    PHASE_CONFIG.findIndex((p) => p.phase === currentPhase),
  );

  return (
    <div className="w-full">
      <div className="flex items-center w-full">
        {PHASE_CONFIG.map((phase, i) => {
          const done = i < currentIdx;
          const active = i === currentIdx;
          const milestone = PHASE_MILESTONES.find(
            (m) => m.afterPhase === phase.phase,
          );

          return (
            <Fragment key={phase.phase}>
              <div className="flex items-center flex-1 min-w-0">
                <button
                  type="button"
                  onClick={() => onPhaseClick(phase.phase)}
                  className="w-full focus:outline-none focus-visible:ring-2 focus-visible:ring-accent/40 rounded"
                >
                  <div
                    className={`
                      flex items-center justify-center gap-1.5 w-full h-10
                      transition-colors cursor-pointer
                      ${
                        active
                          ? "bg-accent text-white"
                          : done
                            ? "bg-accent/10 text-accent"
                            : "bg-bg-cool text-text-muted hover:bg-gray-100"
                      }
                    `}
                    style={{
                      clipPath:
                        i === 0
                          ? "polygon(0 0, calc(100% - 10px) 0, 100% 50%, calc(100% - 10px) 100%, 0 100%)"
                          : i === PHASE_CONFIG.length - 1
                            ? "polygon(10px 0, 100% 0, 100% 100%, 0 100%, 10px 50%)"
                            : "polygon(10px 0, calc(100% - 10px) 0, 100% 50%, calc(100% - 10px) 100%, 0 100%, 10px 50%)",
                    }}
                  >
                    <div className="shrink-0">
                      {done ? (
                        <CheckCircle size={13} />
                      ) : active ? (
                        <span className="relative flex h-2.5 w-2.5">
                          <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-white/60" />
                          <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-white" />
                        </span>
                      ) : (
                        <span className="flex h-2.5 w-2.5 rounded-full bg-current opacity-30" />
                      )}
                    </div>
                    <span className="text-xs font-semibold whitespace-nowrap">
                      {phase.order}. {phase.label}
                    </span>
                  </div>
                </button>
              </div>

              {milestone && i < PHASE_CONFIG.length - 1 && (
                <div className="flex flex-col items-center mx-0.5 shrink-0">
                  <span className="text-[8px] font-medium text-text-secondary whitespace-nowrap mb-0.5">
                    {milestone.label}
                  </span>
                  <div className="flex flex-col items-center">
                    <div className="w-px h-1.5 border-l border-dashed border-text-secondary/40" />
                    <div
                      className={`w-2 h-2 rounded-full border-2 ${
                        done
                          ? "bg-accent border-accent"
                          : "bg-white border-text-secondary/40"
                      }`}
                    />
                    <div className="w-px h-1.5 border-l border-dashed border-text-secondary/40" />
                  </div>
                </div>
              )}
            </Fragment>
          );
        })}
      </div>
    </div>
  );
}
