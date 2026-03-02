import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { maApi } from "@/api/maClient";
import { extractApiError } from "@/api/errors";
import type {
  LegalDocument,
  LegalDocumentCreate,
} from "@/modules/docs/types/legal_document";

const BASE = (txnId: string) => `/transactions/${txnId}/legal-documents`;

// ── 조회 ──────────────────────────────────────────────────────────────────────

export function useLegalDocuments(txnId: string, active = true) {
  return useQuery<LegalDocument[]>({
    queryKey: ["ma", "legal-documents", txnId],
    queryFn: async () => {
      const { data } = await maApi.get(BASE(txnId));
      return data as LegalDocument[];
    },
    enabled: !!txnId && active,
    // GENERATING 상태 문서가 있을 때 3초마다 자동 재조회한다
    refetchInterval: (query) => {
      const docs = query.state.data;
      const hasGenerating = docs?.some((d) => d.status === "GENERATING");
      return hasGenerating ? 3_000 : false;
    },
  });
}

export function useLegalDocument(txnId: string, docId: string) {
  return useQuery<LegalDocument>({
    queryKey: ["ma", "legal-documents", txnId, docId],
    queryFn: async () => {
      const { data } = await maApi.get(`${BASE(txnId)}/${docId}`);
      return data as LegalDocument;
    },
    enabled: !!txnId && !!docId,
  });
}

// ── 생성 ──────────────────────────────────────────────────────────────────────

export function useCreateLegalDocument(txnId: string) {
  const qc = useQueryClient();
  return useMutation<LegalDocument, Error, LegalDocumentCreate>({
    mutationFn: async (body) => {
      const { data } = await maApi.post(BASE(txnId), body);
      return data as LegalDocument;
    },
    onSuccess: (doc) => {
      qc.invalidateQueries({ queryKey: ["ma", "legal-documents", txnId] });
      if (doc.status === "READY") {
        toast.success("법률 문서가 생성되었습니다.");
      } else if (doc.status === "FAILED") {
        toast.error(
          `문서 생성에 실패했습니다: ${doc.error_message ?? "알 수 없는 오류"}`,
        );
      }
    },
    onError: (err) => {
      toast.error(extractApiError(err, "문서 생성 요청에 실패했습니다."));
    },
  });
}

// ── 재생성 ────────────────────────────────────────────────────────────────────

export function useRegenerateLegalDocument(txnId: string) {
  const qc = useQueryClient();
  return useMutation<
    LegalDocument,
    Error,
    { docId: string; body: LegalDocumentCreate }
  >({
    mutationFn: async ({ docId, body }) => {
      const { data } = await maApi.post(
        `${BASE(txnId)}/${docId}/regenerate`,
        body,
      );
      return data as LegalDocument;
    },
    onSuccess: (doc) => {
      qc.invalidateQueries({ queryKey: ["ma", "legal-documents", txnId] });
      qc.invalidateQueries({
        queryKey: ["ma", "legal-documents", txnId, doc.id],
      });
      if (doc.status === "READY") {
        toast.success("문서가 재생성되었습니다.");
      } else if (doc.status === "FAILED") {
        toast.error(`재생성 실패: ${doc.error_message ?? "알 수 없는 오류"}`);
      }
    },
    onError: (err) => {
      toast.error(extractApiError(err, "문서 재생성 요청에 실패했습니다."));
    },
  });
}

// ── 삭제 ──────────────────────────────────────────────────────────────────────

export function useDeleteLegalDocument(txnId: string) {
  const qc = useQueryClient();
  return useMutation<void, Error, string>({
    mutationFn: async (docId) => {
      await maApi.delete(`${BASE(txnId)}/${docId}`);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["ma", "legal-documents", txnId] });
      toast.success("문서가 삭제되었습니다.");
    },
    onError: (err) => {
      toast.error(extractApiError(err, "문서 삭제에 실패했습니다."));
    },
  });
}

// ── 다운로드 URL ───────────────────────────────────────────────────────────────

export function getLegalDocDownloadUrl(txnId: string, docId: string): string {
  return `/api/ma/transactions/${txnId}/legal-documents/${docId}/download`;
}

// ── 파일 크기 포맷 ────────────────────────────────────────────────────────────

export function formatFileSize(bytes: number | null): string {
  if (!bytes) return "";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}
