import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import api from "@/api/client";
import type {
  IssueRead,
  IssueListResponse,
  IssueSummary,
  AnomalyDetectionRequest,
  AnomalyDetectionResponse,
} from "@/modules/fdd/types/issue";

export function useIssues(
  dealId: string,
  filters?: {
    severity?: string;
    status?: string;
    category?: string;
    limit?: number;
    offset?: number;
  }
) {
  return useQuery<IssueListResponse>({
    queryKey: ["fdd", "issues", dealId, filters],
    queryFn: async () => {
      const { data } = await api.get(`/deals/${dealId}/issues`, {
        params: filters,
      });
      return data;
    },
    enabled: !!dealId,
  });
}

export function useIssueSummary(dealId: string) {
  return useQuery<IssueSummary>({
    queryKey: ["fdd", "issues", dealId, "summary"],
    queryFn: async () => {
      const { data } = await api.get(`/deals/${dealId}/issues/summary`);
      return data;
    },
    enabled: !!dealId,
  });
}

export function useRunAnomalyDetection(dealId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (body?: AnomalyDetectionRequest) => {
      const { data } = await api.post(
        `/deals/${dealId}/issues/detect-anomalies`,
        body ?? {}
      );
      return data as AnomalyDetectionResponse;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["fdd", "issues", dealId] });
    },
    onError: (error: Error) => {
      console.error("useRunAnomalyDetection failed:", error);
    },
  });
}

export function useResolveIssue(dealId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({
      issueId,
      resolution_note,
      resolved_by,
    }: {
      issueId: string;
      resolution_note?: string;
      resolved_by?: string;
    }) => {
      const { data } = await api.put(
        `/deals/${dealId}/issues/${issueId}`,
        { status: "RESOLVED", resolution_note, resolved_by }
      );
      return data as IssueRead;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["fdd", "issues", dealId] });
    },
    onError: (error: Error) => {
      console.error("useResolveIssue failed:", error);
    },
  });
}

export function useDismissIssue(dealId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({
      issueId,
      resolution_note,
      resolved_by,
    }: {
      issueId: string;
      resolution_note?: string;
      resolved_by?: string;
    }) => {
      const { data } = await api.put(
        `/deals/${dealId}/issues/${issueId}`,
        { status: "FALSE_POSITIVE", resolution_note, resolved_by }
      );
      return data as IssueRead;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["fdd", "issues", dealId] });
    },
    onError: (error: Error) => {
      console.error("useDismissIssue failed:", error);
    },
  });
}
