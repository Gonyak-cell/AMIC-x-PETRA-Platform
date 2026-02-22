import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { maApi } from "@/api/maClient";
import type {
  Bid,
  BidCreate,
  BidUpdate,
  BidComparisonItem,
} from "@/modules/ma/types/bid";

export function useBids(txnId: string, buyerId?: string, bidType?: string) {
  return useQuery<Bid[]>({
    queryKey: ["ma", "transactions", txnId, "bids", { buyerId, bidType }],
    queryFn: async () => {
      const params: Record<string, string> = {};
      if (buyerId) params.buyer_id = buyerId;
      if (bidType) params.type = bidType;
      const { data } = await maApi.get(`/transactions/${txnId}/bids`, {
        params,
      });
      return data;
    },
    enabled: !!txnId,
  });
}

export function useBidComparison(txnId: string) {
  return useQuery<BidComparisonItem[]>({
    queryKey: ["ma", "transactions", txnId, "bids", "comparison"],
    queryFn: async () => {
      const { data } = await maApi.get(
        `/transactions/${txnId}/bids/comparison`,
      );
      return data;
    },
    enabled: !!txnId,
  });
}

export function useCreateBid(txnId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: BidCreate) => {
      const { data } = await maApi.post(
        `/transactions/${txnId}/bids`,
        body,
      );
      return data as Bid;
    },
    onSuccess: () => {
      qc.invalidateQueries({
        queryKey: ["ma", "transactions", txnId, "bids"],
      });
      toast.success("입찰이 등록되었습니다.");
    },
    onError: () => {
      toast.error("입찰 등록에 실패했습니다.");
    },
  });
}

export function useUpdateBid(txnId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({
      bidId,
      body,
    }: {
      bidId: string;
      body: BidUpdate;
    }) => {
      const { data } = await maApi.patch(
        `/transactions/${txnId}/bids/${bidId}`,
        body,
      );
      return data as Bid;
    },
    onSuccess: () => {
      qc.invalidateQueries({
        queryKey: ["ma", "transactions", txnId, "bids"],
      });
      toast.success("입찰이 수정되었습니다.");
    },
    onError: () => {
      toast.error("입찰 수정에 실패했습니다.");
    },
  });
}

export function useDeleteBid(txnId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (bidId: string) => {
      await maApi.delete(`/transactions/${txnId}/bids/${bidId}`);
    },
    onSuccess: () => {
      qc.invalidateQueries({
        queryKey: ["ma", "transactions", txnId, "bids"],
      });
      toast.success("입찰이 삭제되었습니다.");
    },
    onError: () => {
      toast.error("입찰 삭제에 실패했습니다.");
    },
  });
}
