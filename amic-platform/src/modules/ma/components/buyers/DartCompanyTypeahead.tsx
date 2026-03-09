import { useState, useRef, useEffect, useCallback } from "react";
import { Search, X, Building2 } from "lucide-react";
import { cn } from "@/lib/cn";
import { useDartCompanySearch } from "@/modules/ma/hooks/useDartIntegration";
import type { DartCompanySuggestion } from "@/modules/ma/types/marketing_log";

interface DartCompanyTypeaheadProps {
  txnId: string;
  value: string;
  corpCode: string | null;
  onChange: (companyName: string, corpCode: string | null) => void;
  placeholder?: string;
  disabled?: boolean;
  className?: string;
}

export default function DartCompanyTypeahead({
  txnId,
  value,
  corpCode,
  onChange,
  placeholder = "회사명 입력 (DART 자동검색)",
  disabled,
  className,
}: DartCompanyTypeaheadProps) {
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");
  const [highlightIdx, setHighlightIdx] = useState(-1);
  const inputRef = useRef<HTMLInputElement>(null);
  const wrapperRef = useRef<HTMLDivElement>(null);

  // Debounce 300ms
  useEffect(() => {
    const timer = setTimeout(() => setDebouncedSearch(search), 300);
    return () => clearTimeout(timer);
  }, [search]);

  const { data: suggestions = [], isFetching } = useDartCompanySearch(
    txnId,
    debouncedSearch,
  );

  // 외부 클릭 시 닫기
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (
        wrapperRef.current &&
        !wrapperRef.current.contains(e.target as Node)
      ) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  useEffect(() => {
    setHighlightIdx(-1);
  }, [debouncedSearch]);

  const selectSuggestion = useCallback(
    (suggestion: DartCompanySuggestion) => {
      onChange(suggestion.corp_name, suggestion.corp_code);
      setOpen(false);
      setSearch("");
    },
    [onChange],
  );

  const clearCorpCode = useCallback(() => {
    onChange(value, null);
  }, [onChange, value]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (!open || suggestions.length === 0) return;
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setHighlightIdx((i) => (i < suggestions.length - 1 ? i + 1 : 0));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setHighlightIdx((i) => (i > 0 ? i - 1 : suggestions.length - 1));
    } else if (
      e.key === "Enter" &&
      highlightIdx >= 0 &&
      suggestions[highlightIdx]
    ) {
      e.preventDefault();
      selectSuggestion(suggestions[highlightIdx]);
    } else if (e.key === "Escape") {
      setOpen(false);
    }
  };

  return (
    <div ref={wrapperRef} className={cn("relative", className)}>
      <div className="relative">
        <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-text-muted" />
        <input
          ref={inputRef}
          type="text"
          className="w-full rounded-dr border border-border bg-white pl-8 pr-8 py-1.5 text-sm text-text-primary placeholder:text-text-muted focus:outline-none focus:ring-1 focus:ring-accent"
          value={open ? search : value}
          placeholder={placeholder}
          disabled={disabled}
          onFocus={() => {
            setOpen(true);
            setSearch(value);
          }}
          onChange={(e) => {
            setSearch(e.target.value);
            if (!open) setOpen(true);
          }}
          onKeyDown={handleKeyDown}
          autoComplete="off"
          role="combobox"
          aria-expanded={open}
          aria-haspopup="listbox"
          aria-controls="dart-company-listbox"
          aria-activedescendant={open && highlightIdx >= 0 ? `dart-option-${highlightIdx}` : undefined}
        />
        {corpCode && !disabled && (
          <button
            type="button"
            className="absolute right-2 top-1/2 -translate-y-1/2 text-text-secondary hover:text-negative"
            onClick={clearCorpCode}
            tabIndex={-1}
            aria-label="DART 매핑 해제"
          >
            <X className="h-3 w-3" />
          </button>
        )}
      </div>

      {/* DART corp_code 표시 */}
      {corpCode && (
        <div className="mt-1 flex items-center gap-1 text-[10px] text-text-muted">
          <Building2 className="h-3 w-3" />
          <span>DART: {corpCode}</span>
        </div>
      )}

      {/* 드롭다운 */}
      {open && debouncedSearch.length >= 1 && (
        <div
          className="absolute z-50 mt-1 w-full bg-white border border-gray-border rounded-dr shadow-lg max-h-52 overflow-y-auto"
          role="listbox"
          id="dart-company-listbox"
        >
          {isFetching ? (
            <div className="px-3 py-2 text-xs text-text-muted">검색 중...</div>
          ) : suggestions.length === 0 ? (
            <div className="px-3 py-2 text-xs text-text-muted">
              검색 결과 없음
            </div>
          ) : (
            suggestions.map((s, idx) => (
              <button
                key={s.corp_code}
                type="button"
                role="option"
                id={`dart-option-${idx}`}
                aria-selected={s.corp_code === corpCode}
                className={cn(
                  "w-full text-left px-3 py-2 text-xs hover:bg-accent/10 transition-colors",
                  s.corp_code === corpCode && "bg-accent/5 font-medium",
                  idx === highlightIdx && "bg-accent/10",
                )}
                onMouseDown={(e) => {
                  e.preventDefault();
                  selectSuggestion(s);
                }}
              >
                <div className="font-medium">{s.corp_name}</div>
                <div className="text-text-muted text-[10px]">
                  {s.corp_code}
                  {s.stock_code ? ` | ${s.stock_code}` : ""}
                </div>
              </button>
            ))
          )}
        </div>
      )}
    </div>
  );
}
