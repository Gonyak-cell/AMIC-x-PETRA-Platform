import { useQuery } from "@tanstack/react-query";
import { maApi } from "@/api/maClient";
import type {
  MarketingLog,
  MarketingStage,
  BuyerStageSummary,
} from "@/modules/ma/types/marketing_log";

const KEY = (txnId: string, buyerId: string) => [
  "ma",
  "transactions",
  txnId,
  "buyers",
  buyerId,
  "marketing-logs",
];

export function useBuyerMarketingHistory(
  txnId: string,
  buyerId: string,
  opts?: { stage?: MarketingStage },
) {
  return useQuery<MarketingLog[]>({
    queryKey: [...KEY(txnId, buyerId), opts],
    queryFn: async () => {
      const params: Record<string, string> = {};
      if (opts?.stage) params.stage = opts.stage;
      const { data } = await maApi.get(
        `/transactions/${txnId}/buyers/${buyerId}/marketing-logs`,
        { params },
      );
      return data;
    },
    enabled: !!txnId && !!buyerId,
  });
}

// ── 단계별 요약 ──────────────────────────────────────────

export function useMarketingStageSummary(txnId: string, buyerId: string) {
  return useQuery<BuyerStageSummary>({
    queryKey: ["ma", "transactions", txnId, "buyers", buyerId, "stage-summary"],
    queryFn: async () => {
      const { data } = await maApi.get(
        `/transactions/${txnId}/buyers/${buyerId}/marketing-stage-summary`,
      );
      return data;
    },
    enabled: !!txnId && !!buyerId,
  });
}

export function useShortListOverview(txnId: string) {
  return useQuery<BuyerStageSummary[]>({
    queryKey: ["ma", "transactions", txnId, "short-list", "overview"],
    queryFn: async () => {
      const { data } = await maApi.get(
        `/transactions/${txnId}/short-list/marketing-overview`,
      );
      return data;
    },
    enabled: !!txnId,
  });
}
