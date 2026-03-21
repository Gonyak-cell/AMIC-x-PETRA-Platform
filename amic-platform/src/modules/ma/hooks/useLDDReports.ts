/**
 * LDD 보고서 훅 — VDR 기반 생성, 체크리스트 리뷰, Ralph Loop #2 최종 확정.
 */
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { maApi } from "@/api/maClient";

// ── 타입 ─────────────────────────────────────────────────

export interface LDDReport {
  id: string;
  transaction_id: string;
  report_type: "FULL" | "REDFLAG";
  title: string;
  status:
    | "DRAFT"
    | "ANALYZING"
    | "REVIEW"
    | "FINALIZING"
    | "GENERATING"
    | "READY"
    | "FAILED";
  target_company: string | null;
  dd_period: string | null;
  law_firm: string | null;
  prepared_by: string | null;
  sections: LDDSection[] | null;
  total_items: number;
  issue_count: number;
  red_count: number;
  amber_count: number;
  green_count: number;
  ok_count: number;
  na_count: number;
  pending_count: number;
  rfi_count: number;
  vdr_source: boolean;
  draft_score: number | null;
  final_score: number | null;
  analysis_started_at: string | null;
  analysis_completed_at: string | null;
  review_started_at: string | null;
  review_completed_at: string | null;
  finalize_started_at: string | null;
  finalize_completed_at: string | null;
  template_version: string | null;
  file_name: string | null;
  file_size_bytes: number | null;
  error_message: string | null;
  created_by_email: string | null;
  created_at: string;
  updated_at: string;
}

export interface LDDSection {
  section_type: string;
  title: string;
  items: LDDItem[];
}

export interface LDDItem {
  item_id: string;
  name: string;
  status: "PENDING" | "OK" | "ISSUE" | "NA";
  issue_level: "CRITICAL" | "HIGH" | "MEDIUM" | "LOW" | null;
  risk_color: string;
  description: string;
  deal_impact: string;
  recommendation: string;
  rfi_required: boolean;
  rfi_number: string;
  confidence: number;
  evidence_refs: string[];
  user_comment: string;
  user_approved: boolean | null;
  user_override_status: string | null;
  user_override_level: string | null;
}

export interface ReviewProgress {
  total: number;
  approved: number;
  rejected: number;
  pending: number;
  progress_pct: number;
}

export interface VdrReference {
  id: string;
  ldd_report_id: string;
  item_id: string;
  vdr_document_id: string | null;
  section_type: string;
  relevance_score: number;
  evidence_snippet: string | null;
  page_reference: string | null;
  is_user_confirmed: boolean;
  created_at: string;
  updated_at: string;
}

// ── 요청 타입 ────────────────────────────────────────────

interface CreateFromVdrBody {
  title: string;
  report_type?: "FULL" | "REDFLAG";
  target_company?: string;
  dd_period?: string;
  law_firm?: string;
  prepared_by?: string;
  folder_ids?: string[];
  draft_max_iterations?: number;
  final_max_iterations?: number;
  max_cost_usd?: number;
}

interface ItemReviewBody {
  item_id: string;
  user_approved: boolean;
  user_comment?: string;
  user_override_status?: string | null;
  user_override_level?: string | null;
}

interface FinalizeBody {
  max_iterations?: number;
  max_cost_usd?: number;
}

interface AddReferenceBody {
  item_id: string;
  vdr_document_id: string;
  evidence_snippet?: string;
  page_reference?: string;
}

// ── LDD 보고서 CRUD ──────────────────────────────────────

export function useLDDReports(txnId: string) {
  return useQuery<LDDReport[]>({
    queryKey: ["ma", "ldd-reports", txnId],
    queryFn: async () => {
      const { data } = await maApi.get(`/transactions/${txnId}/ldd-reports`);
      return data;
    },
    enabled: !!txnId,
  });
}

export function useLDDReport(txnId: string, reportId: string) {
  return useQuery<LDDReport>({
    queryKey: ["ma", "ldd-reports", txnId, reportId],
    queryFn: async () => {
      const { data } = await maApi.get(
        `/transactions/${txnId}/ldd-reports/${reportId}`,
      );
      return data;
    },
    enabled: !!txnId && !!reportId,
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      // ANALYZING/FINALIZING/GENERATING 중이면 5초마다 폴링
      if (
        status === "ANALYZING" ||
        status === "FINALIZING" ||
        status === "GENERATING"
      ) {
        return 5000;
      }
      return false;
    },
  });
}

// ── VDR 기반 생성 (Ralph Loop #1) ────────────────────────

export function useCreateLDDFromVdr(txnId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: CreateFromVdrBody) => {
      const { data } = await maApi.post(
        `/transactions/${txnId}/ldd-reports/from-vdr`,
        body,
      );
      return data as LDDReport;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["ma", "ldd-reports", txnId] });
      toast.success("VDR 기반 LDD 분석이 시작되었습니다.");
    },
    onError: () => {
      toast.error("LDD 분석 시작에 실패했습니다.");
    },
  });
}

// ── 체크리스트 리뷰 ──────────────────────────────────────

export function useReviewProgress(txnId: string, reportId: string) {
  return useQuery<ReviewProgress>({
    queryKey: ["ma", "ldd-reports", txnId, reportId, "review-progress"],
    queryFn: async () => {
      const { data } = await maApi.get(
        `/transactions/${txnId}/ldd-reports/${reportId}/review-progress`,
      );
      return data;
    },
    enabled: !!txnId && !!reportId,
  });
}

export function useReviewLDDItem(txnId: string, reportId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: ItemReviewBody) => {
      const { data } = await maApi.put(
        `/transactions/${txnId}/ldd-reports/${reportId}/items/${body.item_id}/review`,
        body,
      );
      return data;
    },
    onSuccess: () => {
      qc.invalidateQueries({
        queryKey: ["ma", "ldd-reports", txnId],
      });
      qc.invalidateQueries({
        queryKey: ["ma", "ldd-reports", txnId, reportId],
      });
      qc.invalidateQueries({
        queryKey: ["ma", "ldd-reports", txnId, reportId, "review-progress"],
      });
    },
    onError: () => {
      toast.error("항목 리뷰 저장에 실패했습니다.");
    },
  });
}

export function useBulkReviewLDD(txnId: string, reportId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (items: ItemReviewBody[]) => {
      const { data } = await maApi.put(
        `/transactions/${txnId}/ldd-reports/${reportId}/items/bulk-review`,
        { items },
      );
      return data;
    },
    onSuccess: (data) => {
      qc.invalidateQueries({
        queryKey: ["ma", "ldd-reports", txnId],
      });
      qc.invalidateQueries({
        queryKey: ["ma", "ldd-reports", txnId, reportId],
      });
      qc.invalidateQueries({
        queryKey: ["ma", "ldd-reports", txnId, reportId, "review-progress"],
      });
      qc.invalidateQueries({ queryKey: ["docs", "ldd-reports"] });
      toast.success(`${data.applied}개 항목 리뷰가 저장되었습니다.`);
    },
    onError: () => {
      toast.error("일괄 리뷰 저장에 실패했습니다.");
    },
  });
}

// ── 최종 확정 (Ralph Loop #2) ────────────────────────────

export function useFinalizeLDD(txnId: string, reportId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: FinalizeBody = {}) => {
      const { data } = await maApi.post(
        `/transactions/${txnId}/ldd-reports/${reportId}/finalize`,
        body,
      );
      return data as LDDReport;
    },
    onSuccess: (report: LDDReport) => {
      qc.invalidateQueries({
        queryKey: ["ma", "ldd-reports", txnId, reportId],
      });
      // 리스트 쿼리도 무효화하여 상태 동기화
      qc.invalidateQueries({
        queryKey: ["ma", "ldd-reports", txnId],
        exact: true,
      });
      qc.invalidateQueries({ queryKey: ["docs", "ldd-reports"] });
      if (report.status === "REVIEW") {
        toast.error(
          report.error_message ?? "QA 게이트 미통과로 리뷰가 필요합니다.",
        );
      } else if (report.status === "FAILED") {
        toast.error(report.error_message ?? "최종 보고서 생성에 실패했습니다.");
      } else {
        toast.success("최종 보고서 생성이 완료되었습니다.");
      }
    },
    onError: () => {
      toast.error("최종 보고서 생성에 실패했습니다.");
    },
  });
}

// ── VDR 참조 ─────────────────────────────────────────────

export function useLDDReferences(txnId: string, reportId: string) {
  return useQuery<VdrReference[]>({
    queryKey: ["ma", "ldd-reports", txnId, reportId, "references"],
    queryFn: async () => {
      const { data } = await maApi.get(
        `/transactions/${txnId}/ldd-reports/${reportId}/references`,
      );
      return data;
    },
    enabled: !!txnId && !!reportId,
  });
}

export function useAddLDDReference(txnId: string, reportId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: AddReferenceBody) => {
      const { data } = await maApi.post(
        `/transactions/${txnId}/ldd-reports/${reportId}/references`,
        body,
      );
      return data as VdrReference;
    },
    onSuccess: () => {
      qc.invalidateQueries({
        queryKey: ["ma", "ldd-reports", txnId, reportId, "references"],
      });
      toast.success("VDR 참조가 추가되었습니다.");
    },
    onError: () => {
      toast.error("VDR 참조 추가에 실패했습니다.");
    },
  });
}

export function useRemoveLDDReference(txnId: string, reportId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (refId: string) => {
      await maApi.delete(
        `/transactions/${txnId}/ldd-reports/${reportId}/references/${refId}`,
      );
    },
    onSuccess: () => {
      qc.invalidateQueries({
        queryKey: ["ma", "ldd-reports", txnId, reportId, "references"],
      });
      toast.success("VDR 참조가 삭제되었습니다.");
    },
    onError: () => {
      toast.error("VDR 참조 삭제에 실패했습니다.");
    },
  });
}
