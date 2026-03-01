import { useCallback, useMemo, useState } from "react";

import { cn } from "@/lib/cn";
import type {
  SICandidate,
  SICompanyRelation,
} from "@/modules/ma/types/si_mapping";
import { formatRevenue } from "@/modules/ma/utils/format";

const RELATION_CONFIG: Record<
  SICompanyRelation,
  { label: string; badgeCls: string }
> = {
  DIRECT: { label: "동종업계", badgeCls: "bg-blue-100 text-blue-700" },
  BACKWARD: { label: "공급자", badgeCls: "bg-orange-100 text-orange-700" },
  FORWARD: { label: "수요자", badgeCls: "bg-green-100 text-green-700" },
};

interface SICandidateTableProps {
  candidates: SICandidate[];
  selectedIds: Set<string>;
  onToggle: (id: string) => void;
  onToggleAll: () => void;
  onCompanyClick?: (id: string) => void;
}

export default function SICandidateTable({
  candidates,
  selectedIds,
  onToggle,
  onToggleAll,
  onCompanyClick,
}: SICandidateTableProps) {
  const [relationFilter, setRelationFilter] = useState<
    SICompanyRelation | "ALL"
  >("ALL");

  const filtered = useMemo(
    () =>
      relationFilter === "ALL"
        ? candidates
        : candidates.filter((c) => c.relation === relationFilter),
    [candidates, relationFilter],
  );

  const allSelected =
    filtered.length > 0 && filtered.every((c) => selectedIds.has(c.company.id));

  const handleToggleAll = useCallback(() => {
    onToggleAll();
  }, [onToggleAll]);

  if (candidates.length === 0) {
    return (
      <div className="py-8 text-center text-sm text-slate-400">
        매핑 결과가 없습니다.
      </div>
    );
  }

  return (
    <div>
      {/* 필터 */}
      <div className="mb-3 flex items-center gap-2">
        <span className="text-xs font-medium text-slate-500">필터:</span>
        {(["ALL", "DIRECT", "BACKWARD", "FORWARD"] as const).map((key) => {
          const isActive = relationFilter === key;
          const count =
            key === "ALL"
              ? candidates.length
              : candidates.filter((c) => c.relation === key).length;
          return (
            <button
              key={key}
              type="button"
              onClick={() => setRelationFilter(key)}
              className={cn(
                "rounded-full px-2.5 py-1 text-xs font-medium transition-colors",
                isActive
                  ? "bg-slate-800 text-white"
                  : "bg-slate-100 text-slate-600 hover:bg-slate-200",
              )}
            >
              {key === "ALL" ? "전체" : RELATION_CONFIG[key].label} ({count})
            </button>
          );
        })}
      </div>

      {/* 테이블 */}
      <div className="overflow-x-auto rounded-lg border border-slate-200">
        <table className="w-full text-left text-sm">
          <thead className="border-b border-slate-200 bg-slate-50">
            <tr>
              <th className="w-10 px-3 py-2">
                <input
                  type="checkbox"
                  checked={allSelected}
                  onChange={handleToggleAll}
                  className="rounded border-slate-300"
                />
              </th>
              <th className="min-w-[140px] px-3 py-2 font-medium text-slate-600">
                기업명
              </th>
              <th className="w-[100px] px-3 py-2 font-medium text-slate-600">
                KSIC
              </th>
              <th className="w-[100px] px-3 py-2 text-right font-medium text-slate-600">
                매출액
              </th>
              <th className="w-[64px] px-3 py-2 font-medium text-slate-600">
                투자이력
              </th>
              <th className="w-[80px] px-3 py-2 font-medium text-slate-600">
                관계
              </th>
              <th className="min-w-[100px] px-3 py-2 font-medium text-slate-600">
                산업(IO)
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {filtered.map((c) => {
              const rel = RELATION_CONFIG[c.relation];
              const isChecked = selectedIds.has(c.company.id);
              return (
                <tr
                  key={c.company.id}
                  className={cn(
                    "transition-colors hover:bg-slate-50",
                    isChecked && "bg-emerald-50/50",
                  )}
                >
                  <td className="px-3 py-2">
                    <input
                      type="checkbox"
                      checked={isChecked}
                      onChange={() => onToggle(c.company.id)}
                      className="rounded border-slate-300"
                    />
                  </td>
                  <td className="px-3 py-2 font-medium text-slate-800">
                    <button
                      type="button"
                      onClick={() => onCompanyClick?.(c.company.id)}
                      className="text-left hover:text-emerald-600 hover:underline"
                    >
                      {c.company.company_name}
                    </button>
                  </td>
                  <td className="px-3 py-2">
                    <div className="flex flex-wrap gap-1">
                      {c.company.ksic_codes?.map((code) => (
                        <span
                          key={code}
                          className="rounded bg-slate-100 px-1 py-0.5 text-xs text-slate-600"
                        >
                          {code}
                        </span>
                      ))}
                    </div>
                  </td>
                  <td className="px-3 py-2 text-right tabular-nums text-slate-700">
                    {formatRevenue(c.company.revenue, c.company.revenue_year)}
                  </td>
                  <td className="px-3 py-2">
                    {c.company.has_investment_history ? (
                      <span className="text-xs font-medium text-emerald-600">
                        있음
                      </span>
                    ) : (
                      <span className="text-xs text-slate-400">없음</span>
                    )}
                  </td>
                  <td className="px-3 py-2">
                    <span
                      className={cn(
                        "inline-block whitespace-nowrap rounded-full px-2 py-0.5 text-xs font-medium",
                        rel.badgeCls,
                      )}
                    >
                      {rel.label}
                    </span>
                  </td>
                  <td className="px-3 py-2 text-xs text-slate-500">
                    {c.io_name || "-"}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <div className="mt-2 text-right text-xs text-slate-500">
        {selectedIds.size}개 선택됨 / 총 {filtered.length}개
      </div>
    </div>
  );
}
