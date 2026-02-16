import { useState, useRef, useEffect, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import {
  Search,
  Briefcase,
  Building2,
  Landmark,
  Home,
  FileText,
  Clock,
  X,
} from "lucide-react";
import { cn } from "@/lib/cn";
import { useGlobalSearch } from "@/hooks/useGlobalSearch";
import { Badge } from "@/components/ui";
import type { GlobalSearchResult, SearchModule } from "@/types/search";

const MODULE_LABELS: Record<SearchModule, string> = {
  fdd: "FDD",
  kiis: "KIIS",
  im: "IM",
};

const MODULE_BADGE_VARIANTS: Record<SearchModule, "info" | "success" | "warning"> = {
  fdd: "info",
  kiis: "success",
  im: "warning",
};

const TYPE_ICONS: Record<string, typeof Briefcase> = {
  deal: Briefcase,
  company: Building2,
  fund: Landmark,
  reit: Home,
  project: FileText,
  news: FileText,
};

interface CommandPaletteProps {
  open: boolean;
  onClose: () => void;
}

const FOCUSABLE_SELECTOR =
  'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])';

export default function CommandPalette({ open, onClose }: CommandPaletteProps) {
  const navigate = useNavigate();
  const inputRef = useRef<HTMLInputElement>(null);
  const listRef = useRef<HTMLDivElement>(null);
  const paletteRef = useRef<HTMLDivElement>(null);
  const [query, setQuery] = useState("");
  const [activeIndex, setActiveIndex] = useState(-1);

  const {
    results,
    isLoading,
    failedModules,
    recentSearches,
    addRecentSearch,
    clearRecentSearches,
  } = useGlobalSearch(query);

  // Group results by module
  const grouped = results.reduce<Record<SearchModule, GlobalSearchResult[]>>(
    (acc, r) => {
      if (!acc[r.module]) acc[r.module] = [];
      acc[r.module].push(r);
      return acc;
    },
    {} as Record<SearchModule, GlobalSearchResult[]>,
  );

  const flatResults = results;

  // Focus input when opened + body scroll lock
  useEffect(() => {
    if (open) {
      setQuery("");
      setActiveIndex(-1);
      document.body.style.overflow = "hidden";
      requestAnimationFrame(() => inputRef.current?.focus());
    }
    return () => {
      document.body.style.overflow = "";
    };
  }, [open]);

  // Focus trap
  useEffect(() => {
    if (!open) return;
    const handleFocusTrap = (e: KeyboardEvent) => {
      if (e.key !== "Tab" || !paletteRef.current) return;
      const focusable = paletteRef.current.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTOR);
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
    document.addEventListener("keydown", handleFocusTrap);
    return () => document.removeEventListener("keydown", handleFocusTrap);
  }, [open]);

  // Navigate to result
  const handleSelect = useCallback(
    (result: GlobalSearchResult) => {
      addRecentSearch(query);
      onClose();
      navigate(result.path);
    },
    [query, addRecentSearch, onClose, navigate],
  );

  const handleRecentClick = useCallback(
    (term: string) => {
      setQuery(term);
    },
    [],
  );

  // Keyboard navigation
  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === "Escape") {
        onClose();
        return;
      }

      if (e.key === "ArrowDown") {
        e.preventDefault();
        setActiveIndex((prev) =>
          prev < flatResults.length - 1 ? prev + 1 : 0,
        );
        return;
      }

      if (e.key === "ArrowUp") {
        e.preventDefault();
        setActiveIndex((prev) =>
          prev > 0 ? prev - 1 : flatResults.length - 1,
        );
        return;
      }

      if (e.key === "Enter" && activeIndex >= 0 && flatResults[activeIndex]) {
        e.preventDefault();
        handleSelect(flatResults[activeIndex]);
      }
    },
    [onClose, flatResults, activeIndex, handleSelect],
  );

  // Scroll active item into view
  useEffect(() => {
    if (activeIndex >= 0 && listRef.current) {
      const items = listRef.current.querySelectorAll("[data-search-item]");
      items[activeIndex]?.scrollIntoView({ block: "nearest" });
    }
  }, [activeIndex]);

  if (!open) return null;

  const hasQuery = query.length >= 2;
  const showRecent = !hasQuery && recentSearches.length > 0;
  const showResults = hasQuery && !isLoading && results.length > 0;
  const showEmpty = hasQuery && !isLoading && results.length === 0;

  return (
    <div
      className="fixed inset-0 z-[60] flex items-start justify-center pt-[15vh]"
      onClick={onClose}
      role="dialog"
      aria-label="Global search"
      aria-modal="true"
    >
      {/* Backdrop */}
      <div className="fixed inset-0 bg-black/50" aria-hidden="true" />

      {/* Palette */}
      <div
        ref={paletteRef}
        className="relative w-full max-w-lg bg-white rounded-xl shadow-2xl border border-gray-border overflow-hidden"
        onClick={(e) => e.stopPropagation()}
        onKeyDown={handleKeyDown}
      >
        {/* Search Input */}
        <div className="flex items-center gap-3 px-4 py-3 border-b border-gray-border">
          <Search className="h-5 w-5 text-text-secondary flex-shrink-0" />
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={(e) => {
              setQuery(e.target.value);
              setActiveIndex(-1);
            }}
            placeholder="Search deals, companies, projects..."
            className="flex-1 text-sm text-text-dark placeholder:text-text-secondary outline-none bg-transparent"
            aria-label="Search input"
            role="combobox"
            aria-expanded={showResults}
            aria-activedescendant={
              activeIndex >= 0 ? `search-result-${activeIndex}` : undefined
            }
          />
          {query && (
            <button
              onClick={() => setQuery("")}
              className="p-1 text-text-secondary hover:text-text-dark"
              aria-label="Clear search"
            >
              <X className="h-4 w-4" />
            </button>
          )}
        </div>

        {/* Content Area */}
        <div ref={listRef} className="max-h-80 overflow-y-auto" role="listbox">
          {/* Recent Searches */}
          {showRecent && (
            <div className="p-2">
              <div className="flex items-center justify-between px-2 py-1.5">
                <span className="text-xs font-semibold text-text-secondary uppercase tracking-wider">
                  Recent Searches
                </span>
                <button
                  onClick={clearRecentSearches}
                  className="text-xs text-text-secondary hover:text-text-dark"
                >
                  Clear
                </button>
              </div>
              {recentSearches.map((term) => (
                <button
                  key={term}
                  onClick={() => handleRecentClick(term)}
                  className="flex items-center gap-3 w-full px-3 py-2 text-sm text-text-dark hover:bg-bg-cool rounded-lg transition-colors"
                >
                  <Clock className="h-4 w-4 text-text-secondary" />
                  {term}
                </button>
              ))}
            </div>
          )}

          {/* Loading */}
          {hasQuery && isLoading && (
            <div className="p-4 text-center text-sm text-text-secondary">
              Searching...
            </div>
          )}

          {/* Grouped Results */}
          {showResults && (
            <div className="p-2">
              {(() => {
                let cumulativeIdx = 0;
                return (Object.keys(grouped) as SearchModule[]).map((module) => (
                  <div key={module} className="mb-2">
                    <div className="px-2 py-1.5">
                      <Badge variant={MODULE_BADGE_VARIANTS[module]}>
                        {MODULE_LABELS[module]}
                      </Badge>
                    </div>
                    {grouped[module].map((result) => {
                      const globalIdx = cumulativeIdx++;
                      const Icon = TYPE_ICONS[result.type] ?? FileText;
                    return (
                      <button
                        key={`${result.module}-${result.id}`}
                        id={`search-result-${globalIdx}`}
                        data-search-item
                        role="option"
                        aria-selected={globalIdx === activeIndex}
                        onClick={() => handleSelect(result)}
                        className={cn(
                          "flex items-center gap-3 w-full px-3 py-2 text-left text-sm rounded-lg transition-colors",
                          globalIdx === activeIndex
                            ? "bg-amic/10 text-amic"
                            : "text-text-dark hover:bg-bg-cool",
                        )}
                      >
                        <Icon className="h-4 w-4 text-text-secondary flex-shrink-0" />
                        <div className="min-w-0 flex-1">
                          <p className="font-medium truncate">{result.title}</p>
                          {result.subtitle && (
                            <p className="text-xs text-text-secondary truncate">
                              {result.subtitle}
                            </p>
                          )}
                        </div>
                        <span className="text-xs text-text-secondary capitalize">
                          {result.type}
                        </span>
                      </button>
                    );
                  })}
                </div>
                ));
              })()}
            </div>
          )}

          {/* Failed modules warning */}
          {failedModules.length > 0 && hasQuery && (
            <div className="mx-2 mt-1 rounded-lg bg-amber-50 border border-amber-200 px-3 py-2 text-xs text-amber-700">
              Some modules could not be searched:{" "}
              {failedModules.map((m) => MODULE_LABELS[m]).join(", ")}
            </div>
          )}

          {/* Empty State */}
          {showEmpty && (
            <div className="p-8 text-center text-sm text-text-secondary">
              No results found for &ldquo;{query}&rdquo;
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center gap-4 px-4 py-2 border-t border-gray-border bg-bg-cool text-xs text-text-secondary">
          <span>
            <kbd className="px-1.5 py-0.5 bg-white border border-gray-border rounded text-[10px]">
              ↑↓
            </kbd>{" "}
            Navigate
          </span>
          <span>
            <kbd className="px-1.5 py-0.5 bg-white border border-gray-border rounded text-[10px]">
              ↵
            </kbd>{" "}
            Open
          </span>
          <span>
            <kbd className="px-1.5 py-0.5 bg-white border border-gray-border rounded text-[10px]">
              Esc
            </kbd>{" "}
            Close
          </span>
        </div>
      </div>
    </div>
  );
}
