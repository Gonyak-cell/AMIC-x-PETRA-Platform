import { isAxiosError } from "axios";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

import { maApi } from "@/api/maClient";
import { extractApiError } from "@/api/errors";
import type {
  BulkAddBuyersRequest,
  BulkAddBuyersResponse,
  BulkAddVcBuyersRequest,
  DeepDiveResponse,
  KsicSuggestion,
  SICompany,
  SIDataStats,
  SIMappingRequest,
  SIMappingResponse,
  VcMappingByRegResponse,
} from "@/modules/ma/types/si_mapping";

// ── Query Keys ──────────────────────────────────────────

const siQK = {
  stats: ["ma", "si-mapping", "stats"] as const,
  ksicSearch: (q: string) => ["ma", "si-mapping", "ksic", q] as const,
  deepDive: (id: string) => ["ma", "si-mapping", "deep-dive", id] as const,
  searchByName: (name: string) =>
    ["ma", "si-mapping", "search-by-name", name] as const,
  vcMappingResult: (txnId: string) =>
    ["ma", "si-mapping", "vc-result", txnId] as const,
};

// ── 데이터 통계 ──────────────────────────────────────────

export function useSIDataStats() {
  return useQuery<SIDataStats>({
    queryKey: siQK.stats,
    queryFn: async () => {
      const { data } = await maApi.get<SIDataStats>("/si-mapping/stats");
      return data;
    },
  });
}

// ── KSIC 자동완성 검색 ──────────────────────────────────

export function useKsicSearch(query: string) {
  return useQuery<KsicSuggestion[]>({
    queryKey: siQK.ksicSearch(query),
    queryFn: async () => {
      const { data } = await maApi.get<KsicSuggestion[]>(
        `/si-mapping/ksic/search?q=${encodeURIComponent(query)}&limit=20`,
      );
      return data;
    },
    enabled: query.length >= 1,
  });
}

// ── 기업 딥다이브 ───────────────────────────────────────

export function useSIDeepDive(companyId: string | null) {
  return useQuery<DeepDiveResponse>({
    queryKey: siQK.deepDive(companyId ?? ""),
    queryFn: async () => {
      const { data } = await maApi.get<DeepDiveResponse>(
        `/si-mapping/companies/${companyId}/deep-dive`,
      );
      return data;
    },
    enabled: !!companyId,
    staleTime: 5 * 60 * 1000,
  });
}

// ── 기업명으로 SICompany 검색 ────────────────────────────

export function useSICompanyByName(name: string | null) {
  return useQuery<SICompany | null>({
    queryKey: siQK.searchByName(name ?? ""),
    queryFn: async () => {
      try {
        const { data } = await maApi.get<SICompany | null>(
          `/si-mapping/companies/search-by-name`,
          { params: { name } },
        );
        return data;
      } catch (error) {
        if (isAxiosError(error) && error.response?.status === 404) {
          return null;
        }
        throw error;
      }
    },
    enabled: !!name,
    staleTime: 10 * 60 * 1000,
  });
}

// ── SI 매핑 실행 ─────────────────────────────────────────

export function useSIMapping() {
  return useMutation<SIMappingResponse, Error, SIMappingRequest>({
    mutationFn: async (body) => {
      const { data } = await maApi.post<SIMappingResponse>(
        "/si-mapping/map",
        body,
      );
      return data;
    },
    onSuccess: (data) => {
      toast.success(`${data.all_candidates.length}개 후보 기업 발견`);
    },
    onError: (err) => {
      toast.error(extractApiError(err, "SI 매핑 실패"));
    },
  });
}

// ── VC 매핑 결과 캐시 조회 ──────────────────────────────

export function useVcMappingResult(txnId: string) {
  return useQuery<VcMappingByRegResponse | null>({
    queryKey: siQK.vcMappingResult(txnId),
    queryFn: () => null,
    enabled: false,
    staleTime: Infinity,
    gcTime: Infinity,
  });
}

// ── 등록번호 기반 VC 매핑 ─────────────────────────────────

export function useVcMappingByRegistration(txnId: string) {
  const qc = useQueryClient();
  return useMutation<
    VcMappingByRegResponse,
    Error,
    {
      corp_reg_no?: string;
      biz_reg_no?: string;
      min_revenue?: number;
      top_n?: number;
    }
  >({
    mutationFn: async (params) => {
      const { data } = await maApi.get<VcMappingByRegResponse>(
        "/si-mapping/vc-map-by-registration",
        { params },
      );
      return data;
    },
    onSuccess: (data) => {
      qc.setQueryData(siQK.vcMappingResult(txnId), data);
      toast.success(`${data.company.company_name}: Value Chain 매핑 완료`);
    },
    // onError toast 제거 — SIMappingPanel이 인라인 에러 UI로 처리 (IMP-1)
  });
}

// ── VC 기업 Long List 일괄 등록 ──────────────────────────

export function useBulkAddVcBuyers(txnId: string) {
  const qc = useQueryClient();
  return useMutation<BulkAddBuyersResponse, Error, BulkAddVcBuyersRequest>({
    mutationFn: async (body) => {
      const { data } = await maApi.post<BulkAddBuyersResponse>(
        `/transactions/${txnId}/vc-mapping/add-buyers`,
        body,
      );
      return data;
    },
    onSuccess: (res) => {
      qc.invalidateQueries({
        queryKey: ["ma", "transactions", txnId, "buyers"],
      });
      toast.success(
        `${res.added_count}개 기업이 Long List에 추가되었습니다.` +
          (res.skipped_count > 0
            ? ` (${res.skipped_count}개 중복 건너뜀)`
            : ""),
      );
    },
    onError: (err) => {
      toast.error(extractApiError(err, "Long List 등록 실패"));
    },
  });
}

// ── 일괄 BuyerCandidate 등록 ────────────────────────────

export function useBulkAddBuyers(txnId: string) {
  const qc = useQueryClient();
  return useMutation<BulkAddBuyersResponse, Error, BulkAddBuyersRequest>({
    mutationFn: async (body) => {
      const { data } = await maApi.post<BulkAddBuyersResponse>(
        `/transactions/${txnId}/si-mapping/add-buyers`,
        body,
      );
      return data;
    },
    onSuccess: (res) => {
      qc.invalidateQueries({
        queryKey: ["ma", "transactions", txnId, "buyers"],
      });
      toast.success(
        `${res.added_count}개 기업이 Long List에 추가되었습니다.` +
          (res.skipped_count > 0
            ? ` (${res.skipped_count}개 중복 건너뜀)`
            : ""),
      );
    },
    onError: (err) => {
      toast.error(extractApiError(err, "Long List 등록 실패"));
    },
  });
}
