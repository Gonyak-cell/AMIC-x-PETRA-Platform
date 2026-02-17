import { useState, useMemo, useCallback } from "react";
import { useNavigate, useSearchParams, Link } from "react-router-dom";
import { Wallet, AlertCircle, Search } from "lucide-react";
import { useGPs } from "@/modules/kiis/hooks/useGPs";
import {
  Card,
  Badge,
  EmptyState,
  Pagination,
  PageHero,
  Spinner,
} from "@/components/ui";
import type { GPListParams, GPSortField } from "@/modules/kiis/types/gp";
import { formatAmount } from "@/lib/format";
import {
  ASSET_CLASS_OPTIONS,
  ASSET_CLASS_BADGE_VARIANT,
  ASSET_CLASS_LABELS,
} from "@/modules/kiis/constants/fundFilters";

const PAGE_SIZE = 20;

function useGPFilters() {
  const [searchParams, setSearchParams] = useSearchParams();

  const params: GPListParams = useMemo(() => {
    const p: GPListParams = { size: PAGE_SIZE };
    const companyName = searchParams.get("company_name");
    const assetClass = searchParams.get("asset_class");
    const sortBy = searchParams.get("sort_by") as GPSortField | null;
    const sortOrder = searchParams.get("sort_order") as "asc" | "desc" | null;
    const page = searchParams.get("page");

    if (companyName) p.company_name = companyName;
    if (assetClass) p.asset_class = assetClass;
    if (sortBy) p.sort_by = sortBy;
    if (sortOrder) p.sort_order = sortOrder;
    if (page) p.page = Number(page);
    return p;
  }, [searchParams]);

  const setFilter = useCallback(
    (key: string, value: string) => {
      setSearchParams((prev) => {
        const next = new URLSearchParams(prev);
        if (value) {
          next.set(key, value);
        } else {
          next.delete(key);
        }
        // 필터 변경 시 페이지 리셋
        if (key !== "page") next.delete("page");
        return next;
      });
    },
    [setSearchParams],
  );

  const page = params.page ?? 1;
  const setPage = useCallback(
    (p: number) => setFilter("page", p > 1 ? String(p) : ""),
    [setFilter],
  );

  return { params, setFilter, page, setPage };
}

export default function GPListPage() {
  const navigate = useNavigate();
  const { params, setFilter, page, setPage } = useGPFilters();
  const [search, setSearch] = useState(params.company_name ?? "");

  const { data, isLoading } = useGPs(params);

  // 디바운스된 검색
  const handleSearchChange = useCallback(
    (value: string) => {
      setSearch(value);
      const timer = setTimeout(() => setFilter("company_name", value), 300);
      return () => clearTimeout(timer);
    },
    [setFilter],
  );

  const selectedAssetClasses = useMemo(
    () => new Set((params.asset_class ?? "").split(",").filter(Boolean)),
    [params.asset_class],
  );

  const toggleAssetClass = useCallback(
    (value: string) => {
      const next = new Set(selectedAssetClasses);
      if (next.has(value)) {
        next.delete(value);
      } else {
        next.add(value);
      }
      setFilter("asset_class", [...next].join(","));
    },
    [selectedAssetClasses, setFilter],
  );

  const sortBy = params.sort_by ?? "total_aum";
  const sortOrder = params.sort_order ?? "desc";

  return (
    <div className="space-y-6">
      <PageHero
        title="GPs & Funds"
        subtitle="운용사별 펀드 현황 · KOFIA 데이터 기반"
        compact
      />

      {/* Search & Filters */}
      <Card>
        <div className="space-y-4">
          {/* 검색 */}
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-text-secondary" />
            <input
              type="text"
              value={search}
              onChange={(e) => handleSearchChange(e.target.value)}
              placeholder="운용사명 검색..."
              className="w-full pl-10 pr-4 py-2 rounded-dr-sm border border-border bg-surface text-sm text-text-dark placeholder:text-text-secondary focus:outline-none focus:ring-2 focus:ring-accent/30 shadow-sm"
            />
          </div>

          {/* 자산 클래스 Chip */}
          <div className="flex flex-wrap gap-2">
            {ASSET_CLASS_OPTIONS.map((opt) => (
              <button
                key={opt.value}
                type="button"
                onClick={() => toggleAssetClass(opt.value)}
                className={`px-3 py-1 rounded-full text-xs font-medium border transition-colors ${
                  selectedAssetClasses.has(opt.value)
                    ? "bg-accent text-white border-accent"
                    : "bg-surface text-text-secondary border-border hover:border-accent/50"
                }`}
              >
                {opt.label}
              </button>
            ))}
          </div>

          {/* 정렬 + 전체 펀드 링크 */}
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div className="flex flex-wrap items-center gap-2 text-sm text-text-secondary">
              <span>정렬:</span>
              {(
                [
                  ["total_aum", "AUM"],
                  ["fund_count", "펀드 수"],
                  ["company_name", "이름"],
                ] as const
              ).map(([field, label]) => (
                <button
                  key={field}
                  type="button"
                  onClick={() => {
                    if (sortBy === field) {
                      setFilter(
                        "sort_order",
                        sortOrder === "desc" ? "asc" : "desc",
                      );
                    } else {
                      setFilter("sort_by", field);
                      setFilter("sort_order", "desc");
                    }
                  }}
                  className={`px-2 py-0.5 rounded text-xs ${
                    sortBy === field
                      ? "bg-accent/10 text-accent font-medium"
                      : "hover:bg-surface-alt"
                  }`}
                >
                  {label}
                  {sortBy === field && (sortOrder === "asc" ? " ↑" : " ↓")}
                </button>
              ))}
            </div>

            <Link
              to="/kiis/funds/all"
              className="text-sm text-accent hover:underline"
            >
              전체 펀드 보기 →
            </Link>
          </div>
        </div>
      </Card>

      {/* GP Card Grid */}
      {isLoading ? (
        <Spinner />
      ) : !data?.items.length ? (
        <EmptyState
          icon={Wallet}
          title="운용사가 없습니다"
          description="검색 조건을 변경해 보세요."
        />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {data.items.map((gp) => (
            <button
              key={gp.company_code || gp.company_name}
              type="button"
              onClick={() =>
                navigate(
                  `/kiis/funds/gp/${encodeURIComponent(gp.company_code || gp.company_name)}?name=${encodeURIComponent(gp.company_name)}`,
                )
              }
              className="text-left w-full"
            >
              <Card className="h-full hover-glow transition-all duration-200 cursor-pointer">
                <div className="space-y-3">
                  {/* Header */}
                  <div className="flex items-start justify-between gap-2">
                    <div className="min-w-0">
                      <h3 className="font-semibold text-text-dark truncate">
                        {gp.company_name}
                      </h3>
                      {gp.vintage_range && (
                        <p className="text-xs text-text-secondary mt-0.5">
                          Vintage {gp.vintage_range}
                        </p>
                      )}
                    </div>
                    {gp.has_maturity_alert && (
                      <AlertCircle className="h-4 w-4 text-caution shrink-0 mt-1" />
                    )}
                  </div>

                  {/* Metrics */}
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <p className="text-xs text-text-secondary">펀드 수</p>
                      <p className="text-lg font-semibold text-text-dark tabular-nums">
                        {gp.fund_count}
                        {gp.active_fund_count < gp.fund_count && (
                          <span className="text-xs font-normal text-text-secondary ml-1">
                            ({gp.active_fund_count} active)
                          </span>
                        )}
                      </p>
                    </div>
                    <div>
                      <p className="text-xs text-text-secondary">총 AUM</p>
                      <p className="text-lg font-semibold text-text-dark tabular-nums">
                        {formatAmount(gp.total_aum, "KRW")}
                      </p>
                    </div>
                  </div>

                  {/* Asset Class Badges */}
                  {gp.asset_classes.length > 0 && (
                    <div className="flex flex-wrap gap-1">
                      {gp.asset_classes.map((ac) => (
                        <Badge
                          key={ac}
                          variant={ASSET_CLASS_BADGE_VARIANT[ac] ?? "neutral"}
                        >
                          {ASSET_CLASS_LABELS[ac] ?? ac}
                        </Badge>
                      ))}
                    </div>
                  )}
                </div>
              </Card>
            </button>
          ))}
        </div>
      )}

      {/* Pagination */}
      <Pagination
        page={page}
        totalPages={data ? Math.ceil(data.total / PAGE_SIZE) : 0}
        onPageChange={setPage}
      />
    </div>
  );
}
