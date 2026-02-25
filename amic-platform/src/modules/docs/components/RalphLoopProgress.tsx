import { useRalphProgress } from "../hooks/useRalphLoop";

interface RalphLoopProgressProps {
  sessionId: string;
}

export default function RalphLoopProgress({ sessionId }: RalphLoopProgressProps) {
  const { data: progress, isLoading } = useRalphProgress(sessionId);

  if (isLoading || !progress) {
    return (
      <div className="flex items-center gap-3 rounded-lg border bg-white p-4">
        <div className="h-4 w-4 animate-spin rounded-full border-2 border-blue-500 border-t-transparent" />
        <span className="text-sm text-gray-500">Ralph Loop 진행 상황 로딩 중...</span>
      </div>
    );
  }

  const phaseName = {
    plan: "Phase 1: 구조 기획",
    iterate: "Phase 2: 섹션별 생성-평가",
    validate: "Phase 3: 통합 검증",
  }[progress.current_phase] ?? progress.current_phase;

  const progressPct = progress.total_iterations > 0
    ? Math.min(100, (progress.iteration / progress.total_iterations) * 100)
    : 0;

  return (
    <div className="rounded-lg border bg-white p-4 space-y-3">
      {/* Phase & Section */}
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm font-medium text-gray-900">{phaseName}</p>
          {progress.current_section && (
            <p className="text-xs text-gray-500">
              현재 섹션: {progress.current_section}
            </p>
          )}
        </div>
        <span className="text-xs text-gray-400">
          반복 {progress.iteration}/{progress.total_iterations}
        </span>
      </div>

      {/* Progress Bar */}
      <div className="h-2 w-full rounded-full bg-gray-100">
        <div
          className="h-full rounded-full bg-blue-500 transition-all duration-500"
          style={{ width: `${progressPct}%` }}
        />
      </div>

      {/* Latest Gate */}
      {progress.gate_results.length > 0 && (
        <div className="flex items-center gap-2 text-xs">
          {progress.gate_results.map((gate, i) => {
            const color = {
              PASS: "text-positive",
              COND: "text-amber-600",
              FAIL: "text-negative",
            }[gate.verdict];
            return (
              <span key={i} className={`font-medium ${color}`}>
                {gate.gate_name}: {gate.verdict} ({gate.weighted_score.toFixed(1)})
              </span>
            );
          })}
        </div>
      )}

      {/* Score History Mini */}
      {progress.score_history.length > 0 && (
        <div className="flex items-center gap-1 text-[10px] text-gray-400">
          <span>점수:</span>
          {progress.score_history.map((p, i) => (
            <span key={i} className="font-mono">
              {p.score.toFixed(1)}
              {i < progress.score_history.length - 1 ? " → " : ""}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
