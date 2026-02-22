import { useState, useMemo, useRef, useEffect, useCallback, useId } from "react";
import { useNavigate } from "react-router-dom";
import { Search, Building2, Landmark, Newspaper, TrendingUp } from "lucide-react";
import { useUnifiedSearch } from "@/modules/kiis/hooks/useSearch";
import type { SearchResultItem, SearchIndexType } from "@/modules/kiis/types/search";
import { cn } from "@/lib/cn";

const VALID_INDEX_TYPES = new Set<string>(["companies", "funds", "news", "deals"]);

function toIndexType(index: string): SearchIndexType {
  const cleaned = index.replace(/^kiis_/, "");
  return VALID_INDEX_TYPES.has(cleaned) ? (cleaned as SearchIndexType) : "companies";
}

const TYPE_ICONS: Record<SearchIndexType, typeof Building2> = {
  companies: Building2,
  funds: Landmark,
  news: Newspaper,
  deals: TrendingUp,
};

const TYPE_ROUTES: Record<SearchIndexType, string> = {
  companies: "/kiis/companies",
  funds: "/kiis/funds",
  news: "/kiis/news",
  deals: "/kiis/deals",
};

function getDisplayName(item: SearchResultItem): string {
  const s = item.source;
  return (
    (s.corp_name as string) ??
    (s.name as string) ??
    (s.title as string) ??
    (s.fund_name as string) ??
    String(item.id)
  );
}

function getDescription(item: SearchResultItem): string | null {
  const s = item.source;
  return (
    (s.induty_code as string) ??
    (s.description as string) ??
    (s.source as string) ??
    null
  );
}

export default function SearchBar() {
  const navigate = useNavigate();
  const [query, setQuery] = useState("");
  const [debouncedQuery, setDebouncedQuery] = useState("");
  const [open, setOpen] = useState(false);
  const [activeIndex, setActiveIndex] = useState(-1);
  const wrapperRef = useRef<HTMLDivElement>(null);
  const listRef = useRef<HTMLDivElement>(null);
  const instanceId = useId();
  const listboxId = `${instanceId}-search-results`;
  const optionId = (idx: number) => `${instanceId}-search-option-${idx}`;

  useEffect(() => {
    const timer = setTimeout(() => setDebouncedQuery(query), 300);
    return () => clearTimeout(timer);
  }, [query]);

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (
        wrapperRef.current &&
        !wrapperRef.current.contains(e.target as Node)
      ) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const { data: results } = useUnifiedSearch({ q: debouncedQuery });
  const items = useMemo(() => results?.items ?? [], [results?.items]);
  const hasResults = open && items.length > 0;

  const handleSelect = useCallback(
    (item: SearchResultItem) => {
      setOpen(false);
      setQuery("");
      setActiveIndex(-1);
      const indexType = toIndexType(item.index);
      const route = TYPE_ROUTES[indexType];
      navigate(`${route}/${item.id}`);
    },
    [navigate],
  );

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (!hasResults) return;

      switch (e.key) {
        case "ArrowDown":
          e.preventDefault();
          setActiveIndex((prev) => (prev < items.length - 1 ? prev + 1 : 0));
          break;
        case "ArrowUp":
          e.preventDefault();
          setActiveIndex((prev) => (prev > 0 ? prev - 1 : items.length - 1));
          break;
        case "Enter":
          e.preventDefault();
          if (activeIndex >= 0 && activeIndex < items.length) {
            handleSelect(items[activeIndex]);
          }
          break;
        case "Escape":
          setOpen(false);
          setActiveIndex(-1);
          break;
      }
    },
    [hasResults, items, activeIndex, handleSelect],
  );

  // Scroll active option into view
  useEffect(() => {
    if (activeIndex < 0 || !listRef.current) return;
    const activeEl = listRef.current.children[activeIndex] as HTMLElement | undefined;
    activeEl?.scrollIntoView({ block: "nearest" });
  }, [activeIndex]);

  // Reset active index when results change
  useEffect(() => {
    setActiveIndex(-1);
  }, [items.length]);

  return (
    <div ref={wrapperRef} className="relative w-full max-w-md">
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-text-secondary" aria-hidden="true" />
        <input
          type="text"
          role="combobox"
          aria-label="Search companies, funds, news, deals"
          aria-autocomplete="list"
          aria-expanded={hasResults}
          aria-controls={listboxId}
          aria-activedescendant={activeIndex >= 0 && hasResults ? optionId(activeIndex) : undefined}
          placeholder="Search companies, funds, news..."
          className="w-full pl-10 pr-4 py-2 text-sm border border-gray-border rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-accent/40 focus:border-accent"
          value={query}
          onChange={(e) => {
            setQuery(e.target.value);
            setOpen(true);
          }}
          onFocus={() => setOpen(true)}
          onKeyDown={handleKeyDown}
        />
      </div>
      {hasResults && (
        <div
          ref={listRef}
          id={listboxId}
          role="listbox"
          aria-label="Search results"
          className="absolute z-50 mt-1 w-full bg-white border border-gray-border rounded-lg shadow-card max-h-64 overflow-y-auto"
        >
          {items.map((item, idx) => {
            const indexType = toIndexType(item.index);
            const Icon = TYPE_ICONS[indexType];
            const name = getDisplayName(item);
            const description = getDescription(item);
            return (
              <div
                key={`${item.index}-${item.id}`}
                id={optionId(idx)}
                role="option"
                aria-selected={idx === activeIndex}
                className={cn(
                  "flex items-center gap-3 w-full px-3 py-2 text-left text-sm cursor-pointer",
                  "transition-colors",
                  idx === activeIndex ? "bg-bg-cool" : "hover:bg-bg-cool",
                )}
                onClick={() => handleSelect(item)}
                onMouseEnter={() => setActiveIndex(idx)}
              >
                <Icon className="h-4 w-4 text-text-secondary shrink-0" aria-hidden="true" />
                <div className="min-w-0">
                  <p className="font-medium text-text-dark truncate">
                    {name}
                  </p>
                  {description && (
                    <p className="text-xs text-text-secondary truncate">
                      {description}
                    </p>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
