import { useState, useRef, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { Search, Building2, Landmark, Home, Newspaper } from "lucide-react";
import { useUnifiedSearch } from "@/modules/kiis/hooks/useSearch";
import type { SearchResultType } from "@/modules/kiis/types/search";
import { cn } from "@/lib/cn";

const TYPE_ICONS: Record<SearchResultType, typeof Building2> = {
  company: Building2,
  fund: Landmark,
  reit: Home,
  news: Newspaper,
};

const TYPE_ROUTES: Record<SearchResultType, string> = {
  company: "/kiis/companies",
  fund: "/kiis/funds",
  reit: "/kiis/reits",
  news: "/kiis/news",
};

export default function SearchBar() {
  const navigate = useNavigate();
  const [query, setQuery] = useState("");
  const [debouncedQuery, setDebouncedQuery] = useState("");
  const [open, setOpen] = useState(false);
  const wrapperRef = useRef<HTMLDivElement>(null);

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

  const handleSelect = (type: SearchResultType, id: string) => {
    setOpen(false);
    setQuery("");
    navigate(`${TYPE_ROUTES[type]}/${id}`);
  };

  return (
    <div ref={wrapperRef} className="relative w-full max-w-md">
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-text-secondary" />
        <input
          type="text"
          placeholder="Search companies, funds, REITs, news..."
          className="w-full pl-10 pr-4 py-2 text-sm border border-gray-border rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-accent/40 focus:border-accent"
          value={query}
          onChange={(e) => {
            setQuery(e.target.value);
            setOpen(true);
          }}
          onFocus={() => setOpen(true)}
        />
      </div>
      {open && results && results.items.length > 0 && (
        <div className="absolute z-50 mt-1 w-full bg-white border border-gray-border rounded-lg shadow-card max-h-64 overflow-y-auto">
          {results.items.map((item) => {
            const Icon = TYPE_ICONS[item.type];
            return (
              <button
                key={`${item.type}-${item.id}`}
                className={cn(
                  "flex items-center gap-3 w-full px-3 py-2 text-left text-sm",
                  "hover:bg-bg-cool transition-colors",
                )}
                onClick={() => handleSelect(item.type, item.id)}
              >
                <Icon className="h-4 w-4 text-text-secondary shrink-0" />
                <div className="min-w-0">
                  <p className="font-medium text-text-dark truncate">
                    {item.name}
                  </p>
                  {item.description && (
                    <p className="text-xs text-text-secondary truncate">
                      {item.description}
                    </p>
                  )}
                </div>
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}
