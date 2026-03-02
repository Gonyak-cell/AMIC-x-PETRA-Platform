import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { maApi } from "@/api/maClient";
import { extractApiError } from "@/api/errors";
import type {
  ApprovalRequest,
  ApprovalCreate,
  ApprovalDecision,
  ApprovalListResponse,
  ApprovalSummary,
  ApprovalType,
  ApprovalStatus,
} from "@/modules/ma/types/approval";

export function useApprovals(
  txnId: string,
  opts?: { type?: ApprovalType; status?: ApprovalStatus },
  active = true,
) {
  return useQuery<ApprovalListResponse>({
    queryKey: ["ma", "transactions", txnId, "approvals", opts],
    queryFn: async () => {
      const params: Record<string, string> = {};
      if (opts?.type) params.approval_type = opts.type;
      if (opts?.status) params.approval_status = opts.status;
      const { data } = await maApi.get(`/transactions/${txnId}/approvals`, {
        params,
      });
      return data;
    },
    enabled: !!txnId && active,
  });
}

export function useApprovalSummary(txnId: string, active = true) {
  return useQuery<ApprovalSummary>({
    queryKey: ["ma", "transactions", txnId, "approvals", "summary"],
    queryFn: async () => {
      const { data } = await maApi.get(
        `/transactions/${txnId}/approvals/summary`,
      );
      return data;
    },
    enabled: !!txnId && active,
  });
}

export function useMyPendingApprovals() {
  return useQuery<ApprovalListResponse>({
    queryKey: ["ma", "approvals", "pending", "me"],
    queryFn: async () => {
      const { data } = await maApi.get("/approvals/pending/me");
      return data;
    },
  });
}

export function useCreateApproval(txnId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: ApprovalCreate) => {
      const { data } = await maApi.post(
        `/transactions/${txnId}/approvals`,
        body,
      );
      return data as ApprovalRequest;
    },
    onSuccess: () => {
      qc.invalidateQueries({
        queryKey: ["ma", "transactions", txnId, "approvals"],
      });
      toast.success("승인 요청이 생성되었습니다.");
    },
    onError: (err: unknown) => {
      toast.error(extractApiError(err, "승인 요청 생성에 실패했습니다."));
    },
  });
}

export function useDecideApproval() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({
      approvalId,
      body,
    }: {
      approvalId: string;
      body: ApprovalDecision;
    }) => {
      const { data } = await maApi.post(
        `/approvals/${approvalId}/decide`,
        body,
      );
      return data as ApprovalRequest;
    },
    onSuccess: (data) => {
      // pending/me 목록 무효화
      qc.invalidateQueries({ queryKey: ["ma", "approvals"] });
      // 해당 거래의 approval 캐시만 무효화
      if (data.transaction_id) {
        qc.invalidateQueries({
          queryKey: ["ma", "transactions", data.transaction_id, "approvals"],
        });
      }
      toast.success("승인 결정이 완료되었습니다.");
    },
    onError: (err: unknown) => {
      toast.error(extractApiError(err, "승인 결정에 실패했습니다."));
    },
  });
}

export function useCancelApproval() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (approvalId: string) => {
      const { data } = await maApi.post(`/approvals/${approvalId}/cancel`);
      return data as ApprovalRequest;
    },
    onSuccess: (data) => {
      qc.invalidateQueries({ queryKey: ["ma", "approvals"] });
      if (data.transaction_id) {
        qc.invalidateQueries({
          queryKey: ["ma", "transactions", data.transaction_id, "approvals"],
        });
      }
      toast.success("승인 요청이 취소되었습니다.");
    },
    onError: (err: unknown) => {
      toast.error(extractApiError(err, "승인 요청 취소에 실패했습니다."));
    },
  });
}
