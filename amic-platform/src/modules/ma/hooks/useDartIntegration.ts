import { useQuery } from "@tanstack/react-query";
import { maApi } from "@/api/maClient";
import type {
  DartCompanySuggestion,
  DartFinancialSummary,
} from "@/modules/ma/types/marketing_log";

export function useDartCompanySearch(txnId: string, query: string) {
  return useQuery<DartCompanySuggestion[]>({
    queryKey: ["ma", "transactions", txnId, "dart-search", query],
    queryFn: async () => {
      const { data } = await maApi.get(
        `/transactions/${txnId}/buyers/dart-search`,
        { params: { q: query } },
      );
      return data;
    },
    enabled: !!txnId && query.length >= 1,
    staleTime: 60_000,
  });
}

export function useDartFinancialSummary(
  txnId: string,
  buyerId: string,
  enabled = true,
) {
  return useQuery<DartFinancialSummary>({
    queryKey: ["ma", "transactions", txnId, "buyers", buyerId, "dart-summary"],
    queryFn: async () => {
      const { data } = await maApi.get(
        `/transactions/${txnId}/buyers/${buyerId}/dart-summary`,
      );
      return data;
    },
    enabled: !!txnId && !!buyerId && enabled,
    staleTime: 5 * 60_000,
    retry: false,
  });
}
