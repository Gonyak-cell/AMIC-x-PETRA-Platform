import { useState, useRef, useEffect, useCallback } from "react";
import { ChevronDown, X } from "lucide-react";
import { cn } from "@/lib/cn";
import { INLINE_INPUT_CLS } from "./InlineSelect";

export interface InlineComboboxOption {
  value: string;
  label: string;
  description?: string;
}

export interface InlineComboboxProps {
  options: InlineComboboxOption[];
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  className?: string;
  disabled?: boolean;
  /** false로 설정하면 X(선택 해제) 버튼을 숨긴다. 기본값 true. */
  clearable?: boolean;
}

export function InlineCombobox({
  options,
  value,
  onChange,
  placeholder = "선택...",
  className,
  disabled,
  clearable = true,
}: InlineComboboxProps) {
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState("");
  const [highlightIdx, setHighlightIdx] = useState(-1);
  const inputRef = useRef<HTMLInputElement>(null);
  const wrapperRef = useRef<HTMLDivElement>(null);

  const selectedOption = options.find((o) => o.value === value);

  const filtered = options.filter(
    (o) =>
      o.label.toLowerCase().includes(search.toLowerCase()) ||
      o.value.toLowerCase().includes(search.toLowerCase()) ||
      (o.description ?? "").toLowerCase().includes(search.toLowerCase()),
  );

  // 외부 클릭 시 닫기
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (
        wrapperRef.current &&
        !wrapperRef.current.contains(e.target as Node)
      ) {
        setOpen(false);
        setSearch("");
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  // highlight 초기화
  useEffect(() => {
    setHighlightIdx(-1);
  }, [search]);

  const select = useCallback(
    (val: string) => {
      onChange(val);
      setOpen(false);
      setSearch("");
      inputRef.current?.blur();
    },
    [onChange],
  );

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (!open) return;
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setHighlightIdx((i) => (i < filtered.length - 1 ? i + 1 : 0));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setHighlightIdx((i) => (i > 0 ? i - 1 : filtered.length - 1));
    } else if (
      e.key === "Enter" &&
      highlightIdx >= 0 &&
      filtered[highlightIdx]
    ) {
      e.preventDefault();
      select(filtered[highlightIdx].value);
    } else if (e.key === "Escape") {
      setOpen(false);
      setSearch("");
    }
  };

  return (
    <div ref={wrapperRef} className="relative inline-block">
      <div className="relative inline-flex items-center">
        <input
          ref={inputRef}
          type="text"
          className={cn(INLINE_INPUT_CLS, "pr-12 w-48", className)}
          value={open ? search : (selectedOption?.label ?? "")}
          placeholder={placeholder}
          disabled={disabled}
          onFocus={() => {
            setOpen(true);
            setSearch("");
          }}
          onChange={(e) => setSearch(e.target.value)}
          onKeyDown={handleKeyDown}
          autoComplete="off"
          role="combobox"
          aria-expanded={open}
          aria-haspopup="listbox"
          aria-activedescendant={
            highlightIdx >= 0 && filtered[highlightIdx]
              ? `cb-opt-${filtered[highlightIdx].value}`
              : undefined
          }
        />
        {value && !disabled && clearable && (
          <button
            type="button"
            className="absolute right-5 top-1/2 -translate-y-1/2 text-text-secondary hover:text-negative"
            onClick={() => {
              onChange("");
              setSearch("");
            }}
            tabIndex={-1}
            aria-label="선택 해제"
          >
            <X className="h-3 w-3" />
          </button>
        )}
        <ChevronDown className="absolute right-1 top-1/2 -translate-y-1/2 h-3 w-3 text-text-secondary pointer-events-none" />
      </div>

      {open && (
        <div
          className="absolute z-50 mt-1 w-56 bg-white border border-gray-border rounded-dr shadow-lg max-h-48 overflow-y-auto"
          role="listbox"
        >
          {filtered.length === 0 ? (
            <div className="px-3 py-2 text-xs text-text-muted">결과 없음</div>
          ) : (
            filtered.map((opt, idx) => (
              <button
                key={opt.value}
                id={`cb-opt-${opt.value}`}
                type="button"
                role="option"
                aria-selected={opt.value === value}
                className={cn(
                  "w-full text-left px-3 py-1.5 text-xs hover:bg-accent/10 transition-colors",
                  opt.value === value && "bg-accent/5 font-medium",
                  idx === highlightIdx && "bg-accent/10",
                )}
                onMouseDown={(e) => {
                  e.preventDefault();
                  select(opt.value);
                }}
              >
                <div>{opt.label}</div>
                {opt.description && (
                  <div className="text-text-muted text-[10px]">
                    {opt.description}
                  </div>
                )}
              </button>
            ))
          )}
        </div>
      )}
    </div>
  );
}
