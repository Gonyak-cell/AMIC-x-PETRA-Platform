import type { RalphSession, RalphProgress, DimensionScore } from "../hooks/useRalphLoop";

// ── Score Badge ─────────────────────────────────────────────────────────────

function ScoreBadge({ score, label }: { score: number; label?: string }) {
  const color =
    score >= 4.0
      ? "text-positive bg-positive-light border-green-200"
      : score >= 3.0
        ? "text-amber-600 bg-caution-light border-amber-200"
        : "text-negative bg-negative-light border-negative/30";

  return (
    <span className={`inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-xs font-medium ${color}`}>
      {label && <span className="opacity-70">{label}</span>}
      {score.toFixed(1)}/5.0
    </span>
  );
}

// ── Dimension Bar ───────────────────────────────────────────────────────────

function DimensionBar({ dim }: { dim: DimensionScore }) {
  const pct = Math.min(100, (dim.score / 5.0) * 100);
  const barColor =
    dim.score >= 4.0 ? "bg-green-500" : dim.score >= 3.0 ? "bg-amber-500" : "bg-red-500";

  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between text-xs">
        <span className="text-gray-600">{dim.label}</span>
        <span className="font-medium">{dim.score.toFixed(1)}</span>
      </div>
      <div className="h-1.5 w-full rounded-full bg-gray-100">
        <div className={`h-full rounded-full ${barColor}`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

// ── Gate Result Card ────────────────────────────────────────────────────────

function GateResultCard({ gate }: { gate: RalphProgress["gate_results"][0] }) {
  const verdictStyle = {
    PASS: "bg-positive-light text-positive border-green-200",
    COND: "bg-caution-light text-amber-700 border-amber-200",
    FAIL: "bg-negative-light text-negative border-negative/30",
  }[gate.verdict];

  return (
    <div className="rounded-lg border bg-white p-4 space-y-3">
      <div className="flex items-center justify-between">
        <h4 className="text-sm font-medium text-gray-900">{gate.gate_name}</h4>
        <span className={`rounded-full border px-2 py-0.5 text-xs font-medium ${verdictStyle}`}>
          {gate.verdict}
        </span>
      </div>
      <ScoreBadge score={gate.weighted_score} />
      <div className="space-y-2">
        {gate.dimensions.map((dim) => (
          <DimensionBar key={dim.name} dim={dim} />
        ))}
      </div>
      {gate.issues.length > 0 && (
        <div className="mt-2">
          <p className="text-xs font-medium text-negative mb-1">이슈 ({gate.issues.length})</p>
          <ul className="text-xs text-gray-600 space-y-0.5">
            {gate.issues.slice(0, 3).map((issue, i) => (
              <li key={i} className="truncate">• {issue}</li>
            ))}
          </ul>
        </div>
      )}
      <div className="flex items-center gap-3 text-[10px] text-gray-400 pt-1">
        <span>${gate.cost_usd.toFixed(3)}</span>
        <span>{gate.duration_ms}ms</span>
      </div>
    </div>
  );
}

// ── Main Dashboard ──────────────────────────────────────────────────────────

interface QualityDashboardProps {
  session: RalphSession;
  progress?: RalphProgress;
}

export default function QualityDashboard({ session, progress }: QualityDashboardProps) {
  const statusBadge = {
    pending: "bg-gray-100 text-gray-600",
    running: "bg-info-light text-info",
    completed: "bg-positive-light text-positive",
    failed: "bg-negative-light text-negative",
  }[session.status];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-lg font-semibold text-gray-900">Ralph Loop 품질 대시보드</h3>
          <p className="text-sm text-gray-500">{session.doc_type} 문서 품질 평가</p>
        </div>
        <div className="flex items-center gap-3">
          <span className={`rounded-full px-3 py-1 text-xs font-medium ${statusBadge}`}>
            {session.status.toUpperCase()}
          </span>
          {session.final_score != null && (
            <ScoreBadge score={session.final_score} label="최종" />
          )}
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <Stat label="반복 횟수" value={`${session.total_iterations}회`} />
        <Stat label="총 비용" value={`$${session.total_cost_usd.toFixed(2)}`} />
        <Stat
          label="최종 점수"
          value={session.final_score != null ? `${session.final_score.toFixed(1)}/5.0` : "-"}
        />
        <Stat
          label="Critical Flags"
          value={session.critical_flags?.length.toString() ?? "0"}
          danger={!!session.critical_flags?.length}
        />
      </div>

      {/* Section Scores */}
      {session.section_scores && Object.keys(session.section_scores).length > 0 && (
        <div>
          <h4 className="text-sm font-medium text-gray-700 mb-3">섹션별 점수</h4>
          <div className="grid grid-cols-2 gap-2 sm:grid-cols-5">
            {Object.entries(session.section_scores).map(([section, score]) => (
              <div key={section} className="rounded-lg border bg-gray-50 p-2 text-center">
                <p className="text-[10px] text-gray-500 truncate">{section}</p>
                <ScoreBadge score={score as number} />
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Score History Chart (simple) */}
      {progress?.score_history && progress.score_history.length > 1 && (
        <div>
          <h4 className="text-sm font-medium text-gray-700 mb-3">점수 추이</h4>
          <div className="flex items-end gap-1 h-20">
            {progress.score_history.map((point, i) => {
              const heightPct = (point.score / 5.0) * 100;
              const barColor =
                point.score >= 4.0
                  ? "bg-green-400"
                  : point.score >= 3.0
                    ? "bg-amber-400"
                    : "bg-red-400";
              return (
                <div
                  key={i}
                  className="flex flex-col items-center flex-1 gap-0.5"
                >
                  <span className="text-[9px] text-gray-400">{point.score.toFixed(1)}</span>
                  <div
                    className={`w-full rounded-t ${barColor}`}
                    style={{ height: `${heightPct}%` }}
                  />
                  <span className="text-[9px] text-gray-400">#{point.iteration}</span>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Gate Results */}
      {progress?.gate_results && progress.gate_results.length > 0 && (
        <div>
          <h4 className="text-sm font-medium text-gray-700 mb-3">
            최신 게이트 결과
          </h4>
          <div className="grid gap-4 sm:grid-cols-2">
            {progress.gate_results.map((gate, i) => (
              <GateResultCard key={i} gate={gate} />
            ))}
          </div>
        </div>
      )}

      {/* Critical Flags */}
      {session.critical_flags && session.critical_flags.length > 0 && (
        <div className="rounded-lg border-2 border-negative/30 bg-negative-light p-4">
          <h4 className="text-sm font-medium text-negative mb-2">Critical Flags</h4>
          <ul className="space-y-1">
            {session.critical_flags.map((flag, i) => (
              <li key={i} className="text-sm text-negative">• {flag}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

// ── Stat Helper ─────────────────────────────────────────────────────────────

function Stat({
  label,
  value,
  danger = false,
}: {
  label: string;
  value: string;
  danger?: boolean;
}) {
  return (
    <div className="rounded-lg border bg-white p-3">
      <p className="text-xs text-gray-500">{label}</p>
      <p className={`text-lg font-semibold ${danger ? "text-negative" : "text-gray-900"}`}>
        {value}
      </p>
    </div>
  );
}
