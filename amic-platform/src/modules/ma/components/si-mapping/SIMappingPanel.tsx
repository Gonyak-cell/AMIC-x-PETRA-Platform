import { useCallback, useEffect, useId, useRef, useState } from "react";

import { gsap } from "@/lib/gsap";
import EngagementDocUpload from "@/modules/ma/components/overview/EngagementDocUpload";
import { useVcMappingByRegistration } from "@/modules/ma/hooks/useSIMapping";
import type { CorporateDocsExtractedData } from "@/modules/ma/types/document_extraction";
import type { VcMappingByRegResponse } from "@/modules/ma/types/si_mapping";

import SIDetailPanel from "./SIDetailPanel";
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
  // 딥다이브 Drawer
  const [deepDiveId, setDeepDiveId] = useState<string | null>(null);

  // VC 등록번호 매핑
  const [vcResult, setVcResult] = useState<VcMappingByRegResponse | null>(null);
  const vcMapMutation = useVcMappingByRegistration();

  // Focus trap ref (wrapper 전체)
  const panelRef = useRef<HTMLDivElement>(null);
  const previousFocusRef = useRef<HTMLElement | null>(null);

  // GSAP 애니메이션 ref
  const backdropRef = useRef<HTMLDivElement>(null);
  const contentRef = useRef<HTMLDivElement>(null);
  const isClosingRef = useRef(false);

  // 접근성 — 고유 ID 생성 (중복 ID 방지)
  const titleId = useId();

  // 퇴장 애니메이션 후 onClose 호출
  const handleClose = useCallback(() => {
    if (isClosingRef.current) return;
    isClosingRef.current = true;

    const tl = gsap.timeline({
      onComplete: () => {
        const elToFocus = previousFocusRef.current;
        onClose();
        requestAnimationFrame(() => {
          elToFocus?.focus();
        });
      },
    });
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

  // 모달 열릴 때 이전 포커스 저장
  useEffect(() => {
    previousFocusRef.current = document.activeElement as HTMLElement;
  }, []);

  // 진입 애니메이션 (Modal.tsx 패턴과 동일)
  useEffect(() => {
    isClosingRef.current = false;
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
    return () => {
      tl.kill();
    };
  }, []);

  // Escape 키 핸들러 — deepDiveId 활성화 시 SlidePanel이 자체 cancel 이벤트로 처리
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        // deepDiveId 활성화 → SlidePanel(dialog top layer)이 자체 cancel 이벤트로 처리
        if (deepDiveId) return;
        handleClose();
      }
    };
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [handleClose, deepDiveId]);

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

  return (
    <div
      ref={panelRef}
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby={titleId}
    >
      {/* 백드롭 (애니메이션용 별도 레이어 — 직접 onClick으로 닫기) */}
      <div
        ref={backdropRef}
        className="fixed inset-0 bg-amic-900/70 backdrop-blur-sm"
        style={{ opacity: 0 }}
        onClick={handleClose}
      />

      {/* 모달 콘텐츠 */}
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
          <button
            type="button"
            onClick={handleClose}
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
                  onCompanyClick={(id) => setDeepDiveId(id)}
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
          <button
            type="button"
            onClick={handleClose}
            className="rounded-lg border border-slate-200 px-4 py-2 text-sm text-slate-600 hover:bg-slate-50"
          >
            닫기
          </button>
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
