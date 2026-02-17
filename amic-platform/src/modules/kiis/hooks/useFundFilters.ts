import { useSearchParams } from "react-router-dom";
import { useMemo, useCallback } from "react";
import type { FundListParams, FundSortField } from "@/modules/kiis/types/fund";
import { parseAmountPreset } from "@/modules/kiis/constants/fundFilters";

const FILTER_KEYS = [
  "company_name",
  "fund_name",
  "fund_type",
  "legal_type",
  "asset_class",
  "fund_status",
  "vintage_from",
  "vintage_to",
  "amount_preset",
] as const;

export function useFundFilters() {
  const [searchParams, setSearchParams] = useSearchParams();

  const params = useMemo<FundListParams>(() => {
    const amountPreset = searchParams.get("amount_preset") || "";
    const { min, max } = parseAmountPreset(amountPreset);

    return {
      company_name: searchParams.get("company_name") || undefined,
      fund_name: searchParams.get("fund_name") || undefined,
      fund_type: searchParams.get("fund_type") || undefined,
      legal_type: searchParams.get("legal_type") || undefined,
      asset_class: searchParams.get("asset_class") || undefined,
      fund_status: searchParams.get("fund_status") || undefined,
      vintage_from: searchParams.get("vintage_from")
        ? Number(searchParams.get("vintage_from"))
        : undefined,
      vintage_to: searchParams.get("vintage_to")
        ? Number(searchParams.get("vintage_to"))
        : undefined,
      amount_min: min,
      amount_max: max,
      sort_by: (searchParams.get("sort_by") as FundSortField) || undefined,
      sort_order: (searchParams.get("sort_order") as "asc" | "desc") || undefined,
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
    [setSearchParams]
  );

  /** 체크박스 그룹용: 쉼표 구분 값 토글 */
  const toggleFilter = useCallback(
    (key: string, value: string) => {
      setSearchParams((prev) => {
        const next = new URLSearchParams(prev);
        const current = next.get(key);
        const values = current ? current.split(",").filter(Boolean) : [];

        if (values.includes(value)) {
          const updated = values.filter((v) => v !== value);
          if (updated.length > 0) {
            next.set(key, updated.join(","));
          } else {
            next.delete(key);
          }
        } else {
          next.set(key, [...values, value].join(","));
        }
        next.set("page", "1");
        return next;
      });
    },
    [setSearchParams]
  );

  /** 특정 필터 키의 선택된 값 배열 반환 */
  const getSelected = useCallback(
    (key: string): string[] => {
      const value = searchParams.get(key);
      return value ? value.split(",").filter(Boolean) : [];
    },
    [searchParams]
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
    [setSearchParams]
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
    toggleFilter,
    getSelected,
    setPage,
    resetFilters,
    activeFilterCount,
    page: params.page ?? 1,
  };
}
