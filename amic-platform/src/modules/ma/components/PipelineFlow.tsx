import { Fragment, useMemo } from "react";
import { Check, CheckCircle, Upload } from "lucide-react";
import {
  PIPELINE_PHASES,
  PIPELINE_MILESTONES,
  type PhaseMilestone,
} from "@/modules/ma/constants";
import type { TransactionPhase } from "@/modules/ma/types/transaction";

interface PipelineFlowProps {
  currentPhase: TransactionPhase;
  onPhaseClick: (phase: TransactionPhase) => void;
  /** 업로드 가능한 마일스톤 클릭 핸들러 */
  onMilestoneClick?: (milestone: PhaseMilestone) => void;
  /** 마일스톤 키 → 문서 업로드 여부 */
  milestoneDocuments?: Record<string, boolean>;
}

/** 단계 수 기반 동적 사이징 — 단계 증감 시 자동 조절 */
function useDynamicSizing() {
  const count = PIPELINE_PHASES.length;
  return useMemo(() => {
    if (count <= 6) {
      return { height: "h-12", font: "text-sm", gap: "gap-2", arrow: 12 };
    }
    if (count <= 8) {
      return { height: "h-11", font: "text-[13px]", gap: "gap-2", arrow: 10 };
    }
    return { height: "h-10", font: "text-xs", gap: "gap-1", arrow: 8 };
  }, [count]);
}

export default function PipelineFlow({
  currentPhase,
  onPhaseClick,
  onMilestoneClick,
  milestoneDocuments,
}: PipelineFlowProps) {
  const rawIdx = PIPELINE_PHASES.findIndex((p) => p.phase === currentPhase);
  // rawIdx === -1 → 숨겨진 단계(POST_CLOSING 등)가 현재 단계 → 모든 스테퍼 단계를 완료로 표시
  const currentIdx = rawIdx === -1 ? PIPELINE_PHASES.length : rawIdx;
  const sizing = useDynamicSizing();
  const arrowPx = sizing.arrow;

  /** 단계별 마일스톤 매핑 캐시 */
  const phaseMilestoneMap = useMemo(
    () => new Map(PIPELINE_MILESTONES.map((m) => [m.afterPhase, m])),
    [],
  );

  return (
    <div className="w-full" role="navigation" aria-label="딜 파이프라인 단계">
      <div className="flex items-center w-full">
        {PIPELINE_PHASES.map((phase, i) => {
          const done = i < currentIdx;
          const active = i === currentIdx;
          const milestone = phaseMilestoneMap.get(phase.phase);

          return (
            <Fragment key={phase.phase}>
              <div className="flex items-center flex-1 min-w-0">
                <button
                  type="button"
                  onClick={() => onPhaseClick(phase.phase)}
                  onKeyDown={(e) => {
                    if (
                      e.key === "ArrowRight" &&
                      i < PIPELINE_PHASES.length - 1
                    ) {
                      e.preventDefault();
                      onPhaseClick(PIPELINE_PHASES[i + 1].phase);
                    } else if (e.key === "ArrowLeft" && i > 0) {
                      e.preventDefault();
                      onPhaseClick(PIPELINE_PHASES[i - 1].phase);
                    }
                  }}
                  aria-label={`${phase.order}. ${phase.label}${active ? " (현재 단계)" : done ? " (완료)" : ""}`}
                  aria-current={active ? "step" : undefined}
                  className="w-full focus:outline-none focus-visible:ring-2 focus-visible:ring-accent/40 rounded"
                >
                  <div
                    className={`
                      flex items-center justify-center ${sizing.gap} w-full ${sizing.height}
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
                          ? `polygon(0 0, calc(100% - ${arrowPx}px) 0, 100% 50%, calc(100% - ${arrowPx}px) 100%, 0 100%)`
                          : i === PIPELINE_PHASES.length - 1
                            ? `polygon(${arrowPx}px 0, 100% 0, 100% 100%, 0 100%, ${arrowPx}px 50%)`
                            : `polygon(${arrowPx}px 0, calc(100% - ${arrowPx}px) 0, 100% 50%, calc(100% - ${arrowPx}px) 100%, 0 100%, ${arrowPx}px 50%)`,
                      paddingLeft: i === 0 ? "8px" : `${arrowPx + 4}px`,
                      paddingRight:
                        i === PIPELINE_PHASES.length - 1
                          ? "8px"
                          : `${arrowPx + 4}px`,
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
                    <span
                      className={`${sizing.font} font-semibold whitespace-nowrap overflow-hidden text-ellipsis`}
                    >
                      {phase.order}. {phase.label}
                    </span>
                  </div>
                </button>
              </div>

              {milestone && i < PIPELINE_PHASES.length - 1 && (
                <MilestoneMarker
                  milestone={milestone}
                  done={done}
                  hasDocument={
                    milestone.milestoneKey
                      ? (milestoneDocuments?.[milestone.milestoneKey] ?? false)
                      : false
                  }
                  onClick={
                    milestone.uploadable && onMilestoneClick
                      ? () => onMilestoneClick(milestone)
                      : undefined
                  }
                />
              )}
            </Fragment>
          );
        })}
      </div>
    </div>
  );
}

/** 마일스톤 다이아몬드 마커 — uploadable 시 클릭 가능 */
function MilestoneMarker({
  milestone,
  done,
  hasDocument,
  onClick,
}: {
  milestone: PhaseMilestone;
  done: boolean;
  hasDocument: boolean;
  onClick?: () => void;
}) {
  const Wrapper = onClick ? "button" : "div";
  const ariaLabel = milestone.uploadable
    ? hasDocument
      ? `${milestone.documentLabel} 업로드 완료 — 클릭하여 관리`
      : `${milestone.documentLabel} 업로드`
    : milestone.label;

  return (
    <Wrapper
      {...(onClick ? { type: "button" as const, onClick } : {})}
      aria-label={ariaLabel}
      className={`flex flex-col items-center mx-0.5 shrink-0 ${
        onClick
          ? "cursor-pointer hover:opacity-80 focus:outline-none focus-visible:ring-2 focus-visible:ring-accent/40 rounded"
          : ""
      }`}
      title={ariaLabel}
    >
      <span className="text-[8px] font-medium text-text-secondary whitespace-nowrap mb-0.5">
        {milestone.label}
      </span>
      <div className="flex flex-col items-center">
        <div className="w-px h-1.5 border-l border-dashed border-text-secondary/40" />
        {milestone.uploadable ? (
          <div
            className={`flex items-center justify-center w-4 h-4 rounded-full border-2 ${
              hasDocument
                ? "bg-accent border-accent text-white"
                : done
                  ? "bg-accent/20 border-accent"
                  : "bg-white border-text-secondary/40"
            }`}
          >
            {hasDocument ? (
              <CheckCircle size={10} />
            ) : (
              <Upload
                size={8}
                className={done ? "text-accent" : "text-text-secondary/60"}
              />
            )}
          </div>
        ) : (
          <div
            className={`flex items-center justify-center rounded-full border-2 ${
              done
                ? "w-3.5 h-3.5 bg-accent border-accent text-white"
                : "w-2 h-2 bg-white border-text-secondary/40"
            }`}
          >
            {done && <Check size={8} strokeWidth={3} />}
          </div>
        )}
        <div className="w-px h-1.5 border-l border-dashed border-text-secondary/40" />
      </div>
    </Wrapper>
  );
}
