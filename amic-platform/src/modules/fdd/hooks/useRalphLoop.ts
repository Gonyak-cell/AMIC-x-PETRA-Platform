import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import api from "@/api/client";

export interface RalphConfig {
  max_iterations_per_section: number;
  max_cost_usd: number;
  pass_threshold: number;
}

export interface RalphSession {
  id: string;
  deal_id: string;
  pass_type: "draft" | "final";
  status: string;
  checklist_id: string | null;
  report_version_id: string | null;
  total_iterations: number;
  total_cost_usd: number;
  final_score: number;
  section_scores: Record<string, number> | null;
  critical_flags: string[] | null;
  error_message: string | null;
  created_by: string | null;
  created_at: string | null;
  updated_at: string | null;
}

export interface RalphProgress {
  session_id: string;
  status: string;
  total_iterations: number;
  total_cost_usd: number;
  final_score: number;
  section_scores: Record<string, number> | null;
  progress: Record<string, unknown> | null;
  critical_flags: string[] | null;
}

export function useFddRalphSessions(dealId: string) {
  return useQuery<RalphSession[]>({
    queryKey: ["fdd", "ralph-sessions", dealId],
    queryFn: async () => {
      const { data } = await api.get(`/deals/${dealId}/ralph/sessions`);
      return data as RalphSession[];
    },
    enabled: !!dealId,
  });
}

export function useFddRalphProgress(dealId: string, sessionId: string | null) {
  return useQuery<RalphProgress>({
    queryKey: ["fdd", "ralph-progress", dealId, sessionId],
    queryFn: async () => {
      const { data } = await api.get(
        `/deals/${dealId}/ralph/sessions/${sessionId}/progress`
      );
      return data as RalphProgress;
    },
    enabled: !!dealId && !!sessionId,
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      if (status === "COMPLETED" || status === "FAILED") return false;
      return 3000;
    },
  });
}

export function useCreateFddRalphSession(dealId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (body: {
      pass_type: "draft" | "final";
      checklist_id?: string;
      config?: Partial<RalphConfig>;
    }) => {
      const { data } = await api.post(`/deals/${dealId}/ralph/sessions`, body);
      return data as RalphSession;
    },
    onSuccess: (session) => {
      queryClient.invalidateQueries({
        queryKey: ["fdd", "ralph-sessions", dealId],
      });
      if (session.status === "COMPLETED") {
        toast.success(
          `Ralph Loop ${session.pass_type === "draft" ? "Draft" : "Final"} pass completed — Score: ${session.final_score.toFixed(1)}/5.0`
        );
      }
    },
    onError: () => {
      toast.error("Ralph Loop session failed");
    },
  });
}
