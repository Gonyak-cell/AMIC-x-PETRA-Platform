import { useSearchParams } from "react-router-dom";
import { useMemo, useCallback } from "react";
import type { CompanyListParams, SearchType } from "@/modules/kiis/types/company";

const FILTER_KEYS = ["search", "search_type", "corp_cls"] as const;

export function useCompanyFilters() {
  const [searchParams, setSearchParams] = useSearchParams();

  const params = useMemo<CompanyListParams>(() => {
    return {
      search: searchParams.get("search") || undefined,
      search_type: (searchParams.get("search_type") as SearchType) || "name",
      corp_cls: searchParams.get("corp_cls") || undefined,
      page: searchParams.get("page") ? Number(searchParams.get("page")) : 1,
      size: 20,
    };
  }, [searchParams]);

  /** 단일 필터 값 설정 */
  const setFilter = useCallback(
    (key: string, value: string | undefined) => {
      setSearchParams((prev) => {
        const next = new URLSearchParams(prev);
        if (value) {
          next.set(key, value);
        } else {
          next.delete(key);
        }
        next.set("page", "1");
        return next;
      });
    },
    [setSearchParams],
  );

  /** 체크박스 그룹용: 쉼표 구분 값 토글 */
  const getSelected = useCallback(
    (key: string): string[] => {
      const value = searchParams.get(key);
      return value ? value.split(",").filter(Boolean) : [];
    },
    [searchParams],
  );

  /** 페이지 변경 */
  const setPage = useCallback(
    (page: number) => {
      setSearchParams((prev) => {
        const next = new URLSearchParams(prev);
        next.set("page", String(page));
        return next;
      });
    },
    [setSearchParams],
  );

  /** 전체 필터 초기화 */
  const resetFilters = useCallback(() => {
    setSearchParams({});
  }, [setSearchParams]);

  /** 적용 중인 필터 개수 */
  const activeFilterCount = useMemo(() => {
    return FILTER_KEYS.filter((k) => searchParams.has(k)).length;
  }, [searchParams]);

  return {
    params,
    setFilter,
    getSelected,
    setPage,
    resetFilters,
    activeFilterCount,
    page: params.page ?? 1,
  };
}
