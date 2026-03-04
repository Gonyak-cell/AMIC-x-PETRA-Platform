import { useCallback, useEffect, useRef, useState } from "react";

import {
  useBulkAddBuyers,
  useSIMapping,
  useVcMappingByRegistration,
} from "@/modules/ma/hooks/useSIMapping";
import type { CorporateDocsExtractedData } from "@/modules/ma/types/document_extraction";
import type {
  KsicSuggestion,
  SIMappingResponse,
  VcMappingByRegResponse,
} from "@/modules/ma/types/si_mapping";

import KsicSearchInput from "./KsicSearchInput";
import SICandidateTable from "./SICandidateTable";
import SIDetailPanel from "./SIDetailPanel";
import ValueChainDiagram from "./ValueChainDiagram";
import VcMappingResult from "./VcMappingResult";

interface SIMappingPanelProps {
  txnId: string;
  onClose: () => void;
  corporateInfo?: CorporateDocsExtractedData | null;
}

export default function SIMappingPanel({
  txnId,
  onClose,
  corporateInfo,
}: SIMappingPanelProps) {
  // 검색 상태
  const [selectedKsic, setSelectedKsic] = useState<KsicSuggestion[]>([]);
  const [topN, setTopN] = useState(5);

  // 매핑 결과
  const [mappingResult, setMappingResult] = useState<SIMappingResponse | null>(
    null,
  );

  // 선택된 기업 ID
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());

  // 딥다이브 Drawer
  const [deepDiveId, setDeepDiveId] = useState<string | null>(null);

  // VC 등록번호 매핑
  const [vcResult, setVcResult] = useState<VcMappingByRegResponse | null>(null);
  const vcMapMutation = useVcMappingByRegistration();

  // Focus trap ref
  const panelRef = useRef<HTMLDivElement>(null);
  const previousFocusRef = useRef<HTMLElement | null>(null);

  // 모달 열릴 때 이전 포커스 저장 + 닫힐 때 복원
  useEffect(() => {
    previousFocusRef.current = document.activeElement as HTMLElement;
    return () => {
      previousFocusRef.current?.focus();
    };
  }, []);

  // Escape 키 핸들러 — 하위 패널이 열려 있으면 그것만 닫기
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        if (deepDiveId) {
          setDeepDiveId(null);
        } else {
          onClose();
        }
      }
    };
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [onClose, deepDiveId]);

  // Body scroll lock
  useEffect(() => {
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = "";
    };
  }, []);

  // Focus trap
  useEffect(() => {
    const panel = panelRef.current;
    if (!panel) return;

    const FOCUSABLE =
      'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])';
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key !== "Tab") return;
      const focusable = panel.querySelectorAll<HTMLElement>(FOCUSABLE);
      if (focusable.length === 0) return;
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (e.shiftKey && document.activeElement === first) {
        e.preventDefault();
        last.focus();
      } else if (!e.shiftKey && document.activeElement === last) {
        e.preventDefault();
        first.focus();
      }
    };

    panel.addEventListener("keydown", handleKeyDown);
    requestAnimationFrame(() => {
      const first = panel.querySelector<HTMLElement>(FOCUSABLE);
      first?.focus();
    });
    return () => panel.removeEventListener("keydown", handleKeyDown);
  }, []);

  const corpRegNo = corporateInfo?.corporate_registration_number ?? undefined;
  const bizRegNo = corporateInfo?.business_registration_number ?? undefined;
  const hasRegNo = !!(corpRegNo || bizRegNo);

  const { mutate: runVcMapping } = vcMapMutation;
  const handleVcMapping = useCallback(() => {
    runVcMapping(
      { corp_reg_no: corpRegNo, biz_reg_no: bizRegNo },
      { onSuccess: (data) => setVcResult(data) },
    );
  }, [corpRegNo, bizRegNo, runVcMapping]);

  // Mutations
  const mapMutation = useSIMapping();
  const bulkAddMutation = useBulkAddBuyers(txnId);

  const { mutate: runMapping } = mapMutation;
  const handleRunMapping = useCallback(() => {
    if (selectedKsic.length === 0) return;
    runMapping(
      {
        ksic_codes: selectedKsic.map((s) => s.code),
        top_n: topN,
      },
      {
        onSuccess: (data) => {
          setMappingResult(data);
          setSelectedIds(new Set());
        },
      },
    );
  }, [selectedKsic, topN, runMapping]);

  const handleToggle = useCallback((id: string) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }, []);

  const handleToggleAll = useCallback((filteredIds: string[]) => {
    setSelectedIds((prev) => {
      const allSelected = filteredIds.every((id) => prev.has(id));
      if (allSelected) {
        const next = new Set(prev);
        filteredIds.forEach((id) => next.delete(id));
        return next;
      }
      const next = new Set(prev);
      filteredIds.forEach((id) => next.add(id));
      return next;
    });
  }, []);

  const { mutate: runBulkAdd } = bulkAddMutation;
  const handleBulkAdd = useCallback(() => {
    if (selectedIds.size === 0) return;
    runBulkAdd(
      { si_company_ids: Array.from(selectedIds) },
      { onSuccess: () => setSelectedIds(new Set()) },
    );
  }, [selectedIds, runBulkAdd]);

  return (
    <div
      ref={panelRef}
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="si-mapping-title"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div className="flex max-h-[90vh] w-full max-w-6xl flex-col rounded-2xl bg-white shadow-2xl">
        {/* 헤더 */}
        <div className="flex items-center justify-between border-b border-slate-200 px-6 py-4">
          <div>
            <h2
              id="si-mapping-title"
              className="text-lg font-bold text-slate-800"
            >
              SI 자동 매핑
            </h2>
            <p className="text-sm text-slate-500">
              KSIC 코드 기반 전략적 투자자 후보 자동 도출
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="SI 매핑 패널 닫기"
            className="rounded-lg p-2 text-slate-400 hover:bg-slate-100 hover:text-slate-600"
          >
            <svg
              aria-hidden="true"
              className="h-5 w-5"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
          </button>
        </div>

        {/* 본문 (스크롤) */}
        <div className="flex-1 overflow-y-auto px-6 py-4">
          {/* VC 자동 매핑 (법인정보 기반) */}
          {hasRegNo && (
            <div className="mb-6 rounded-lg border border-emerald-200 bg-emerald-50/30 p-4">
              <h3 className="mb-2 text-sm font-semibold text-emerald-800">
                법인정보 기반 Value Chain 매핑
              </h3>
              <div className="mb-3 flex flex-wrap items-center gap-x-6 gap-y-1 text-xs text-emerald-700">
                {corpRegNo && <span>법인등록번호: {corpRegNo}</span>}
                {bizRegNo && <span>사업자등록번호: {bizRegNo}</span>}
              </div>
              {!vcResult && (
                <button
                  type="button"
                  onClick={handleVcMapping}
                  disabled={vcMapMutation.isPending}
                  className="rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-700 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  {vcMapMutation.isPending
                    ? "매핑 중..."
                    : "Value Chain 매핑 실행"}
                </button>
              )}
              {vcMapMutation.isError && (
                <p role="alert" className="mt-2 text-sm text-red-600">
                  {vcMapMutation.error.message}
                </p>
              )}
              {vcResult && (
                <VcMappingResult
                  txnId={txnId}
                  company={vcResult.company}
                  mapping={vcResult.mapping}
                />
              )}
            </div>
          )}

          {/* KSIC 기반 SI 매핑 */}
          {hasRegNo && (
            <div className="mb-3">
              <h3 className="text-sm font-semibold text-slate-600">
                KSIC 기반 SI 매핑
              </h3>
            </div>
          )}

          {/* 검색 영역 */}
          <div className="mb-6 rounded-lg border border-slate-200 bg-slate-50/50 p-4">
            <div className="grid grid-cols-[1fr_auto_auto] items-end gap-4">
              <KsicSearchInput
                selectedCodes={selectedKsic}
                onSelect={setSelectedKsic}
              />
              <div>
                <label className="mb-1.5 block text-sm font-medium text-slate-700">
                  Top-N
                </label>
                <select
                  value={topN}
                  onChange={(e) => setTopN(Number(e.target.value))}
                  className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm"
                >
                  {[3, 5, 10, 15, 20].map((n) => (
                    <option key={n} value={n}>
                      {n}개
                    </option>
                  ))}
                </select>
              </div>
              <button
                type="button"
                onClick={handleRunMapping}
                disabled={selectedKsic.length === 0 || mapMutation.isPending}
                className="rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-700 disabled:cursor-not-allowed disabled:opacity-50"
              >
                {mapMutation.isPending ? "매핑 중..." : "매핑 실행"}
              </button>
            </div>
            {mapMutation.isError && (
              <p role="alert" className="mt-2 text-sm text-red-600">
                {mapMutation.error.message}
              </p>
            )}
          </div>

          {/* 결과 영역 */}
          {mappingResult && (
            <>
              {/* Value Chain 다이어그램 */}
              <div className="mb-6">
                <h3 className="mb-3 text-sm font-semibold text-slate-700">
                  Value Chain 구조
                </h3>
                <ValueChainDiagram
                  directPeers={mappingResult.direct_peers}
                  backwardChain={mappingResult.backward_chain}
                  forwardChain={mappingResult.forward_chain}
                  targetKsicCodes={mappingResult.target_ksic_codes}
                />
              </div>

              {/* 후보 테이블 */}
              <div>
                <h3 className="mb-3 text-sm font-semibold text-slate-700">
                  SI 후보 기업 ({mappingResult.all_candidates.length}개)
                </h3>
                <SICandidateTable
                  candidates={mappingResult.all_candidates}
                  selectedIds={selectedIds}
                  onToggle={handleToggle}
                  onToggleAll={handleToggleAll}
                  onCompanyClick={setDeepDiveId}
                />
              </div>
            </>
          )}
        </div>

        {/* 푸터 */}
        <div className="flex items-center justify-between border-t border-slate-200 px-6 py-3">
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg border border-slate-200 px-4 py-2 text-sm text-slate-600 hover:bg-slate-50"
          >
            닫기
          </button>
          {mappingResult && (
            <div className="flex items-center gap-3">
              {bulkAddMutation.isError && (
                <p role="alert" className="text-sm text-red-600">
                  {bulkAddMutation.error.message}
                </p>
              )}
              <button
                type="button"
                onClick={handleBulkAdd}
                disabled={selectedIds.size === 0 || bulkAddMutation.isPending}
                className="rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-700 disabled:cursor-not-allowed disabled:opacity-50"
              >
                {bulkAddMutation.isPending
                  ? "등록 중..."
                  : `선택 항목 Long List에 추가 (${selectedIds.size}개)`}
              </button>
            </div>
          )}
        </div>
      </div>

      {/* 기업 상세 패널 */}
      <SIDetailPanel
        companyId={deepDiveId}
        onClose={() => setDeepDiveId(null)}
      />
    </div>
  );
}
