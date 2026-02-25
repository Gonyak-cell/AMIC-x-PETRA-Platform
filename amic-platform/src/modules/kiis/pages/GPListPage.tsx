import { useState, useMemo, useCallback, useRef } from "react";
import { useNavigate, useSearchParams, Link } from "react-router-dom";
import { Wallet, AlertCircle, Search, Database, Globe } from "lucide-react";
import { useGPs } from "@/modules/kiis/hooks/useGPs";
import { useGPRegistry } from "@/modules/kiis/hooks/useGPRegistry";
import { useScrollReveal } from "@/hooks/useScrollReveal";
import {
  Card,
  Badge,
  EmptyState,
  Pagination,
  PageHero,
  Spinner,
} from "@/components/ui";
import type { GPListParams, GPSortField } from "@/modules/kiis/types/gp";
import type { GPRegistryItem } from "@/modules/kiis/types/gpRegistry";
import { formatAmountKRW } from "@/lib/format";
import {
  ASSET_CLASS_OPTIONS,
  ASSET_CLASS_BADGE_VARIANT,
  ASSET_CLASS_LABELS,
} from "@/modules/kiis/constants/fundFilters";
import heroImg from "@/assets/images/heroes/forestgp-vc.jpg";

const PAGE_SIZE = 20;

type DataSource = "kofia" | "registry";

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

  const source = (searchParams.get("source") as DataSource) ?? "kofia";
  const setSource = useCallback(
    (s: DataSource) => {
      setSearchParams((prev) => {
        const next = new URLSearchParams(prev);
        if (s === "kofia") {
          next.delete("source");
        } else {
          next.set("source", s);
        }
        next.delete("page");
        return next;
      });
    },
    [setSearchParams],
  );

  return { params, setFilter, page, setPage, source, setSource };
}

/* ─── 공공데이터 등록 운용사 카드 ─── */
function RegistryGPCard({ gp }: { gp: GPRegistryItem }) {
  return (
    <Card className="h-full hover-glow transition-all duration-200">
      <div className="space-y-3">
        <div className="min-w-0">
          <h3 className="font-semibold text-text-dark truncate">
            {gp.company_name}
          </h3>
          {gp.company_name_en && (
            <p className="text-xs text-text-secondary mt-0.5 truncate">
              {gp.company_name_en}
            </p>
          )}
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div>
            <p className="text-xs text-text-secondary">펀드 수</p>
            <p className="text-lg font-semibold text-text-dark tabular-nums">
              {gp.fund_count ?? "—"}
            </p>
          </div>
          <div>
            <p className="text-xs text-text-secondary">AUM</p>
            <p className="text-lg font-semibold text-text-dark tabular-nums">
              {gp.aum ? formatAmountKRW(gp.aum) : "—"}
            </p>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-3 text-xs text-text-secondary">
          <div>
            <p>임직원</p>
            <p className="text-text-dark font-medium">
              {gp.employee_count ?? "—"}명
            </p>
          </div>
          <div>
            <p>설립일</p>
            <p className="text-text-dark font-medium">
              {gp.established_date || "—"}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-1.5">
          <Badge variant="neutral">
            <Globe className="h-3 w-3 mr-1" />
            공공데이터
          </Badge>
          {gp.data_date && (
            <span className="text-xs text-text-secondary">
              기준: {gp.data_date}
            </span>
          )}
        </div>
      </div>
    </Card>
  );
}

export default function GPListPage() {
  const navigate = useNavigate();
  const { params, setFilter, page, setPage, source, setSource } =
    useGPFilters();
  const [search, setSearch] = useState(params.company_name ?? "");

  const kofiaQuery = useGPs(params);
  const registryQuery = useGPRegistry({
    company_name: params.company_name,
    page,
    size: PAGE_SIZE,
  });

  const isKofia = source === "kofia";
  const data = isKofia ? kofiaQuery.data : registryQuery.data;
  const isLoading = isKofia ? kofiaQuery.isLoading : registryQuery.isLoading;

  const gridRef = useRef<HTMLDivElement>(null);
  useScrollReveal(gridRef, { stagger: 0.05, y: 20 }, [isLoading, data?.items.length]);

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
        subtitle="운용사별 펀드 현황 · KOFIA + 공공데이터포털"
        compact
        backgroundImage={heroImg}
        backgroundOpacity={0.18}
      />

      {/* 데이터소스 전환 탭 */}
      <div className="flex gap-2">
        <button
          type="button"
          onClick={() => setSource("kofia")}
          className={`flex items-center gap-2 px-4 py-2 rounded-dr-sm text-sm font-medium transition-colors ${
            isKofia
              ? "bg-accent text-white shadow-sm"
              : "bg-white text-text-secondary border border-border hover:border-accent/50"
          }`}
        >
          <Database className="h-4 w-4" />
          KOFIA 펀드 데이터
        </button>
        <button
          type="button"
          onClick={() => setSource("registry")}
          className={`flex items-center gap-2 px-4 py-2 rounded-dr-sm text-sm font-medium transition-colors ${
            !isKofia
              ? "bg-accent text-white shadow-sm"
              : "bg-white text-text-secondary border border-border hover:border-accent/50"
          }`}
        >
          <Globe className="h-4 w-4" />
          등록 운용사 (공공데이터)
        </button>
      </div>

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
              className="w-full pl-10 pr-4 py-2 rounded-dr-sm border border-border bg-white text-sm text-text-dark placeholder:text-text-secondary focus:outline-none focus:ring-2 focus:ring-accent/30 shadow-sm"
            />
          </div>

          {/* 자산 클래스 Chip — KOFIA 전용 */}
          {isKofia && (
            <div className="flex flex-wrap gap-2">
              {ASSET_CLASS_OPTIONS.map((opt) => (
                <button
                  key={opt.value}
                  type="button"
                  onClick={() => toggleAssetClass(opt.value)}
                  className={`px-3 py-1 rounded-full text-xs font-medium border transition-colors ${
                    selectedAssetClasses.has(opt.value)
                      ? "bg-accent text-white border-accent"
                      : "bg-white text-text-secondary border-border hover:border-accent/50"
                  }`}
                >
                  {opt.label}
                </button>
              ))}
            </div>
          )}

          {/* 정렬 + 전체 펀드 링크 — KOFIA 전용 */}
          {isKofia && (
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
                        : "hover:bg-white-alt"
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
          )}

          {/* 공공데이터 설명 */}
          {!isKofia && (
            <p className="text-xs text-text-secondary">
              공공데이터포털 금융통계 기반 등록 자산운용사 정보입니다. KOFIA
              DIS에 미포함된 기관전용 사모펀드 운용사도 포함됩니다.
            </p>
          )}
        </div>
      </Card>

      {/* GP Card Grid */}
      {isLoading ? (
        <Spinner />
      ) : !data?.items.length ? (
        <EmptyState
          icon={Wallet}
          title="운용사가 없습니다"
          description={
            !isKofia && !params.company_name
              ? "DATA_GO_KR_API_KEY가 설정되어 있는지 확인하세요."
              : "검색 조건을 변경해 보세요."
          }
        />
      ) : (
        <div
          ref={gridRef}
          className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4"
        >
          {isKofia
            ? data.items.map((gp) => {
                const kofiaGp = gp as (typeof kofiaQuery.data extends { items: (infer T)[] } | undefined ? T : never);
                return (
                  <button
                    key={kofiaGp.company_code || kofiaGp.company_name}
                    type="button"
                    onClick={() =>
                      navigate(
                        `/kiis/funds/gp/${encodeURIComponent(kofiaGp.company_code || kofiaGp.company_name)}?name=${encodeURIComponent(kofiaGp.company_name)}`,
                      )
                    }
                    className="text-left w-full"
                  >
                    <Card className="h-full hover-glow transition-all duration-200 cursor-pointer">
                      <div className="space-y-3">
                        <div className="flex items-start justify-between gap-2">
                          <div className="min-w-0">
                            <h3 className="font-semibold text-text-dark truncate">
                              {kofiaGp.company_name}
                            </h3>
                            {kofiaGp.vintage_range && (
                              <p className="text-xs text-text-secondary mt-0.5">
                                Vintage {kofiaGp.vintage_range}
                              </p>
                            )}
                          </div>
                          {kofiaGp.has_maturity_alert && (
                            <AlertCircle className="h-4 w-4 text-caution shrink-0 mt-1" />
                          )}
                        </div>

                        <div className="grid grid-cols-2 gap-3">
                          <div>
                            <p className="text-xs text-text-secondary">
                              펀드 수
                            </p>
                            <p className="text-lg font-semibold text-text-dark tabular-nums">
                              {kofiaGp.fund_count}
                              {kofiaGp.active_fund_count <
                                kofiaGp.fund_count && (
                                <span className="text-xs font-normal text-text-secondary ml-1">
                                  ({kofiaGp.active_fund_count} active)
                                </span>
                              )}
                            </p>
                          </div>
                          <div>
                            <p className="text-xs text-text-secondary">
                              총 AUM
                            </p>
                            <p className="text-lg font-semibold text-text-dark tabular-nums">
                              {formatAmountKRW(kofiaGp.total_aum)}
                            </p>
                          </div>
                        </div>

                        {kofiaGp.asset_classes.length > 0 && (
                          <div className="flex flex-wrap gap-1">
                            {kofiaGp.asset_classes.map((ac) => (
                              <Badge
                                key={ac}
                                variant={
                                  ASSET_CLASS_BADGE_VARIANT[ac] ?? "neutral"
                                }
                              >
                                {ASSET_CLASS_LABELS[ac] ?? ac}
                              </Badge>
                            ))}
                          </div>
                        )}
                      </div>
                    </Card>
                  </button>
                );
              })
            : data.items.map((gp) => (
                <RegistryGPCard
                  key={(gp as GPRegistryItem).finance_company_code || (gp as GPRegistryItem).company_name}
                  gp={gp as GPRegistryItem}
                />
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
