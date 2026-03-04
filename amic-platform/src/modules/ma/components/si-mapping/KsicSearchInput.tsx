import {
  useCallback,
  useEffect,
  useRef,
  useState,
  type KeyboardEvent,
} from "react";

import { cn } from "@/lib/cn";
import { useKsicSearch } from "@/modules/ma/hooks/useSIMapping";
import type { KsicSuggestion } from "@/modules/ma/types/si_mapping";

interface KsicSearchInputProps {
  selectedCodes: KsicSuggestion[];
  onSelect: (codes: KsicSuggestion[]) => void;
}

export default function KsicSearchInput({
  selectedCodes,
  onSelect,
}: KsicSearchInputProps) {
  const [query, setQuery] = useState("");
  const [debouncedQuery, setDebouncedQuery] = useState("");
  const [isOpen, setIsOpen] = useState(false);
  const [highlightIdx, setHighlightIdx] = useState(-1);
  const wrapperRef = useRef<HTMLDivElement>(null);

  // 디바운스 (300ms)
  useEffect(() => {
    const timer = setTimeout(() => setDebouncedQuery(query), 300);
    return () => clearTimeout(timer);
  }, [query]);

  const { data: suggestions = [], isLoading: isSearching } =
    useKsicSearch(debouncedQuery);

  // 외부 클릭 시 드롭다운 닫기
  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (
        wrapperRef.current &&
        !wrapperRef.current.contains(e.target as Node)
      ) {
        setIsOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const handleSelect = useCallback(
    (item: KsicSuggestion) => {
      if (!selectedCodes.find((s) => s.code === item.code)) {
        onSelect([...selectedCodes, item]);
      }
      setQuery("");
      setIsOpen(false);
      setHighlightIdx(-1);
    },
    [selectedCodes, onSelect],
  );

  const handleRemove = useCallback(
    (code: string) => {
      onSelect(selectedCodes.filter((s) => s.code !== code));
    },
    [selectedCodes, onSelect],
  );

  // 이미 선택된 코드는 드롭다운에서 제외
  const filteredSuggestions = suggestions.filter(
    (s) => !selectedCodes.find((sc) => sc.code === s.code),
  );

  const handleKeyDown = useCallback(
    (e: KeyboardEvent<HTMLInputElement>) => {
      if (!isOpen || filteredSuggestions.length === 0) return;
      if (e.key === "ArrowDown") {
        e.preventDefault();
        setHighlightIdx((prev) =>
          prev < filteredSuggestions.length - 1 ? prev + 1 : 0,
        );
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        setHighlightIdx((prev) =>
          prev > 0 ? prev - 1 : filteredSuggestions.length - 1,
        );
      } else if (e.key === "Enter" && highlightIdx >= 0) {
        e.preventDefault();
        handleSelect(filteredSuggestions[highlightIdx]);
      } else if (e.key === "Escape") {
        setIsOpen(false);
        setHighlightIdx(-1);
      }
    },
    [isOpen, filteredSuggestions, highlightIdx, handleSelect],
  );

  return (
    <div ref={wrapperRef} className="relative">
      <label className="mb-1.5 block text-sm font-medium text-slate-700">
        타겟 KSIC 코드
      </label>

      {/* 선택된 코드 칩 */}
      {selectedCodes.length > 0 && (
        <div className="mb-2 flex flex-wrap gap-1.5">
          {selectedCodes.map((item) => (
            <span
              key={item.code}
              className="inline-flex items-center gap-1 rounded-full bg-emerald-50 px-2.5 py-1 text-xs font-medium text-emerald-700"
            >
              {item.code} — {item.name}
              <button
                type="button"
                onClick={() => handleRemove(item.code)}
                aria-label={`${item.code} ${item.name} 제거`}
                className="ml-0.5 text-emerald-500 hover:text-emerald-800"
              >
                &times;
              </button>
            </span>
          ))}
        </div>
      )}

      {/* 검색 입력 */}
      <input
        type="text"
        value={query}
        onChange={(e) => {
          setQuery(e.target.value);
          setIsOpen(true);
          setHighlightIdx(-1);
        }}
        onFocus={() => query.length >= 1 && setIsOpen(true)}
        onKeyDown={handleKeyDown}
        placeholder="KSIC 코드 또는 산업명 검색 (예: C10, 식료품)"
        className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm placeholder:text-slate-400 focus:border-emerald-500 focus:outline-none focus:ring-1 focus:ring-emerald-500"
      />

      {/* 드롭다운 */}
      {isOpen && filteredSuggestions.length > 0 && (
        <ul className="absolute z-20 mt-1 max-h-60 w-full overflow-auto rounded-lg border border-slate-200 bg-white py-1 shadow-lg">
          {filteredSuggestions.map((item, idx) => (
            <li key={item.code}>
              <button
                type="button"
                onClick={() => handleSelect(item)}
                className={cn(
                  "w-full px-3 py-2 text-left text-sm hover:bg-emerald-50",
                  "flex items-center gap-2",
                  idx === highlightIdx && "bg-emerald-50",
                )}
              >
                <span className="font-mono text-xs font-semibold text-emerald-600">
                  {item.code}
                </span>
                <span className="text-slate-600">{item.name}</span>
              </button>
            </li>
          ))}
        </ul>
      )}

      {/* 검색 결과 없음 */}
      {isOpen &&
        filteredSuggestions.length === 0 &&
        debouncedQuery.length >= 1 &&
        !isSearching && (
          <div className="absolute z-20 mt-1 w-full rounded-lg border border-slate-200 bg-white py-3 text-center text-sm text-slate-400 shadow-lg">
            검색 결과가 없습니다
          </div>
        )}
    </div>
  );
}
