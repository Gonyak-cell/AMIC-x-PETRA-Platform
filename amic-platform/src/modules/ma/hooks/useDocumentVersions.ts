import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { maApi } from "@/api/maClient";
import type {
  DocumentMaster,
  DocumentMasterCreatePayload,
  DocumentMasterListResponse,
  DocumentRevision,
  RevisionListResponse,
} from "@/modules/ma/types/document_version";

// ── Query Keys ─────────────────────────────────────────

const DOCS_KEY = (txnId: string) =>
  ["ma", "transactions", txnId, "documents"] as const;

const REVISIONS_KEY = (txnId: string, docId: string) =>
  ["ma", "transactions", txnId, "documents", docId, "revisions"] as const;

// ── DocumentMaster 훅 ──────────────────────────────────

export function useDocuments(txnId: string, docType?: string) {
  return useQuery<DocumentMasterListResponse>({
    queryKey: [...DOCS_KEY(txnId), { docType }],
    queryFn: async () => {
      const params = new URLSearchParams();
      if (docType) params.set("doc_type", docType);
      const { data } = await maApi.get(
        `/transactions/${txnId}/documents?${params.toString()}`,
      );
      return data;
    },
    enabled: !!txnId,
  });
}

export function useCreateDocument(txnId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: DocumentMasterCreatePayload) => {
      const { data } = await maApi.post(
        `/transactions/${txnId}/documents`,
        payload,
      );
      return data as DocumentMaster;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: DOCS_KEY(txnId) });
      toast.success("문서 원장이 생성되었습니다.");
    },
    onError: (error: unknown) => {
      const msg =
        error instanceof Error
          ? error.message
          : "문서 원장 생성에 실패했습니다.";
      toast.error(msg);
    },
  });
}

// ── DocumentRevision 훅 ────────────────────────────────

export function useDocumentRevisions(txnId: string, docId: string) {
  return useQuery<RevisionListResponse>({
    queryKey: REVISIONS_KEY(txnId, docId),
    queryFn: async () => {
      const { data } = await maApi.get(
        `/transactions/${txnId}/documents/${docId}/revisions`,
      );
      return data;
    },
    enabled: !!txnId && !!docId,
  });
}

export function useUploadRevision(txnId: string, docId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (formData: FormData) => {
      const { data } = await maApi.post(
        `/transactions/${txnId}/documents/${docId}/revisions`,
        formData,
        { headers: { "Content-Type": "multipart/form-data" } },
      );
      return data as DocumentRevision;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: REVISIONS_KEY(txnId, docId) });
      qc.invalidateQueries({ queryKey: DOCS_KEY(txnId) });
      toast.success("새 리비전이 업로드되었습니다.");
    },
    onError: (error: unknown) => {
      const msg =
        error instanceof Error
          ? error.message
          : "리비전 업로드에 실패했습니다.";
      toast.error(msg);
    },
  });
}

export function useDeleteRevision(txnId: string, docId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (revId: string) => {
      await maApi.delete(
        `/transactions/${txnId}/documents/${docId}/revisions/${revId}`,
      );
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: REVISIONS_KEY(txnId, docId) });
      qc.invalidateQueries({ queryKey: DOCS_KEY(txnId) });
      toast.success("리비전이 삭제되었습니다.");
    },
    onError: (error: unknown) => {
      const msg =
        error instanceof Error
          ? error.message
          : "리비전 삭제에 실패했습니다.";
      toast.error(msg);
    },
  });
}

// ── 유틸 ───────────────────────────────────────────────

export function getRevisionDownloadUrl(
  txnId: string,
  docId: string,
  revId: string,
): string {
  return `/api/v1/transactions/${txnId}/documents/${docId}/revisions/${revId}/download`;
}
