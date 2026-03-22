import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

import { extractApiError } from "@/api/errors";
import { maApi } from "@/api/maClient";
import type {
  Bid,
  BidComparisonItem,
  BidCreate,
  BidImportResult,
  BidType,
  BidUpdate,
} from "@/modules/ma/types/bid";

function invalidateBidQueries(
  qc: ReturnType<typeof useQueryClient>,
  txnId: string,
) {
  qc.invalidateQueries({
    queryKey: ["ma", "transactions", txnId, "bids"],
  });
  qc.invalidateQueries({
    queryKey: ["ma", "transactions", txnId, "buyers"],
  });
  qc.invalidateQueries({
    queryKey: ["ma", "transactions", txnId, "bidding-summary"],
  });
}

export function useBids(
  txnId: string,
  buyerId?: string,
  bidType?: string,
  active = true,
) {
  return useQuery<Bid[]>({
    queryKey: ["ma", "transactions", txnId, "bids", { buyerId, bidType }],
    queryFn: async () => {
      const params: Record<string, string> = {};
      if (buyerId) {
        params.buyer_id = buyerId;
      }
      if (bidType) {
        params.type = bidType;
      }
      const { data } = await maApi.get(`/transactions/${txnId}/bids`, {
        params,
      });
      return data;
    },
    enabled: !!txnId && active,
  });
}

export function useBidComparison(txnId: string, active = true) {
  return useQuery<BidComparisonItem[]>({
    queryKey: ["ma", "transactions", txnId, "bids", "comparison"],
    queryFn: async () => {
      const { data } = await maApi.get(
        `/transactions/${txnId}/bids/comparison`,
      );
      return data;
    },
    enabled: !!txnId && active,
  });
}

export function useCreateBid(txnId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: BidCreate) => {
      const { data } = await maApi.post(`/transactions/${txnId}/bids`, body);
      return data as Bid;
    },
    onSuccess: () => {
      invalidateBidQueries(qc, txnId);
      toast.success("입찰 정보를 등록했습니다.");
    },
    onError: (err) => {
      toast.error(extractApiError(err, "입찰 등록에 실패했습니다."));
    },
  });
}

export function useUpdateBid(txnId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ bidId, body }: { bidId: string; body: BidUpdate }) => {
      const { data } = await maApi.patch(
        `/transactions/${txnId}/bids/${bidId}`,
        body,
      );
      return data as Bid;
    },
    onSuccess: () => {
      invalidateBidQueries(qc, txnId);
      toast.success("입찰 정보를 수정했습니다.");
    },
    onError: (err) => {
      toast.error(extractApiError(err, "입찰 수정에 실패했습니다."));
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
      invalidateBidQueries(qc, txnId);
      toast.success("입찰 정보를 삭제했습니다.");
    },
    onError: (err) => {
      toast.error(extractApiError(err, "입찰 삭제에 실패했습니다."));
    },
  });
}

export function useImportBidFromAttachment(txnId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({
      attachmentId,
      buyerCandidateId,
      bidType,
    }: {
      attachmentId: string;
      buyerCandidateId?: string;
      bidType?: BidType;
    }) => {
      const { data } = await maApi.post(
        `/transactions/${txnId}/bids/import-from-attachment`,
        {
          attachment_id: attachmentId,
          buyer_candidate_id: buyerCandidateId,
          bid_type: bidType,
        },
      );
      return data as BidImportResult;
    },
    onSuccess: (result) => {
      invalidateBidQueries(qc, txnId);
      toast.success(
        result.created
          ? `${result.buyer_name} ${result.bid.bid_type} 입찰을 자동 등록했습니다.`
          : `${result.buyer_name} ${result.bid.bid_type} 입찰 정보를 문서 기준으로 보강했습니다.`,
      );
      if (result.warnings.length > 0) {
        toast.info(result.warnings[0]);
      }
    },
    onError: (err) => {
      toast.error(
        extractApiError(err, "입찰 문서 자동 기재에 실패했습니다."),
      );
    },
  });
}
