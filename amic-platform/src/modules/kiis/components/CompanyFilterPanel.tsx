import { useState, useRef, useEffect, useCallback } from "react";
import { Search, SlidersHorizontal, ChevronDown, X, RotateCcw } from "lucide-react";
import { cn } from "@/lib/cn";
import {
  CORP_CLS_OPTIONS,
  SEARCH_TYPE_OPTIONS,
} from "@/modules/kiis/constants/companyFilters";
import type { SearchType } from "@/modules/kiis/types/company";

interface CompanyFilterPanelProps {
  searchText: string;
  onSearchTextChange: (value: string) => void;
  searchType: SearchType;
  onSearchTypeChange: (value: SearchType) => void;
  corpClsList: string[];
  onSetFilter: (key: string, value: string | undefined) => void;
  onReset: () => void;
  activeFilterCount: number;
}

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
          : "bg-white border-gray-border text-text-secondary hover:border-amic-300 hover:text-text-body",
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

export function CompanyFilterPanel({
  searchText,
  onSearchTextChange,
  searchType,
  onSearchTypeChange,
  corpClsList,
  onSetFilter,
  onReset,
  activeFilterCount,
}: CompanyFilterPanelProps) {
  const [expanded, setExpanded] = useState(true);

  // 디바운스 타이머
  const searchTimer = useRef<ReturnType<typeof setTimeout>>(undefined);

  useEffect(
    () => () => {
      clearTimeout(searchTimer.current);
    },
    [],
  );

  const currentPlaceholder =
    SEARCH_TYPE_OPTIONS.find((o) => o.value === searchType)?.placeholder ??
    "검색어 입력...";

  const handleSearchChange = useCallback(
    (value: string) => {
      onSearchTextChange(value);
      clearTimeout(searchTimer.current);
      searchTimer.current = setTimeout(() => {
        onSetFilter("search", value || undefined);
      }, 300);
    },
    [onSearchTextChange, onSetFilter],
  );

  const handleSearchTypeChange = useCallback(
    (value: string) => {
      const st = value as SearchType;
      onSearchTypeChange(st);
      onSetFilter("search_type", st === "name" ? undefined : st);
      // 검색 유형 변경 시 검색어 초기화
      onSearchTextChange("");
      onSetFilter("search", undefined);
    },
    [onSearchTypeChange, onSetFilter, onSearchTextChange],
  );

  const toggleChip = (key: string, currentSelected: string[], value: string) => {
    const next = currentSelected.includes(value)
      ? currentSelected.filter((v) => v !== value)
      : [...currentSelected, value];
    onSetFilter(key, next.join(",") || undefined);
  };

  return (
    <div className="rounded-dr border border-gray-border bg-white shadow-dr-sm overflow-hidden">
      {/* ── 헤더 바: 검색 유형 + 검색 입력 + 필터 토글 ── */}
      <div className="px-5 py-4 flex flex-col gap-3">
        {/* 검색 유형 드롭다운 + 검색 입력 */}
        <div className="flex gap-2">
          <select
            value={searchType}
            onChange={(e) => handleSearchTypeChange(e.target.value)}
            className={cn(
              "shrink-0 px-3 py-2 text-sm rounded-lg border border-gray-border",
              "bg-bg-cool text-text-body",
              "focus:outline-none focus:ring-2 focus:ring-accent/30 focus:border-accent focus:bg-white",
              "transition-all duration-150 cursor-pointer",
            )}
          >
            {SEARCH_TYPE_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>

          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-text-muted" />
            <input
              type="text"
              placeholder={currentPlaceholder}
              value={searchText}
              onChange={(e) => handleSearchChange(e.target.value)}
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
            {/* 시장 구분 */}
            <div className="space-y-2">
              <SectionLabel>시장 구분</SectionLabel>
              <div className="flex flex-wrap gap-2">
                {CORP_CLS_OPTIONS.map((opt) => (
                  <Chip
                    key={opt.value}
                    label={opt.label}
                    active={corpClsList.includes(opt.value)}
                    onClick={() => toggleChip("corp_cls", corpClsList, opt.value)}
                  />
                ))}
              </div>
            </div>

            {/* 적용된 필터 태그 */}
            {corpClsList.length > 0 && (
              <ActiveFilterTags
                corpClsList={corpClsList}
                onRemove={(value) => {
                  const next = corpClsList.filter((v) => v !== value);
                  onSetFilter("corp_cls", next.join(",") || undefined);
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
  corpClsList,
  onRemove,
}: {
  corpClsList: string[];
  onRemove: (value: string) => void;
}) {
  const labelMap: Record<string, string> = {};
  for (const opt of CORP_CLS_OPTIONS) labelMap[opt.value] = opt.label;

  return (
    <div className="pt-3 border-t border-gray-border/40">
      <div className="flex flex-wrap gap-1.5">
        {corpClsList.map((v) => (
          <span
            key={v}
            className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full bg-accent/8 text-accent text-xs font-medium"
          >
            {labelMap[v] ?? v}
            <button
              type="button"
              onClick={() => onRemove(v)}
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
