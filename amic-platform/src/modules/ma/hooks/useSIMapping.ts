import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { isAxiosError } from "axios";
import { toast } from "sonner";

import { maApi } from "@/api/maClient";

/** axios 에러에서 BE detail 메시지 추출 (없으면 기본 message) */
function extractDetail(err: Error): string {
  if (isAxiosError(err)) {
    const detail = (err.response?.data as { detail?: string } | undefined)
      ?.detail;
    if (detail) return detail;
  }
  return err.message;
}
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
      const { data } = await maApi.get<SICompany | null>(
        `/si-mapping/companies/search-by-name`,
        { params: { name } },
      );
      return data;
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
      toast.error(`SI 매핑 실패: ${extractDetail(err)}`);
    },
  });
}

// ── 등록번호 기반 VC 매핑 ─────────────────────────────────

export function useVcMappingByRegistration() {
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
      toast.success(`${data.company.company_name}: Value Chain 매핑 완료`);
    },
    onError: (err) => {
      toast.error(`VC 매핑 실패: ${extractDetail(err)}`);
    },
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
      toast.error(`Long List 등록 실패: ${extractDetail(err)}`);
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
      toast.error(`Long List 등록 실패: ${extractDetail(err)}`);
    },
  });
}
