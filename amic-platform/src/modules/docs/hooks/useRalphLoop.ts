import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { maApi } from "@/api/maClient";
import { extractApiError } from "@/api/errors";

// ── Types ────────────────────────────────────────────────────────────────────

export interface DimensionScore {
  name: string;
  label: string;
  score: number;
  weight: number;
  feedback: string;
}

export interface GateResult {
  gate_name: string;
  verdict: "PASS" | "COND" | "FAIL";
  weighted_score: number;
  dimensions: DimensionScore[];
  issues: string[];
  suggestions: string[];
  critical_flags: string[];
  cost_usd: number;
  duration_ms: number;
}

export interface RalphProgress {
  current_phase: string;
  current_section: string | null;
  iteration: number;
  total_iterations: number;
  gate_results: GateResult[];
  score_history: Array<{ iteration: number; score: number }>;
}

export interface RalphSession {
  id: string;
  transaction_id: string;
  doc_type: string;
  status: "pending" | "running" | "completed" | "failed";
  total_iterations: number;
  total_cost_usd: number;
  final_score: number | null;
  section_scores: Record<string, number> | null;
  output_path: string | null;
  critical_flags: string[] | null;
  created_at: string;
  updated_at: string;
}

export interface RalphSessionCreate {
  doc_type: string;
  source_dir?: string;
  config?: Record<string, unknown>;
}

// ── Hooks ────────────────────────────────────────────────────────────────────

export function useRalphSessions(txnId: string) {
  return useQuery<RalphSession[]>({
    queryKey: ["ralph", "sessions", txnId],
    queryFn: async () => {
      const { data } = await maApi.get(
        `/ralph/transactions/${txnId}/sessions`
      );
      return data as RalphSession[];
    },
    enabled: !!txnId,
    refetchInterval: (query) => {
      const sessions = query.state.data;
      const hasRunning = sessions?.some((s) => s.status === "running");
      return hasRunning ? 2_000 : false;
    },
  });
}

export function useRalphSession(sessionId: string) {
  return useQuery<RalphSession>({
    queryKey: ["ralph", "session", sessionId],
    queryFn: async () => {
      const { data } = await maApi.get(`/ralph/sessions/${sessionId}`);
      return data as RalphSession;
    },
    enabled: !!sessionId,
    refetchInterval: (query) => {
      return query.state.data?.status === "running" ? 2_000 : false;
    },
  });
}

export function useRalphProgress(sessionId: string) {
  return useQuery<RalphProgress>({
    queryKey: ["ralph", "progress", sessionId],
    queryFn: async () => {
      const { data } = await maApi.get(
        `/ralph/sessions/${sessionId}/progress`
      );
      return data as RalphProgress;
    },
    enabled: !!sessionId,
    refetchInterval: 2_000,
  });
}

export function useCreateRalphSession(txnId: string) {
  const qc = useQueryClient();
  return useMutation<RalphSession, Error, RalphSessionCreate>({
    mutationFn: async (body) => {
      const { data } = await maApi.post(
        `/ralph/transactions/${txnId}/sessions`,
        body
      );
      return data as RalphSession;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["ralph", "sessions", txnId] });
      toast.success("Ralph Loop 세션이 시작되었습니다.");
    },
    onError: (err) => {
      toast.error(
        extractApiError(err, "Ralph Loop 세션 생성에 실패했습니다.")
      );
    },
  });
}

// ── LDD Auto Create Hook ────────────────────────────────────────────────────

export interface LDDReportCreateAuto {
  title: string;
  report_type?: "FULL" | "REDFLAG";
  target_company?: string;
  dd_period?: string;
  law_firm?: string;
  prepared_by?: string;
  source_dir: string;
  max_iterations?: number;
  max_cost_usd?: number;
}

export function useCreateLDDReportAuto(txnId: string) {
  const qc = useQueryClient();
  return useMutation<unknown, Error, LDDReportCreateAuto>({
    mutationFn: async (body) => {
      const { data } = await maApi.post(
        `/transactions/${txnId}/ldd-reports/auto`,
        body
      );
      return data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["ma", "ldd-reports", txnId] });
      toast.success("AI 자동 분석이 시작되었습니다.");
    },
    onError: (err) => {
      toast.error(
        extractApiError(err, "AI 자동 분석 요청에 실패했습니다.")
      );
    },
  });
}
