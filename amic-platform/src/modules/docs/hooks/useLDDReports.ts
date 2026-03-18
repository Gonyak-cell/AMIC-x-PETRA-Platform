import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { maApi } from "@/api/maClient";
import { extractApiError } from "@/api/errors";
import type {
  LDDReport,
  LDDReportCreate,
  LDDSection,
  LDDSectionsUpdate,
} from "@/modules/docs/types/ldd_report";

const BASE = (txnId: string) => `/transactions/${txnId}/ldd-reports`;

// ── 조회 ──────────────────────────────────────────────────────────────────────

export function useLDDReports(txnId: string) {
  return useQuery<LDDReport[]>({
    queryKey: ["ma", "ldd-reports", txnId],
    queryFn: async () => {
      const { data } = await maApi.get(BASE(txnId));
      return data as LDDReport[];
    },
    enabled: !!txnId,
    // ANALYZING/FINALIZING/GENERATING 상태 보고서가 있을 때 자동 재조회
    refetchInterval: (query) => {
      const reports = query.state.data;
      const hasAsync = reports?.some(
        (r) => r.status === "ANALYZING" || r.status === "FINALIZING" || r.status === "GENERATING"
      );
      return hasAsync ? 5_000 : false;
    },
  });
}

export function useLDDReport(txnId: string, reportId: string) {
  return useQuery<LDDReport>({
    queryKey: ["ma", "ldd-reports", txnId, reportId],
    queryFn: async () => {
      const { data } = await maApi.get(`${BASE(txnId)}/${reportId}`);
      return data as LDDReport;
    },
    enabled: !!txnId && !!reportId,
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      if (status === "ANALYZING" || status === "FINALIZING" || status === "GENERATING") {
        return 5_000;
      }
      return false;
    },
  });
}

// ── 기본 섹션 구조 조회 ───────────────────────────────────────────────────────

export function useDefaultLDDSections() {
  return useQuery<LDDSection[]>({
    queryKey: ["ldd-default-sections"],
    queryFn: async () => {
      const { data } = await maApi.get("/ldd-reports/default-sections");
      return (data as { sections: LDDSection[] }).sections;
    },
    staleTime: Infinity, // 기본 섹션은 서버 재시작 전까지 변하지 않음
  });
}

// ── 생성 ──────────────────────────────────────────────────────────────────────

export function useCreateLDDReport(txnId: string) {
  const qc = useQueryClient();
  return useMutation<LDDReport, Error, LDDReportCreate>({
    mutationFn: async (body) => {
      const { data } = await maApi.post(BASE(txnId), body);
      return data as LDDReport;
    },
    onSuccess: (report) => {
      qc.invalidateQueries({ queryKey: ["ma", "ldd-reports", txnId] });
      if (report.status === "REVIEW") {
        toast.success("LDD 초안이 생성되었습니다. 리뷰를 진행해주세요.");
      } else if (report.status === "READY") {
        toast.success("LDD 보고서가 생성되었습니다.");
      } else if (report.status === "FAILED") {
        toast.error(`보고서 생성에 실패했습니다: ${report.error_message ?? "알 수 없는 오류"}`);
      }
    },
    onError: (err) => {
      toast.error(extractApiError(err, "LDD 보고서 생성 요청에 실패했습니다."));
    },
  });
}

// ── AI 자동 생성 (Ralph Loop) ────────────────────────────────────────────────

interface LDDReportCreateAuto {
  title: string;
  report_type: string;
  source_dir: string;
  target_company?: string;
  dd_period?: string;
  law_firm?: string;
  prepared_by?: string;
  max_iterations?: number;
  max_cost_usd?: number;
}

export function useCreateLDDReportAuto(txnId: string) {
  const qc = useQueryClient();
  return useMutation<LDDReport, Error, LDDReportCreateAuto>({
    mutationFn: async (body) => {
      const { data } = await maApi.post(`${BASE(txnId)}/auto`, body);
      return data as LDDReport;
    },
    onSuccess: (report) => {
      qc.invalidateQueries({ queryKey: ["ma", "ldd-reports", txnId] });
      if (report.status === "READY") {
        toast.success("AI 자동 분석으로 LDD 보고서가 생성되었습니다.");
      } else if (report.status === "FAILED") {
        toast.error(`AI 분석 실패: ${report.error_message ?? "알 수 없는 오류"}`);
      }
    },
    onError: (err) => {
      toast.error(extractApiError(err, "AI 자동 분석 요청에 실패했습니다."));
    },
  });
}

// ── 섹션 수정 ─────────────────────────────────────────────────────────────────

export function useUpdateLDDSections(txnId: string) {
  const qc = useQueryClient();
  return useMutation<LDDReport, Error, { reportId: string; sections: LDDSection[] }>({
    mutationFn: async ({ reportId, sections }) => {
      const body: LDDSectionsUpdate = { sections };
      const { data } = await maApi.put(`${BASE(txnId)}/${reportId}/sections`, body);
      return data as LDDReport;
    },
    onSuccess: (report) => {
      qc.invalidateQueries({ queryKey: ["ma", "ldd-reports", txnId] });
      qc.invalidateQueries({ queryKey: ["ma", "ldd-reports", txnId, report.id] });
      if (report.status === "READY") {
        toast.success("체크리스트가 저장되고 보고서가 재생성되었습니다.");
      } else if (report.status === "FAILED") {
        toast.error(`보고서 재생성에 실패했습니다: ${report.error_message ?? "알 수 없는 오류"}`);
      }
    },
    onError: (err) => {
      toast.error(extractApiError(err, "체크리스트 저장에 실패했습니다."));
    },
  });
}

// ── 재생성 ────────────────────────────────────────────────────────────────────

export function useRegenerateLDDReport(txnId: string) {
  const qc = useQueryClient();
  return useMutation<LDDReport, Error, string>({
    mutationFn: async (reportId) => {
      const { data } = await maApi.post(`${BASE(txnId)}/${reportId}/regenerate`);
      return data as LDDReport;
    },
    onSuccess: (report) => {
      qc.invalidateQueries({ queryKey: ["ma", "ldd-reports", txnId] });
      qc.invalidateQueries({ queryKey: ["ma", "ldd-reports", txnId, report.id] });
      if (report.status === "READY") {
        toast.success("보고서가 재생성되었습니다.");
      } else if (report.status === "FAILED") {
        toast.error(`재생성 실패: ${report.error_message ?? "알 수 없는 오류"}`);
      }
    },
    onError: (err) => {
      toast.error(extractApiError(err, "보고서 재생성에 실패했습니다."));
    },
  });
}

// ── 삭제 ──────────────────────────────────────────────────────────────────────

export function useDeleteLDDReport(txnId: string) {
  const qc = useQueryClient();
  return useMutation<void, Error, string>({
    mutationFn: async (reportId) => {
      await maApi.delete(`${BASE(txnId)}/${reportId}`);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["ma", "ldd-reports", txnId] });
      toast.success("LDD 보고서가 삭제되었습니다.");
    },
    onError: (err) => {
      toast.error(extractApiError(err, "보고서 삭제에 실패했습니다."));
    },
  });
}

// ── 전체 LDD 보고서 목록 (거래 횡단 조회) ────────────────────────────────────────

export function useLDDReportsList() {
  return useQuery<LDDReport[]>({
    queryKey: ["ma", "ldd-reports", "all"],
    queryFn: async () => {
      const { data } = await maApi.get("/ldd-reports");
      return data as LDDReport[];
    },
  });
}

// ── 다운로드 URL ───────────────────────────────────────────────────────────────

export function getLDDReportDownloadUrl(txnId: string, reportId: string): string {
  return `/api/ma/transactions/${txnId}/ldd-reports/${reportId}/download`;
}

// ── 파일 크기 포맷 ────────────────────────────────────────────────────────────

export function formatFileSize(bytes: number | null): string {
  if (!bytes) return "";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}
