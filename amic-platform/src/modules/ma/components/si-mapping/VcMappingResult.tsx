import { memo, useCallback, useState } from "react";
import { toast } from "sonner";

import { useBulkAddVcBuyers } from "@/modules/ma/hooks/useSIMapping";
import type {
  VcChainCompany,
  VcChainPanel,
  VcCompanyLookupResult,
  VcMappingResponse,
} from "@/modules/ma/types/si_mapping";
import { formatBillions } from "@/modules/ma/utils/format";

type VcTab = "forward" | "backward" | "competitors";

interface VcMappingResultProps {
  txnId: string;
  company: VcCompanyLookupResult;
  mapping: VcMappingResponse;
}

const CompanyRow = memo(function CompanyRow({
  company,
  checked,
  onToggle,
}: {
  company: VcChainCompany;
  checked: boolean;
  onToggle: (id: number) => void;
}) {
  return (
    <tr className="border-b border-slate-100 last:border-b-0 hover:bg-slate-50/50">
      <td className="px-3 py-2">
        <input
          type="checkbox"
          aria-label={`${company.company_name} 선택`}
          checked={checked}
          onChange={() => onToggle(company.id)}
          className="h-4 w-4 rounded border-slate-300 accent-emerald-600"
        />
      </td>
      <td className="px-3 py-2 text-sm font-medium text-slate-800">
        {company.company_name}
      </td>
      <td className="px-3 py-2 text-sm text-slate-600">
        {company.industry_name}
      </td>
      <td className="px-3 py-2 text-right text-sm text-slate-600">
        {formatBillions(company.revenue)}
      </td>
      <td className="px-3 py-2 text-sm text-slate-500">
        {company.corp_type ?? "-"}
      </td>
    </tr>
  );
});

const ChainPanelCard = memo(function ChainPanelCard({
  panel,
  selectedIds,
  onToggle,
}: {
  panel: VcChainPanel;
  selectedIds: Set<number>;
  onToggle: (id: number) => void;
}) {
  const [expanded, setExpanded] = useState(true);
  const coeff = Number(panel.coefficient);
  const coeffDisplay = Number.isNaN(coeff)
    ? panel.coefficient
    : coeff.toFixed(4);

  return (
    <div className="rounded-lg border border-slate-200 bg-white">
      <button
        type="button"
        onClick={() => setExpanded(!expanded)}
        aria-expanded={expanded}
        className="flex w-full items-center justify-between px-4 py-3 text-left hover:bg-slate-50"
      >
        <div className="flex items-center gap-3">
          <span className="text-sm font-semibold text-slate-700">
            {panel.industry_name}
          </span>
          <span className="rounded-full bg-emerald-50 px-2 py-0.5 text-xs font-medium text-emerald-700">
            계수 {coeffDisplay}
          </span>
          <span className="text-xs text-slate-400">
            {panel.companies.length}개 기업
          </span>
        </div>
        <svg
          aria-hidden="true"
          className={`h-4 w-4 text-slate-400 transition-transform ${expanded ? "rotate-180" : ""}`}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M19 9l-7 7-7-7"
          />
        </svg>
      </button>
      {expanded && panel.companies.length > 0 && (
        <table className="w-full">
          <thead>
            <tr className="border-t border-slate-100 bg-slate-50/50 text-xs text-slate-500">
              <th scope="col" className="w-10 px-3 py-2">
                <span className="sr-only">선택</span>
              </th>
              <th scope="col" className="px-3 py-2 text-left font-medium">
                기업명
              </th>
              <th scope="col" className="px-3 py-2 text-left font-medium">
                업종
              </th>
              <th scope="col" className="px-3 py-2 text-right font-medium">
                매출
              </th>
              <th scope="col" className="px-3 py-2 text-left font-medium">
                법인구분
              </th>
            </tr>
          </thead>
          <tbody>
            {panel.companies.map((c) => (
              <CompanyRow
                key={c.id}
                company={c}
                checked={selectedIds.has(c.id)}
                onToggle={onToggle}
              />
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
});

const TAB_CONFIG: { key: VcTab; label: string }[] = [
  { key: "forward", label: "전방 (고객)" },
  { key: "backward", label: "후방 (공급)" },
  { key: "competitors", label: "경쟁사" },
];

export default function VcMappingResult({
  txnId,
  company,
  mapping,
}: VcMappingResultProps) {
  const [activeTab, setActiveTab] = useState<VcTab>("forward");
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());
  const bulkAddMutation = useBulkAddVcBuyers(txnId);

  const handleToggle = useCallback((id: number) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }, []);

  const handleBulkAdd = () => {
    if (selectedIds.size === 0) return;
    const MAX_BULK = 100;
    if (selectedIds.size > MAX_BULK) {
      toast.warning(`최대 ${MAX_BULK}건까지 일괄 등록할 수 있습니다.`);
      return;
    }
    bulkAddMutation.mutate(
      { vc_company_ids: Array.from(selectedIds) },
      { onSuccess: () => setSelectedIds(new Set()) },
    );
  };

  const panelsMap: Record<VcTab, VcChainPanel[]> = {
    forward: mapping.forward_chains,
    backward: mapping.backward_chains,
    competitors: [],
  };
  const countMap: Record<VcTab, number> = {
    forward: mapping.total_forward,
    backward: mapping.total_backward,
    competitors: mapping.total_competitors,
  };
  const currentPanels = panelsMap[activeTab];
  const currentCount = countMap[activeTab];

  return (
    <div className="space-y-4">
      {/* 조회 기업 정보 */}
      <div className="flex items-center gap-4 rounded-lg border border-emerald-200 bg-emerald-50/50 px-4 py-3">
        <div className="flex-1">
          <div className="flex items-center gap-2">
            <span className="text-sm font-semibold text-emerald-800">
              {company.company_name}
            </span>
            <span className="rounded bg-emerald-100 px-1.5 py-0.5 text-xs text-emerald-700">
              {company.industry_name}
            </span>
          </div>
          <div className="mt-1 flex gap-4 text-xs text-emerald-600">
            {company.corp_reg_no && (
              <span>법인등록번호: {company.corp_reg_no}</span>
            )}
            {company.biz_reg_no && (
              <span>사업자등록번호: {company.biz_reg_no}</span>
            )}
            {company.revenue && (
              <span>매출: {formatBillions(company.revenue)}</span>
            )}
          </div>
        </div>
      </div>

      {/* 탭 */}
      <div role="tablist" className="flex gap-1 rounded-lg bg-slate-100 p-1">
        {TAB_CONFIG.map(({ key, label }) => (
          <button
            key={key}
            id={`vc-tab-${key}`}
            role="tab"
            aria-selected={activeTab === key}
            aria-controls={`vc-tabpanel-${key}`}
            type="button"
            onClick={() => {
              setActiveTab(key);
              setSelectedIds(new Set());
            }}
            className={`flex-1 rounded-md px-3 py-2 text-sm font-medium transition-colors ${
              activeTab === key
                ? "bg-white text-slate-800 shadow-sm"
                : "text-slate-500 hover:text-slate-700"
            }`}
          >
            {label} ({countMap[key]})
          </button>
        ))}
      </div>

      {/* 패널 목록 또는 경쟁사 테이블 */}
      <div
        role="tabpanel"
        id={`vc-tabpanel-${activeTab}`}
        aria-labelledby={`vc-tab-${activeTab}`}
        className="space-y-3"
      >
        {activeTab === "competitors" ? (
          mapping.competitors.length > 0 ? (
            <div className="rounded-lg border border-slate-200 bg-white">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-slate-100 bg-slate-50/50 text-xs text-slate-500">
                    <th scope="col" className="w-10 px-3 py-2">
                      <span className="sr-only">선택</span>
                    </th>
                    <th scope="col" className="px-3 py-2 text-left font-medium">
                      기업명
                    </th>
                    <th scope="col" className="px-3 py-2 text-left font-medium">
                      업종
                    </th>
                    <th
                      scope="col"
                      className="px-3 py-2 text-right font-medium"
                    >
                      매출
                    </th>
                    <th scope="col" className="px-3 py-2 text-left font-medium">
                      법인구분
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {mapping.competitors.map((c) => (
                    <CompanyRow
                      key={c.id}
                      company={c}
                      checked={selectedIds.has(c.id)}
                      onToggle={handleToggle}
                    />
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="py-8 text-center text-sm text-slate-400">
              경쟁사 데이터가 없습니다.
            </p>
          )
        ) : currentPanels.length > 0 ? (
          currentPanels.map((panel) => (
            <ChainPanelCard
              key={`${activeTab}-${panel.industry_name}`}
              panel={panel}
              selectedIds={selectedIds}
              onToggle={handleToggle}
            />
          ))
        ) : (
          <p className="py-8 text-center text-sm text-slate-400">
            {activeTab === "forward" ? "전방" : "후방"} 연관 데이터가 없습니다.
            ({currentCount}개)
          </p>
        )}
      </div>

      {/* Long List 등록 버튼 */}
      <div
        aria-hidden={selectedIds.size === 0}
        className={`flex justify-end transition-opacity ${selectedIds.size > 0 ? "opacity-100" : "pointer-events-none opacity-0"}`}
      >
        <button
          type="button"
          onClick={handleBulkAdd}
          disabled={bulkAddMutation.isPending || selectedIds.size === 0}
          className="rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-700 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {bulkAddMutation.isPending
            ? "등록 중..."
            : `선택 항목 Long List에 추가 (${selectedIds.size}개)`}
        </button>
      </div>
    </div>
  );
}
