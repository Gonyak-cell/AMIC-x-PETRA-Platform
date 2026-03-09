import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { maApi } from "@/api/maClient";
import type {
  MarketingLog,
  MarketingLogCreate,
  MarketingLogUpdate,
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

export function useMarketingLogs(
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

export function useCreateMarketingLog(txnId: string, buyerId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: MarketingLogCreate) => {
      const { data } = await maApi.post(
        `/transactions/${txnId}/buyers/${buyerId}/marketing-logs`,
        body,
      );
      return data as MarketingLog;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: KEY(txnId, buyerId) });
      qc.invalidateQueries({
        queryKey: [
          "ma",
          "transactions",
          txnId,
          "buyers",
          buyerId,
          "stage-summary",
        ],
      });
      qc.invalidateQueries({
        queryKey: ["ma", "transactions", txnId, "short-list", "overview"],
      });
      toast.success("마케팅 로그가 생성되었습니다.");
    },
    onError: (err: Error) => {
      toast.error(err.message || "마케팅 로그 생성에 실패했습니다.");
    },
  });
}

export function useUpdateMarketingLog(txnId: string, buyerId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({
      logId,
      body,
    }: {
      logId: string;
      body: MarketingLogUpdate;
    }) => {
      const { data } = await maApi.patch(
        `/transactions/${txnId}/buyers/${buyerId}/marketing-logs/${logId}`,
        body,
      );
      return data as MarketingLog;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: KEY(txnId, buyerId) });
      qc.invalidateQueries({
        queryKey: [
          "ma",
          "transactions",
          txnId,
          "buyers",
          buyerId,
          "stage-summary",
        ],
      });
      qc.invalidateQueries({
        queryKey: ["ma", "transactions", txnId, "short-list", "overview"],
      });
      toast.success("마케팅 로그가 수정되었습니다.");
    },
    onError: (err: Error) => {
      toast.error(err.message || "마케팅 로그 수정에 실패했습니다.");
    },
  });
}

export function useDeleteMarketingLog(txnId: string, buyerId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (logId: string) => {
      await maApi.delete(
        `/transactions/${txnId}/buyers/${buyerId}/marketing-logs/${logId}`,
      );
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: KEY(txnId, buyerId) });
      qc.invalidateQueries({
        queryKey: [
          "ma",
          "transactions",
          txnId,
          "buyers",
          buyerId,
          "stage-summary",
        ],
      });
      qc.invalidateQueries({
        queryKey: ["ma", "transactions", txnId, "short-list", "overview"],
      });
      toast.success("마케팅 로그가 삭제되었습니다.");
    },
    onError: (err: Error) => {
      toast.error(err.message || "마케팅 로그 삭제에 실패했습니다.");
    },
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
