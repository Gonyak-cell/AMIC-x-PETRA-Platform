import { useQuery } from "@tanstack/react-query";
import { maApi } from "@/api/maClient";
import type {
  VdrAccessAction,
  VdrAccessLogListResponse,
  BuyerActivitySummary,
} from "@/modules/ma/types/vdr";

const ACCESS_KEY = (txnId: string) => [
  "ma",
  "transactions",
  txnId,
  "vdr",
  "access",
];

export function useVdrAccessLogs(
  txnId: string,
  opts?: {
    buyerId?: string;
    documentId?: string;
    action?: VdrAccessAction;
    skip?: number;
    limit?: number;
  },
) {
  return useQuery<VdrAccessLogListResponse>({
    queryKey: [...ACCESS_KEY(txnId), "logs", opts],
    queryFn: async () => {
      const params: Record<string, string | number> = {};
      if (opts?.buyerId) params.buyer_id = opts.buyerId;
      if (opts?.documentId) params.document_id = opts.documentId;
      if (opts?.action) params.action = opts.action;
      if (opts?.skip != null) params.skip = opts.skip;
      if (opts?.limit != null) params.limit = opts.limit;
      const { data } = await maApi.get(
        `/transactions/${txnId}/vdr/access-logs`,
        { params },
      );
      return data;
    },
    enabled: !!txnId,
  });
}

export function useVdrAccessSummary(txnId: string) {
  return useQuery<BuyerActivitySummary[]>({
    queryKey: [...ACCESS_KEY(txnId), "summary"],
    queryFn: async () => {
      const { data } = await maApi.get(
        `/transactions/${txnId}/vdr/access-summary`,
      );
      return data;
    },
    enabled: !!txnId,
  });
}

export function useDocumentAccessLogs(
  txnId: string,
  docId: string,
  opts?: { skip?: number; limit?: number },
) {
  return useQuery<VdrAccessLogListResponse>({
    queryKey: [...ACCESS_KEY(txnId), "doc", docId, opts],
    queryFn: async () => {
      const params: Record<string, number> = {};
      if (opts?.skip != null) params.skip = opts.skip;
      if (opts?.limit != null) params.limit = opts.limit;
      const { data } = await maApi.get(
        `/transactions/${txnId}/vdr/documents/${docId}/access-logs`,
        { params },
      );
      return data;
    },
    enabled: !!txnId && !!docId,
  });
}
