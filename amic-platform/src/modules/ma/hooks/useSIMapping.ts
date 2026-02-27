import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

import { maApi } from "@/api/maClient";
import type {
  BulkAddBuyersRequest,
  BulkAddBuyersResponse,
  DeepDiveResponse,
  KsicSuggestion,
  SIDataStats,
  SIMappingRequest,
  SIMappingResponse,
} from "@/modules/ma/types/si_mapping";

// ── Query Keys ──────────────────────────────────────────

const siQK = {
  stats: ["ma", "si-mapping", "stats"] as const,
  ksicSearch: (q: string) => ["ma", "si-mapping", "ksic", q] as const,
  deepDive: (id: string) => ["ma", "si-mapping", "deep-dive", id] as const,
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
      toast.error(`SI 매핑 실패: ${err.message}`);
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
      toast.error(`Long List 등록 실패: ${err.message}`);
    },
  });
}
