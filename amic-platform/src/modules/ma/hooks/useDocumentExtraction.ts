import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import axios from "axios";
import { toast } from "sonner";
import { maApi } from "@/api/maClient";
import { IN_PROGRESS_STATUSES } from "@/modules/ma/types/document_extraction";
import type {
  DocumentExtraction,
  ExtractionListResponse,
  ExtractionConfirmRequest,
} from "@/modules/ma/types/document_extraction";

// ── Query Keys ─────────────────────────────────────────────

const extractionQK = (txnId: string) =>
  ["ma", "transactions", txnId, "extractions"] as const;

const extractionDetailQK = (txnId: string, id: string) =>
  ["ma", "transactions", txnId, "extractions", id] as const;

// ── Read 훅 ────────────────────────────────────────────────

/** 추출 작업 목록 — 진행중 상태가 있으면 3초 폴링 */
export function useExtractions(txnId: string) {
  return useQuery<ExtractionListResponse>({
    queryKey: extractionQK(txnId),
    queryFn: async () => {
      const { data } = await maApi.get(`/transactions/${txnId}/extractions`);
      return data;
    },
    enabled: !!txnId,
    refetchInterval: (query) => {
      const items = query.state.data?.items ?? [];
      const hasInProgress = items.some((e) =>
        IN_PROGRESS_STATUSES.includes(e.status),
      );
      return hasInProgress ? 3000 : false;
    },
  });
}

/** 단일 추출 상세 — 진행중이면 2초 폴링 */
export function useExtraction(txnId: string, id: string) {
  return useQuery<DocumentExtraction>({
    queryKey: extractionDetailQK(txnId, id),
    queryFn: async () => {
      const { data } = await maApi.get(
        `/transactions/${txnId}/extractions/${id}`,
      );
      return data;
    },
    enabled: !!txnId && !!id,
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      if (!status) return false;
      return IN_PROGRESS_STATUSES.includes(status) ? 2000 : false;
    },
  });
}

// ── Write 훅 ───────────────────────────────────────────────

/** 단일 문서 AI 추출 생성 */
export function useCreateExtraction(txnId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (params: {
      vdrDocumentId: string;
      docCategoryHint?: string;
    }) => {
      const { data } = await maApi.post(`/transactions/${txnId}/extractions`, {
        vdr_document_id: params.vdrDocumentId,
        doc_category_hint: params.docCategoryHint ?? null,
      });
      return data as DocumentExtraction;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: extractionQK(txnId) });
      toast.success("AI 분석을 시작했습니다.");
    },
    onError: (error) => {
      const detail =
        axios.isAxiosError(error) &&
        typeof error.response?.data?.detail === "string"
          ? error.response.data.detail
          : "AI 분석 생성에 실패했습니다.";
      toast.error(detail);
    },
  });
}

/** 일괄 추출 (최대 10건) */
export function useBatchExtract(txnId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (vdrDocumentIds: string[]) => {
      const { data } = await maApi.post(
        `/transactions/${txnId}/extractions/batch`,
        { vdr_document_ids: vdrDocumentIds },
      );
      return data as DocumentExtraction[];
    },
    onSuccess: (data) => {
      qc.invalidateQueries({ queryKey: extractionQK(txnId) });
      toast.success(`${data.length}건의 AI 분석을 시작했습니다.`);
    },
    onError: (error) => {
      const detail =
        axios.isAxiosError(error) &&
        typeof error.response?.data?.detail === "string"
          ? error.response.data.detail
          : "일괄 AI 분석 생성에 실패했습니다.";
      toast.error(detail);
    },
  });
}

/** FAILED 추출 재시도 */
export function useRetryExtraction(txnId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (extractionId: string) => {
      const { data } = await maApi.post(
        `/transactions/${txnId}/extractions/${extractionId}/retry`,
      );
      return data as DocumentExtraction;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: extractionQK(txnId) });
      toast.success("AI 분석을 재시도합니다.");
    },
    onError: (error) => {
      const detail =
        axios.isAxiosError(error) &&
        typeof error.response?.data?.detail === "string"
          ? error.response.data.detail
          : "재시도에 실패했습니다.";
      toast.error(detail);
    },
  });
}

/** 추출 결과 확정 (검토 후 DB 매핑) */
export function useConfirmExtraction(txnId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({
      extractionId,
      body,
    }: {
      extractionId: string;
      body: ExtractionConfirmRequest;
    }) => {
      const { data } = await maApi.put(
        `/transactions/${txnId}/extractions/${extractionId}/confirm`,
        body,
      );
      return data as DocumentExtraction;
    },
    onSuccess: (data) => {
      qc.invalidateQueries({ queryKey: extractionQK(txnId) });
      qc.invalidateQueries({
        queryKey: extractionDetailQK(txnId, data.id),
      });
      // 매핑 대상 쿼리도 무효화
      if (data.target_model) {
        // 백엔드 Literal["nda","bid","contract","transaction"] 기준
        const MODEL_TO_QK: Record<string, string> = {
          transaction: "",
          bid: "bids",
          contract: "contracts",
          nda: "ndas",
        };
        const qk = MODEL_TO_QK[data.target_model];
        if (qk === "") {
          qc.invalidateQueries({
            queryKey: ["ma", "transactions", txnId],
          });
        } else if (qk) {
          qc.invalidateQueries({
            queryKey: ["ma", "transactions", txnId, qk],
          });
        }
      }
      toast.success("추출 결과가 확정되었습니다.");
    },
    onError: (error) => {
      const detail =
        axios.isAxiosError(error) &&
        typeof error.response?.data?.detail === "string"
          ? error.response.data.detail
          : "추출 확정에 실패했습니다.";
      toast.error(detail);
    },
  });
}
