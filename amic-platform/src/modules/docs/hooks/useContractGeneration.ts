/** 계약서 자동 생성 API 훅 */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type { AxiosError } from "axios";
import { toast } from "sonner";
import { maApi } from "@/api/maClient";
import { extractApiError } from "@/api/errors";
import type {
  ContractTemplate,
  ContractTemplateDetail,
  ContractGenerateRequest,
  ContractGenerationResult,
  ContractSaveHtmlResponse,
} from "@/modules/docs/types/contract_generation";

/** Axios 에러에서 HTTP 상태 코드를 추출한다. */
function getStatusCode(err: unknown): number | undefined {
  return (err as AxiosError)?.response?.status;
}

const BASE = (txnId: string) => `/transactions/${txnId}/contract-generation`;

// ── 템플릿 목록 조회 ─────────────────────────────────────────────────────

export function useContractTemplates(txnId: string) {
  return useQuery<ContractTemplate[]>({
    queryKey: ["ma", "contract-templates", txnId],
    queryFn: async () => {
      const { data } = await maApi.get(`${BASE(txnId)}/templates`);
      return data as ContractTemplate[];
    },
    enabled: !!txnId,
    staleTime: 5 * 60 * 1000,
  });
}

// ── 템플릿 상세 조회 ─────────────────────────────────────────────────────

export function useContractTemplateDetail(txnId: string, templateId: string) {
  return useQuery<ContractTemplateDetail>({
    queryKey: ["ma", "contract-templates", txnId, templateId],
    queryFn: async () => {
      const { data } = await maApi.get(
        `${BASE(txnId)}/templates/${templateId}`,
      );
      return data as ContractTemplateDetail;
    },
    enabled: !!txnId && !!templateId,
  });
}

// ── 계약서 HTML 생성 ─────────────────────────────────────────────────────

export function useGenerateContract(txnId: string) {
  const qc = useQueryClient();
  return useMutation<ContractGenerationResult, Error, ContractGenerateRequest>({
    mutationFn: async (body) => {
      const { data } = await maApi.post(`${BASE(txnId)}/generate`, body);
      return data as ContractGenerationResult;
    },
    onSuccess: (result) => {
      qc.invalidateQueries({ queryKey: ["ma", "legal-documents", txnId] });
      toast.success(
        `계약서가 생성되었습니다 (${result.clauses_used}개 조항${result.llm_smoothed ? ", LLM 다듬기 완료" : ""})`,
      );
    },
    onError: (err) => {
      const code = getStatusCode(err);
      if (code === 422) {
        toast.error(
          `입력 항목을 확인하세요: ${extractApiError(err, "필수 변수가 누락되었습니다.")}`,
        );
      } else if (code === 429) {
        toast.error("요청이 너무 많습니다. 1분 후 다시 시도하세요.");
      } else {
        toast.error(extractApiError(err, "계약서 생성에 실패했습니다."));
      }
    },
  });
}

// ── DOCX 내보내기 ────────────────────────────────────────────────────────

export function useExportDocx(txnId: string) {
  return useMutation<Blob, Error, { html: string; title: string }>({
    mutationFn: async ({ html, title }) => {
      const { data } = await maApi.post(
        `${BASE(txnId)}/export-docx`,
        { html, title },
        { responseType: "blob" },
      );
      return data as Blob;
    },
    onSuccess: () => {
      toast.success("DOCX 파일이 생성되었습니다.");
    },
    onError: (err) => {
      toast.error(extractApiError(err, "DOCX 변환에 실패했습니다."));
    },
  });
}

// ── HTML 저장 ────────────────────────────────────────────────────────────

export function useSaveContractHtml(txnId: string) {
  return useMutation<
    ContractSaveHtmlResponse,
    Error,
    { docId: string; html: string; lastModifiedAt?: string | null }
  >({
    mutationFn: async ({ docId, html, lastModifiedAt }) => {
      const { data } = await maApi.patch(`${BASE(txnId)}/${docId}/save-html`, {
        html,
        last_modified_at: lastModifiedAt,
      });
      return data as ContractSaveHtmlResponse;
    },
    onSuccess: () => {
      toast.success("초안이 저장되었습니다.");
    },
    onError: (err) => {
      const code = getStatusCode(err);
      if (code === 409) {
        toast.error(
          "문서가 다른 사용자에 의해 수정되었습니다. 페이지를 새로고침한 후 다시 시도하세요.",
          { duration: 8000 },
        );
      } else {
        toast.error(extractApiError(err, "저장에 실패했습니다."));
      }
    },
  });
}

// ── DOCX 다운로드 헬퍼 ──────────────────────────────────────────────────

export function downloadBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}
