import { cn } from "@/lib/cn";
import type {
  SICompany,
  ValueChainPanel as VCPanel,
} from "@/modules/ma/types/si_mapping";
import { formatRevenue } from "@/modules/ma/utils/format";

interface ValueChainDiagramProps {
  directPeers: SICompany[];
  backwardChain: VCPanel[];
  forwardChain: VCPanel[];
  targetKsicCodes: string[];
}

function PanelCard({
  panel,
  color,
}: {
  panel: VCPanel;
  color: "orange" | "green";
}) {
  const colorCls =
    color === "orange"
      ? "border-orange-200 bg-orange-50"
      : "border-green-200 bg-green-50";
  const badgeCls =
    color === "orange"
      ? "bg-orange-100 text-orange-700"
      : "bg-green-100 text-green-700";

  return (
    <div className={cn("rounded-lg border p-3", colorCls)}>
      <div className="mb-1.5 flex items-center justify-between">
        <span
          className={cn(
            "rounded px-1.5 py-0.5 text-xs font-semibold",
            badgeCls,
          )}
        >
          {panel.io_code}
        </span>
        <span className="text-xs text-slate-500">
          거래액 {formatRevenue(panel.transaction_value)}
        </span>
      </div>
      <p className="mb-2 text-sm font-medium text-slate-700">{panel.io_name}</p>
      <p className="text-xs text-slate-500">{panel.companies.length}개 기업</p>
    </div>
  );
}

export default function ValueChainDiagram({
  directPeers,
  backwardChain,
  forwardChain,
  targetKsicCodes,
}: ValueChainDiagramProps) {
  return (
    <div className="grid grid-cols-[1fr_auto_1fr_auto_1fr] items-start gap-2">
      {/* 왼쪽: 후방산업 (공급자) */}
      <div>
        <h4 className="mb-2 text-center text-xs font-semibold uppercase tracking-wider text-orange-600">
          후방산업 (공급자)
        </h4>
        <div className="space-y-2">
          {backwardChain.length > 0 ? (
            backwardChain.map((p) => (
              <PanelCard key={p.io_code} panel={p} color="orange" />
            ))
          ) : (
            <p className="text-center text-xs text-slate-400">데이터 없음</p>
          )}
        </div>
      </div>

      {/* 화살표 → */}
      <div className="flex h-full items-center pt-6">
        <div className="h-px w-6 bg-slate-300" />
        <div className="h-0 w-0 border-y-4 border-l-6 border-y-transparent border-l-slate-300" />
      </div>

      {/* 중앙: 타겟/동종업계 */}
      <div>
        <h4 className="mb-2 text-center text-xs font-semibold uppercase tracking-wider text-blue-600">
          타겟 / 동종업계
        </h4>
        <div className="rounded-lg border border-blue-200 bg-blue-50 p-3">
          <div className="mb-2 flex flex-wrap gap-1">
            {targetKsicCodes.map((code) => (
              <span
                key={code}
                className="rounded bg-blue-100 px-1.5 py-0.5 text-xs font-semibold text-blue-700"
              >
                {code}
              </span>
            ))}
          </div>
          <p className="text-sm font-medium text-slate-700">
            동종업계 {directPeers.length}개 기업
          </p>
        </div>
      </div>

      {/* 화살표 → */}
      <div className="flex h-full items-center pt-6">
        <div className="h-px w-6 bg-slate-300" />
        <div className="h-0 w-0 border-y-4 border-l-6 border-y-transparent border-l-slate-300" />
      </div>

      {/* 오른쪽: 전방산업 (수요자) */}
      <div>
        <h4 className="mb-2 text-center text-xs font-semibold uppercase tracking-wider text-green-600">
          전방산업 (수요자)
        </h4>
        <div className="space-y-2">
          {forwardChain.length > 0 ? (
            forwardChain.map((p) => (
              <PanelCard key={p.io_code} panel={p} color="green" />
            ))
          ) : (
            <p className="text-center text-xs text-slate-400">데이터 없음</p>
          )}
        </div>
      </div>
    </div>
  );
}
