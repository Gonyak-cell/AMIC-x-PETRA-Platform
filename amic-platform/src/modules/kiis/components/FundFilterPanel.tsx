import { useState, useRef, useEffect, useCallback } from "react";
import { Search, SlidersHorizontal, ChevronDown, X, RotateCcw } from "lucide-react";
import { cn } from "@/lib/cn";
import {
  FUND_TYPE_OPTIONS,
  LEGAL_TYPE_OPTIONS,
  ASSET_CLASS_OPTIONS,
  FUND_STATUS_OPTIONS,
  AMOUNT_PRESET_OPTIONS,
  DATA_SOURCE_OPTIONS,
  getVintageYearOptions,
} from "@/modules/kiis/constants/fundFilters";

interface FundFilterPanelProps {
  companyName: string;
  fundName: string;
  onCompanyNameChange: (value: string) => void;
  onFundNameChange: (value: string) => void;
  fundTypes: string[];
  legalTypes: string[];
  assetClasses: string[];
  fundStatuses: string[];
  dataSource: string;
  vintageFrom: string;
  vintageTo: string;
  amountPreset: string;
  onSetFilter: (key: string, value: string | undefined) => void;
  onReset: () => void;
  activeFilterCount: number;
}

const VINTAGE_OPTIONS = getVintageYearOptions();

// ── Chip 토글 버튼 ──
function Chip({
  label,
  active,
  onClick,
}: {
  label: string;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "px-3 py-1.5 rounded-full text-[13px] font-medium",
        "border transition-all duration-150 select-none",
        "focus:outline-none focus-visible:ring-2 focus-visible:ring-accent/40",
        active
          ? "bg-accent/10 border-accent text-accent hover:bg-accent/15"
          : "bg-white border-gray-border text-text-secondary hover:border-amic-300 hover:text-text-body"
      )}
    >
      {active && <span className="mr-1">&#10003;</span>}
      {label}
    </button>
  );
}

// ── 섹션 헤더 ──
function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <span className="text-xs font-semibold uppercase tracking-wider text-text-muted">
      {children}
    </span>
  );
}

export function FundFilterPanel({
  companyName,
  fundName,
  onCompanyNameChange,
  onFundNameChange,
  fundTypes,
  legalTypes,
  assetClasses,
  fundStatuses,
  dataSource,
  vintageFrom,
  vintageTo,
  amountPreset,
  onSetFilter,
  onReset,
  activeFilterCount,
}: FundFilterPanelProps) {
  const [expanded, setExpanded] = useState(true);

  // 디바운스 타이머
  const companyTimer = useRef<ReturnType<typeof setTimeout>>(undefined);
  const fundTimer = useRef<ReturnType<typeof setTimeout>>(undefined);

  useEffect(
    () => () => {
      clearTimeout(companyTimer.current);
      clearTimeout(fundTimer.current);
    },
    [],
  );

  const handleCompanyChange = useCallback(
    (value: string) => {
      onCompanyNameChange(value);
      clearTimeout(companyTimer.current);
      companyTimer.current = setTimeout(() => {
        onSetFilter("company_name", value || undefined);
      }, 300);
    },
    [onCompanyNameChange, onSetFilter],
  );

  const handleFundChange = useCallback(
    (value: string) => {
      onFundNameChange(value);
      clearTimeout(fundTimer.current);
      fundTimer.current = setTimeout(() => {
        onSetFilter("fund_name", value || undefined);
      }, 300);
    },
    [onFundNameChange, onSetFilter],
  );

  const toggleChip = (key: string, currentSelected: string[], value: string) => {
    const next = currentSelected.includes(value)
      ? currentSelected.filter((v) => v !== value)
      : [...currentSelected, value];
    onSetFilter(key, next.join(",") || undefined);
  };

  return (
    <div className="rounded-dr border border-gray-border bg-white shadow-dr-sm overflow-hidden">
      {/* ── 헤더 바: 검색 + 필터 토글 ── */}
      <div className="px-5 py-4 flex flex-col gap-3">
        {/* 검색 입력 */}
        <div className="flex gap-3 flex-wrap">
          <div className="relative flex-1 min-w-[200px]">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-text-muted" />
            <input
              type="text"
              placeholder="운용사 검색..."
              value={companyName}
              onChange={(e) => handleCompanyChange(e.target.value)}
              className={cn(
                "w-full pl-9 pr-3 py-2 text-sm rounded-lg border border-gray-border",
                "bg-bg-cool text-text-body placeholder:text-text-muted",
                "focus:outline-none focus:ring-2 focus:ring-accent/30 focus:border-accent focus:bg-white",
                "transition-all duration-150",
              )}
            />
          </div>
          <div className="relative flex-1 min-w-[200px]">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-text-muted" />
            <input
              type="text"
              placeholder="펀드명 검색..."
              value={fundName}
              onChange={(e) => handleFundChange(e.target.value)}
              className={cn(
                "w-full pl-9 pr-3 py-2 text-sm rounded-lg border border-gray-border",
                "bg-bg-cool text-text-body placeholder:text-text-muted",
                "focus:outline-none focus:ring-2 focus:ring-accent/30 focus:border-accent focus:bg-white",
                "transition-all duration-150",
              )}
            />
          </div>
        </div>

        {/* 필터 토글 바 */}
        <div className="flex items-center justify-between">
          <button
            type="button"
            onClick={() => setExpanded(!expanded)}
            className={cn(
              "flex items-center gap-2 text-sm font-medium transition-colors",
              expanded ? "text-accent" : "text-text-secondary hover:text-text-body",
            )}
          >
            <SlidersHorizontal className="h-4 w-4" />
            상세 필터
            {activeFilterCount > 0 && (
              <span className="inline-flex items-center justify-center h-5 min-w-[20px] px-1.5 rounded-full bg-accent text-white text-[11px] font-bold">
                {activeFilterCount}
              </span>
            )}
            <ChevronDown
              className={cn(
                "h-3.5 w-3.5 transition-transform duration-200",
                expanded && "rotate-180",
              )}
            />
          </button>

          {activeFilterCount > 0 && (
            <button
              type="button"
              onClick={onReset}
              className="flex items-center gap-1.5 text-xs text-text-secondary hover:text-negative transition-colors"
            >
              <RotateCcw className="h-3 w-3" />
              초기화
            </button>
          )}
        </div>
      </div>

      {/* ── 확장 필터 영역 ── */}
      <div
        className={cn(
          "grid transition-all duration-200 ease-in-out",
          expanded ? "grid-rows-[1fr] opacity-100" : "grid-rows-[0fr] opacity-0",
        )}
      >
        <div className="overflow-hidden">
          <div className="border-t border-gray-border/60 px-5 py-4 space-y-4 bg-bg-cool/40">
            {/* 행 0: 데이터 소스 */}
            <div className="space-y-2">
              <SectionLabel>데이터 소스</SectionLabel>
              <div className="flex flex-wrap gap-2">
                {DATA_SOURCE_OPTIONS.map((opt) => (
                  <Chip
                    key={opt.value}
                    label={opt.label}
                    active={dataSource === opt.value}
                    onClick={() => onSetFilter("data_source", opt.value || undefined)}
                  />
                ))}
              </div>
            </div>

            {/* 행 1: Investment Type + Legal Type */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-2">
                <SectionLabel>투자 방식</SectionLabel>
                <div className="flex flex-wrap gap-2">
                  {FUND_TYPE_OPTIONS.map((opt) => (
                    <Chip
                      key={opt.value}
                      label={opt.label}
                      active={fundTypes.includes(opt.value)}
                      onClick={() => toggleChip("fund_type", fundTypes, opt.value)}
                    />
                  ))}
                </div>
              </div>
              <div className="space-y-2">
                <SectionLabel>법률 유형</SectionLabel>
                <div className="flex flex-wrap gap-2">
                  {LEGAL_TYPE_OPTIONS.map((opt) => (
                    <Chip
                      key={opt.value}
                      label={opt.label}
                      active={legalTypes.includes(opt.value)}
                      onClick={() => toggleChip("legal_type", legalTypes, opt.value)}
                    />
                  ))}
                </div>
              </div>
            </div>

            {/* 행 2: Asset Class (풀 너비) */}
            <div className="space-y-2">
              <SectionLabel>자산 유형</SectionLabel>
              <div className="flex flex-wrap gap-2">
                {ASSET_CLASS_OPTIONS.map((opt) => (
                  <Chip
                    key={opt.value}
                    label={opt.label}
                    active={assetClasses.includes(opt.value)}
                    onClick={() =>
                      toggleChip("asset_class", assetClasses, opt.value)
                    }
                  />
                ))}
              </div>
            </div>

            {/* 행 3: Status + Vintage + Amount */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 items-start">
              <div className="space-y-2">
                <SectionLabel>펀드 상태</SectionLabel>
                <div className="flex flex-wrap gap-2">
                  {FUND_STATUS_OPTIONS.map((opt) => (
                    <Chip
                      key={opt.value}
                      label={opt.label}
                      active={fundStatuses.includes(opt.value)}
                      onClick={() =>
                        toggleChip("fund_status", fundStatuses, opt.value)
                      }
                    />
                  ))}
                </div>
              </div>

              <div className="space-y-2">
                <SectionLabel>빈티지</SectionLabel>
                <div className="flex items-center gap-2">
                  <select
                    value={vintageFrom}
                    onChange={(e) =>
                      onSetFilter("vintage_from", e.target.value || undefined)
                    }
                    className={cn(
                      "flex-1 px-2.5 py-1.5 text-sm rounded-lg border border-gray-border",
                      "bg-white text-text-body appearance-none",
                      "focus:outline-none focus:ring-2 focus:ring-accent/30 focus:border-accent",
                      "transition-all duration-150",
                    )}
                  >
                    {VINTAGE_OPTIONS.map((opt) => (
                      <option key={opt.value} value={opt.value}>
                        {opt.label}
                      </option>
                    ))}
                  </select>
                  <span className="text-text-muted text-xs">~</span>
                  <select
                    value={vintageTo}
                    onChange={(e) =>
                      onSetFilter("vintage_to", e.target.value || undefined)
                    }
                    className={cn(
                      "flex-1 px-2.5 py-1.5 text-sm rounded-lg border border-gray-border",
                      "bg-white text-text-body appearance-none",
                      "focus:outline-none focus:ring-2 focus:ring-accent/30 focus:border-accent",
                      "transition-all duration-150",
                    )}
                  >
                    {VINTAGE_OPTIONS.map((opt) => (
                      <option key={opt.value} value={opt.value}>
                        {opt.label}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="space-y-2">
                <SectionLabel>설정액</SectionLabel>
                <select
                  value={amountPreset}
                  onChange={(e) =>
                    onSetFilter("amount_preset", e.target.value || undefined)
                  }
                  className={cn(
                    "w-full px-2.5 py-1.5 text-sm rounded-lg border border-gray-border",
                    "bg-white text-text-body appearance-none",
                    "focus:outline-none focus:ring-2 focus:ring-accent/30 focus:border-accent",
                    "transition-all duration-150",
                  )}
                >
                  {AMOUNT_PRESET_OPTIONS.map((opt) => (
                    <option key={opt.value} value={opt.value}>
                      {opt.label}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            {/* 적용된 필터 태그 */}
            {activeFilterCount > 0 && (
              <ActiveFilterTags
                fundTypes={fundTypes}
                legalTypes={legalTypes}
                assetClasses={assetClasses}
                fundStatuses={fundStatuses}
                vintageFrom={vintageFrom}
                vintageTo={vintageTo}
                amountPreset={amountPreset}
                onRemove={(key, value) => {
                  if (key === "vintage_from" || key === "vintage_to" || key === "amount_preset") {
                    onSetFilter(key, undefined);
                  } else {
                    // chip 배열에서 제거
                    const current = key === "fund_type" ? fundTypes
                      : key === "legal_type" ? legalTypes
                      : key === "asset_class" ? assetClasses
                      : fundStatuses;
                    const next = current.filter((v) => v !== value);
                    onSetFilter(key, next.join(",") || undefined);
                  }
                }}
              />
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

// ── 적용된 필터 태그 표시 ──
function ActiveFilterTags({
  fundTypes,
  legalTypes,
  assetClasses,
  fundStatuses,
  vintageFrom,
  vintageTo,
  amountPreset,
  onRemove,
}: {
  fundTypes: string[];
  legalTypes: string[];
  assetClasses: string[];
  fundStatuses: string[];
  vintageFrom: string;
  vintageTo: string;
  amountPreset: string;
  onRemove: (key: string, value: string) => void;
}) {
  const labelMap: Record<string, string> = {};
  for (const opt of FUND_TYPE_OPTIONS) labelMap[`fund_type:${opt.value}`] = opt.label;
  for (const opt of LEGAL_TYPE_OPTIONS) labelMap[`legal_type:${opt.value}`] = opt.label;
  for (const opt of ASSET_CLASS_OPTIONS) labelMap[`asset_class:${opt.value}`] = opt.label;
  for (const opt of FUND_STATUS_OPTIONS) labelMap[`fund_status:${opt.value}`] = opt.label;

  const tags: { key: string; value: string; label: string }[] = [];
  for (const v of fundTypes) tags.push({ key: "fund_type", value: v, label: labelMap[`fund_type:${v}`] ?? v });
  for (const v of legalTypes) tags.push({ key: "legal_type", value: v, label: labelMap[`legal_type:${v}`] ?? v });
  for (const v of assetClasses) tags.push({ key: "asset_class", value: v, label: labelMap[`asset_class:${v}`] ?? v });
  for (const v of fundStatuses) tags.push({ key: "fund_status", value: v, label: labelMap[`fund_status:${v}`] ?? v });
  if (vintageFrom) tags.push({ key: "vintage_from", value: vintageFrom, label: `${vintageFrom}~` });
  if (vintageTo) tags.push({ key: "vintage_to", value: vintageTo, label: `~${vintageTo}` });
  if (amountPreset) {
    const preset = AMOUNT_PRESET_OPTIONS.find((o) => o.value === amountPreset);
    tags.push({ key: "amount_preset", value: amountPreset, label: preset?.label ?? amountPreset });
  }

  if (tags.length === 0) return null;

  return (
    <div className="pt-3 border-t border-gray-border/40">
      <div className="flex flex-wrap gap-1.5">
        {tags.map((tag) => (
          <span
            key={`${tag.key}-${tag.value}`}
            className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full bg-accent/8 text-accent text-xs font-medium"
          >
            {tag.label}
            <button
              type="button"
              onClick={() => onRemove(tag.key, tag.value)}
              className="hover:bg-accent/20 rounded-full p-0.5 transition-colors"
            >
              <X className="h-3 w-3" />
            </button>
          </span>
        ))}
      </div>
    </div>
  );
}
