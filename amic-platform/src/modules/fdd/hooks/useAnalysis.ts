import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import api from "@/api/client";

export type AnalysisRunStatus = "PENDING" | "RUNNING" | "COMPLETED" | "FAILED";

export interface AnalysisRun {
  id: string;
  deal_id: string;
  trigger: string;
  status: AnalysisRunStatus;
  input_file_ids: string[] | null;
  output_checklist_id: string | null;
  progress_percent: number;
  error_message: string | null;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
  cross_verify_summary: Record<string, unknown> | null;
  qa_result: Record<string, unknown> | null;
}

export function useAnalysisRuns(dealId: string) {
  return useQuery({
    queryKey: ["fdd", "analysis", dealId],
    queryFn: async () => {
      const { data } = await api.get<AnalysisRun[]>(
        `/deals/${dealId}/analysis/runs`
      );
      return data;
    },
  });
}

export function useRunAnalysis(dealId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (opts?: {
      fileIds?: string[];
      cross_verify_enabled?: boolean;
    }) => {
      const { data } = await api.post<AnalysisRun>(
        `/deals/${dealId}/analysis/run`,
        {
          file_ids: opts?.fileIds ?? null,
          cross_verify_enabled: opts?.cross_verify_enabled ?? false,
        }
      );
      return data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["fdd", "analysis", dealId] });
      qc.invalidateQueries({ queryKey: ["fdd", "checklist", dealId] });
    },
  });
}
