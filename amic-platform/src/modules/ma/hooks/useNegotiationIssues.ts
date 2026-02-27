import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { maApi } from "@/api/maClient";
import type {
  NegotiationIssue,
  NegotiationIssueCreate,
  NegotiationIssueUpdate,
  NegotiationIssueListResponse,
  NegotiationIssueStatus,
  NegotiationIssuePriority,
  IssueDecisionStatus,
  AIClauseSuggestionResponse,
} from "@/modules/ma/types/negotiation_issue";

const KEY = (txnId: string) => ["ma", "transactions", txnId, "negotiation-issues"];

export function useNegotiationIssues(
  txnId: string,
  opts?: { status?: NegotiationIssueStatus; priority?: NegotiationIssuePriority; meetingId?: string; contractId?: string },
) {
  return useQuery<NegotiationIssueListResponse>({
    queryKey: [...KEY(txnId), opts],
    queryFn: async () => {
      const params: Record<string, string> = {};
      if (opts?.status) params.status = opts.status;
      if (opts?.priority) params.priority = opts.priority;
      if (opts?.meetingId) params.meeting_id = opts.meetingId;
      if (opts?.contractId) params.contract_id = opts.contractId;
      const { data } = await maApi.get(`/transactions/${txnId}/negotiation-issues`, { params });
      return data;
    },
    enabled: !!txnId,
  });
}

export function useCreateNegotiationIssue(txnId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: NegotiationIssueCreate) => {
      const { data } = await maApi.post(`/transactions/${txnId}/negotiation-issues`, body);
      return data as NegotiationIssue;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: KEY(txnId) });
      toast.success("협상 이견이 등록되었습니다.");
    },
    onError: () => {
      toast.error("협상 이견 등록에 실패했습니다.");
    },
  });
}

export function useUpdateNegotiationIssue(txnId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ issueId, body }: { issueId: string; body: NegotiationIssueUpdate }) => {
      const { data } = await maApi.patch(
        `/transactions/${txnId}/negotiation-issues/${issueId}`,
        body,
      );
      return data as NegotiationIssue;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: KEY(txnId) });
      toast.success("협상 이견이 수정되었습니다.");
    },
    onError: () => {
      toast.error("협상 이견 수정에 실패했습니다.");
    },
  });
}

export function useDeleteNegotiationIssue(txnId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (issueId: string) => {
      await maApi.delete(`/transactions/${txnId}/negotiation-issues/${issueId}`);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: KEY(txnId) });
      toast.success("협상 이견이 삭제되었습니다.");
    },
    onError: () => {
      toast.error("협상 이견 삭제에 실패했습니다.");
    },
  });
}

export function useBatchUpdateDecision(txnId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (items: { issue_id: string; decision_status: IssueDecisionStatus }[]) => {
      const { data } = await maApi.patch(
        `/transactions/${txnId}/negotiation-issues/batch-decision`,
        items,
      );
      return data as NegotiationIssue[];
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: KEY(txnId) });
      toast.success("의사결정이 업데이트되었습니다.");
    },
    onError: () => {
      toast.error("의사결정 업데이트에 실패했습니다.");
    },
  });
}

export function useAIClauseSuggestion(txnId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (issueId: string) => {
      const { data } = await maApi.post(
        `/transactions/${txnId}/negotiation-issues/${issueId}/ai-suggest`,
      );
      return data as AIClauseSuggestionResponse;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: KEY(txnId) });
      toast.success("AI 조항 수정 제안이 생성되었습니다.");
    },
    onError: () => {
      toast.error("AI 제안 생성에 실패했습니다.");
    },
  });
}
