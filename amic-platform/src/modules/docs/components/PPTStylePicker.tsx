import { useEffect, useRef } from "react";
import type { PPTDesignStyle } from "@/modules/docs/types/document";

/** CSS 미니 슬라이드 미리보기 — AMIC 디자인 토큰 컬러 사용 */
function MiniSlidePreview({
  primaryColor,
  accentColor,
  brandText,
  partnerText,
}: {
  primaryColor: string;
  accentColor: string;
  brandText: string;
  partnerText?: string;
}) {
  return (
    <div
      className="relative w-full rounded overflow-hidden border border-gray-200 shadow-sm"
      style={{ aspectRatio: "16/9", maxHeight: "90px" }}
    >
      {/* 슬라이드 배경 */}
      <div className="absolute inset-0 bg-white" />

      {/* 헤더 바 (primary 컬러) */}
      <div
        className="absolute top-0 left-0 right-0"
        style={{ height: "28%", backgroundColor: primaryColor }}
      >
        {/* 로고 텍스트 */}
        <div className="absolute top-1 left-2 flex flex-col">
          <span
            className="text-white font-bold leading-none"
            style={{ fontSize: "5px", letterSpacing: "0.08em" }}
          >
            {brandText}
          </span>
          {partnerText && (
            <span
              className="font-bold leading-none"
              style={{ fontSize: "4px", color: accentColor, letterSpacing: "0.06em" }}
            >
              x {partnerText}
            </span>
          )}
        </div>
        {/* 서브헤더 악센트 바 */}
        <div
          className="absolute bottom-0 right-0"
          style={{ width: "40%", height: "3px", backgroundColor: accentColor }}
        />
      </div>

      {/* 콘텐츠 영역 - 텍스트 라인 스켈레톤 */}
      <div className="absolute bottom-0 left-0 right-0 px-2 py-1.5" style={{ top: "30%" }}>
        <div className="h-1 w-2/3 rounded mb-1" style={{ backgroundColor: primaryColor, opacity: 0.6 }} />
        <div className="h-0.5 w-full rounded mb-1 bg-gray-200" />
        <div className="h-0.5 w-4/5 rounded mb-1 bg-gray-200" />
        <div className="h-0.5 w-3/5 rounded bg-gray-200" />
      </div>

      {/* KPI 카드 스켈레톤 (우측 하단) */}
      <div className="absolute bottom-1 right-1 flex gap-0.5">
        {[accentColor, primaryColor].map((c, i) => (
          <div
            key={i}
            className="rounded"
            style={{ width: "10px", height: "10px", backgroundColor: c, opacity: 0.7 }}
          />
        ))}
      </div>
    </div>
  );
}

/** 컬러 스와치 인디케이터 */
function ColorSwatch({ primary, accent }: { primary: string; accent: string }) {
  return (
    <div className="flex items-center gap-1.5">
      <div
        className="w-4 h-4 rounded-full border border-white shadow-sm"
        style={{ backgroundColor: primary }}
        title={primary}
      />
      <div
        className="w-4 h-4 rounded-full border border-white shadow-sm"
        style={{ backgroundColor: accent }}
        title={accent}
      />
      <span className="text-xs text-text-secondary font-mono">{primary}</span>
    </div>
  );
}

interface PPTStylePickerProps {
  selected: PPTDesignStyle | null;
  partnerName: string;
  onSelect: (style: PPTDesignStyle) => void;
  onPartnerNameChange: (name: string) => void;
}

export function PPTStylePicker({
  selected,
  partnerName,
  onSelect,
  onPartnerNameChange,
}: PPTStylePickerProps) {
  const partnerInputRef = useRef<HTMLInputElement>(null);

  // AMIC_COLLAB 선택 시 파트너명 입력창에 자동 포커스
  useEffect(() => {
    if (selected === "AMIC_COLLAB") {
      partnerInputRef.current?.focus();
    }
  }, [selected]);

  const AMIC_PRIMARY = "#0F3A32";
  const AMIC_ACCENT = "#26C260";

  const styles: {
    style: PPTDesignStyle;
    title: string;
    subtitle: string;
    description: string;
    primary: string;
    accent: string;
    brandText: string;
    partnerText?: string;
    features: string[];
  }[] = [
    {
      style: "AMIC",
      title: "AMIC 스타일",
      subtitle: "AMIC & PETRABRIDGE PARTNERS 단독",
      description: "AMIC 브랜드 디자인 시스템 — 현재 TM 문서에 적용된 공식 스타일",
      primary: AMIC_PRIMARY,
      accent: AMIC_ACCENT,
      brandText: "AMIC",
      features: ["Dark Green #0F3A32 헤더", "Green #26C260 강조", "Inter / Pretendard 폰트"],
    },
    {
      style: "AMIC_COLLAB",
      title: "AMIC x 파트너",
      subtitle: "협업 파트너 공동 브랜딩",
      description: "AMIC 디자인 시스템 유지 + 파트너명 공동 표기 (표지/footer)",
      primary: AMIC_PRIMARY,
      accent: AMIC_ACCENT,
      brandText: "AMIC",
      partnerText: partnerName || "파트너명",
      features: ["동일 AMIC 컬러/폰트", "표지에 'AMIC x [파트너]' 표기", "footer 공동 저작 표기"],
    },
  ];

  return (
    <div className="space-y-3">
      <p className="text-sm text-text-secondary">
        PPTX 파일에 적용할 브랜딩 스타일을 선택하세요. 컬러, 폰트, 레이아웃은 AMIC 공식 디자인 시스템을 따릅니다.
      </p>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        {styles.map((s) => {
          const isSelected = selected === s.style;
          const isCollab = s.style === "AMIC_COLLAB";
          return (
            <button
              key={s.style}
              type="button"
              onClick={() => onSelect(s.style)}
              className={`text-left p-5 rounded-xl border-2 transition-all ${
                isSelected
                  ? "border-amic bg-amic/5 ring-1 ring-amic/20"
                  : "border-gray-border bg-white hover:border-amic/40 hover:bg-bg-cool"
              }`}
            >
              {/* 미니 슬라이드 미리보기 */}
              <div className="mb-3">
                <MiniSlidePreview
                  primaryColor={s.primary}
                  accentColor={s.accent}
                  brandText={s.brandText}
                  partnerText={isCollab ? (partnerName || "파트너") : undefined}
                />
              </div>

              {/* 제목 + 서브타이틀 */}
              <div className="mb-2">
                <h3
                  className={`text-base font-heading font-semibold ${
                    isSelected ? "text-amic" : "text-text-dark"
                  }`}
                >
                  {s.title}
                </h3>
                <p className="text-xs text-text-secondary mt-0.5">{s.subtitle}</p>
              </div>

              {/* 설명 */}
              <p className="text-sm text-text-secondary mb-3">{s.description}</p>

              {/* 컬러 스와치 */}
              <div className="mb-3">
                <ColorSwatch primary={s.primary} accent={s.accent} />
              </div>

              {/* 특징 배지 */}
              <div className="flex flex-wrap gap-1.5 mb-3">
                {s.features.map((f) => (
                  <span
                    key={f}
                    className={`px-2 py-0.5 text-xs rounded ${
                      isSelected
                        ? "bg-amic/10 text-amic"
                        : "bg-bg-cool text-text-secondary"
                    }`}
                  >
                    {f}
                  </span>
                ))}
              </div>

              {/* AMIC_COLLAB: 파트너명 입력 (카드 선택 시 인라인 표시) */}
              {isCollab && isSelected && (
                <div
                  className="mt-1"
                  onClick={(e) => e.stopPropagation()} // 카드 클릭 이벤트 버블링 차단
                >
                  <label htmlFor="ppt-partner-name" className="block text-xs font-medium text-text-dark mb-1">
                    파트너명 <span className="text-caution">*</span>
                  </label>
                  <input
                    id="ppt-partner-name"
                    ref={partnerInputRef}
                    type="text"
                    value={partnerName}
                    onChange={(e) => onPartnerNameChange(e.target.value)}
                    placeholder="예: 삼일PwC, Goldman Sachs"
                    maxLength={100}
                    className="w-full px-3 py-1.5 text-sm border border-gray-border rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-amic/30 focus:border-amic"
                  />
                  {partnerName && (
                    <p className="text-xs text-text-secondary mt-1">
                      표지에 <strong className="text-text-dark">AMIC x {partnerName}</strong>으로 표기됩니다
                    </p>
                  )}
                </div>
              )}
            </button>
          );
        })}
      </div>
    </div>
  );
}
