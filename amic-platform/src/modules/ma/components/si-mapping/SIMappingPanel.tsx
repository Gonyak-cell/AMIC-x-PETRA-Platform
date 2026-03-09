import { useCallback, useEffect, useId, useRef, useState } from "react";
import { toast } from "sonner";
import { X } from "lucide-react";

import { Button } from "@/components/ui/Button";
import { gsap } from "@/lib/gsap";
import EngagementDocUpload from "@/modules/ma/components/overview/EngagementDocUpload";
import {
  useBulkAddVcBuyers,
  useSICompanyByName,
  useVcMappingByRegistration,
  useVcMappingResult,
} from "@/modules/ma/hooks/useSIMapping";
import type { CorporateDocsExtractedData } from "@/modules/ma/types/document_extraction";

import SIDetailPanel from "./SIDetailPanel";
import VcMappingResult from "./VcMappingResult";

const FOCUSABLE_SELECTOR =
  'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])';

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
  // 딥다이브 — 기업명 기반 조회 (VC 기업 integer PK → SI 기업 UUID 변환)
  const [deepDiveName, setDeepDiveName] = useState<string | null>(null);
  const siLookup = useSICompanyByName(deepDiveName);
  const resolvedId = siLookup.data?.id ?? null;

  // VC 등록번호 매핑 (React Query 캐시로 모달 재열기 시 유지)
  const { data: vcResult } = useVcMappingResult(txnId);
  const vcMapMutation = useVcMappingByRegistration(txnId);

  // VC 기업 선택 상태 (Long List 추가용)
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());
  const bulkAddMutation = useBulkAddVcBuyers(txnId);
  const { mutate: bulkAddMutate, reset: resetBulkAdd } = bulkAddMutation;

  const handleToggle = useCallback((id: number) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }, []);

  const handleClearSelection = useCallback(() => {
    setSelectedIds(new Set());
    resetBulkAdd();
  }, [resetBulkAdd]);

  const handleBulkAdd = useCallback(() => {
    if (selectedIds.size === 0) return;
    if (selectedIds.size > 100) {
      toast.warning("최대 100건까지 일괄 등록할 수 있습니다.");
      return;
    }
    bulkAddMutate(
      { vc_company_ids: Array.from(selectedIds) },
      { onSuccess: () => setSelectedIds(new Set()) },
    );
  }, [selectedIds, bulkAddMutate]);

  // Refs
  const dialogRef = useRef<HTMLDialogElement>(null);
  const previousFocusRef = useRef<HTMLElement | null>(null);
  const contentRef = useRef<HTMLDivElement>(null);
  const backdropRef = useRef<HTMLDivElement>(null);
  const isClosingRef = useRef(false);
  const exitTlRef = useRef<gsap.core.Timeline | null>(null);

  // 접근성 — 고유 ID 생성
  const titleId = useId();

  // 퇴장 애니메이션 후 dialog.close() + onClose 호출
  const handleClose = useCallback(() => {
    if (isClosingRef.current) return;
    isClosingRef.current = true;

    const tl = gsap.timeline({
      onComplete: () => {
        dialogRef.current?.close();
        onClose();
        requestAnimationFrame(() => {
          previousFocusRef.current?.focus();
        });
      },
    });
    exitTlRef.current = tl;
    tl.to(contentRef.current, {
      scale: 0.95,
      opacity: 0,
      y: 12,
      duration: 0.25,
      ease: "power2.in",
    });
    tl.to(
      backdropRef.current,
      { opacity: 0, duration: 0.2, ease: "power2.in" },
      "-=0.15",
    );
  }, [onClose]);

  // 마운트 시 dialog.showModal() + GSAP 진입 애니메이션
  useEffect(() => {
    previousFocusRef.current = document.activeElement as HTMLElement;
    isClosingRef.current = false;
    dialogRef.current?.showModal();

    const tl = gsap.timeline();
    tl.fromTo(
      backdropRef.current,
      { opacity: 0 },
      { opacity: 1, duration: 0.3, ease: "power2.out" },
    );
    tl.fromTo(
      contentRef.current,
      { scale: 0.95, opacity: 0, y: 16 },
      { scale: 1, opacity: 1, y: 0, duration: 0.35, ease: "power3.out" },
      "-=0.15",
    );

    requestAnimationFrame(() => {
      const first =
        contentRef.current?.querySelector<HTMLElement>(FOCUSABLE_SELECTOR);
      first?.focus();
    });

    return () => {
      tl.kill();
      exitTlRef.current?.kill();
    };
  }, []);

  // 딥다이브 기업 조회 상태 처리 (loading → error/empty 통합)
  useEffect(() => {
    if (!deepDiveName) return;
    if (siLookup.isFetching) {
      const id = toast.loading("기업 정보 조회 중...");
      return () => {
        toast.dismiss(id);
      };
    }
    if (siLookup.isError) {
      toast.error("기업 정보 조회 중 오류가 발생했습니다.");
      setDeepDiveName(null);
    } else if (siLookup.isSuccess && !siLookup.data) {
      toast.info("해당 기업의 상세 정보를 조회할 수 없습니다.");
      setDeepDiveName(null);
    }
  }, [
    deepDiveName,
    siLookup.isFetching,
    siLookup.isError,
    siLookup.isSuccess,
    siLookup.data,
  ]);

  const corpRegNo = corporateInfo?.corporate_registration_number ?? undefined;
  const bizRegNo = corporateInfo?.business_registration_number ?? undefined;
  const hasRegNo = !!(corpRegNo || bizRegNo);

  const { mutate: runVcMapping } = vcMapMutation;
  const handleVcMapping = useCallback(() => {
    runVcMapping({ corp_reg_no: corpRegNo, biz_reg_no: bizRegNo });
  }, [corpRegNo, bizRegNo, runVcMapping]);

  return (
    <dialog
      ref={dialogRef}
      className="fixed inset-0 z-50 bg-transparent p-0 m-0 max-w-none max-h-none w-full h-full backdrop:bg-transparent"
      onCancel={(e) => {
        e.preventDefault();
        handleClose();
      }}
      aria-labelledby={titleId}
    >
      {/* 백드롭 (애니메이션용 별도 레이어) */}
      <div
        ref={backdropRef}
        className="fixed inset-0 bg-amic-900/70 backdrop-blur-sm"
        style={{ opacity: 0 }}
        onClick={handleClose}
      />

      {/* 모달 콘텐츠 */}
      <div className="relative flex min-h-screen items-center justify-center p-4">
        <div
          ref={contentRef}
          className="relative flex max-h-[90vh] w-full max-w-6xl flex-col rounded-2xl bg-white shadow-2xl"
          style={{ opacity: 0 }}
          onClick={(e) => e.stopPropagation()}
        >
          {/* 헤더 */}
          <div className="flex items-center justify-between border-b border-slate-200 px-6 py-4">
            <div>
              <h2 id={titleId} className="text-lg font-bold text-slate-800">
                SI 자동 매핑
              </h2>
              <p className="text-sm text-slate-500">
                법인정보 기반 Value Chain 자동 매핑
              </p>
            </div>
            <Button
              variant="ghost"
              size="sm"
              onClick={handleClose}
              className="p-1.5"
              aria-label="SI 매핑 패널 닫기"
            >
              <X className="h-5 w-5" />
            </Button>
          </div>

          {/* 본문 (스크롤) */}
          <div className="flex-1 overflow-y-auto px-6 py-4">
            {/* VC 자동 매핑 (법인정보 기반) */}
            {hasRegNo ? (
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
                    aria-busy={vcMapMutation.isPending}
                    className="rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-700 disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    {vcMapMutation.isPending
                      ? "매핑 중..."
                      : "Value Chain 매핑 실행"}
                  </button>
                )}
                {vcMapMutation.isError && (
                  <div role="alert" className="mt-2 space-y-0.5">
                    <p className="text-sm text-red-600">
                      {vcMapMutation.error.message}
                    </p>
                    <p className="text-xs text-red-500">
                      잠시 후 다시 시도해 주세요.
                    </p>
                  </div>
                )}
                {vcResult && (
                  <VcMappingResult
                    company={vcResult.company}
                    mapping={vcResult.mapping}
                    onCompanyClick={setDeepDiveName}
                    selectedIds={selectedIds}
                    onToggle={handleToggle}
                    onClearSelection={handleClearSelection}
                  />
                )}
              </div>
            ) : (
              <div className="mb-6 rounded-lg border border-amber-200 bg-amber-50/30 p-4">
                <div className="mb-3">
                  <h3 className="mb-0.5 text-sm font-semibold text-amber-800">
                    법인정보 기반 Value Chain 매핑
                  </h3>
                  <p className="text-xs text-amber-700">
                    자동 매핑을 위해 법인등기부등본 또는 사업자등록증을
                    업로드하세요. 업로드 후 Overview의 법인 정보도 자동으로
                    업데이트됩니다.
                  </p>
                </div>
                <EngagementDocUpload txnId={txnId} />
              </div>
            )}

            {/* KSIC 기반 SI 매핑 — 현재 비활성화 */}
          </div>

          {/* 푸터 */}
          <div className="flex items-center justify-between border-t border-slate-200 px-6 py-3">
            <Button variant="ghost" size="sm" onClick={handleClose}>
              닫기
            </Button>
            <div className="flex items-center gap-3">
              {bulkAddMutation.isError && (
                <p role="alert" className="text-sm text-red-600">
                  {bulkAddMutation.error.message}
                </p>
              )}
              {vcResult && selectedIds.size > 0 && (
                <button
                  type="button"
                  onClick={handleBulkAdd}
                  disabled={bulkAddMutation.isPending}
                  aria-busy={bulkAddMutation.isPending}
                  className="rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-700 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  {bulkAddMutation.isPending
                    ? "등록 중..."
                    : `선택 항목 Long List에 추가 (${selectedIds.size}개)`}
                </button>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* 기업 상세 패널 */}
      <SIDetailPanel
        companyId={resolvedId}
        onClose={() => setDeepDiveName(null)}
      />
    </dialog>
  );
}
