import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

import { extractApiError } from "@/api/errors";
import { maApi } from "@/api/maClient";
import type {
  ClassificationStatusItem,
  DirectUploadBatchResult,
  VdrDocument,
  VdrDocumentUpdate,
  VdrFolder,
  VdrFolderCreate,
  VdrFolderUpdate,
  VdrSummary,
} from "@/modules/ma/types/vdr";
import { CLASSIFICATION_POLL_INTERVAL_MS } from "@/modules/ma/types/vdr";

// ── Query Keys ─────────────────────────────────────────

const folderQK = (txnId: string) =>
  ["ma", "transactions", txnId, "vdr", "folders"] as const;
const docQK = (txnId: string, folderId: string) =>
  [
    "ma",
    "transactions",
    txnId,
    "vdr",
    "folders",
    folderId,
    "documents",
  ] as const;
const allDocQK = (txnId: string) =>
  ["ma", "transactions", txnId, "vdr", "all-documents"] as const;
const summaryQK = (txnId: string) =>
  ["ma", "transactions", txnId, "vdr", "summary"] as const;

// ── 요약 ────────────────────────────────────────────────

export function useVdrSummary(txnId: string) {
  return useQuery<VdrSummary>({
    queryKey: summaryQK(txnId),
    queryFn: async () => {
      const { data } = await maApi.get(`/transactions/${txnId}/vdr/summary`);
      return data;
    },
    enabled: !!txnId,
  });
}

// ── 폴더 ────────────────────────────────────────────────

/** 서버의 중첩 트리 응답을 parent_id 참조 기반 평탄 배열로 변환 */
function flattenVdrFolders(tree: VdrFolder[]): VdrFolder[] {
  const result: VdrFolder[] = [];
  function walk(nodes: VdrFolder[]) {
    for (const node of nodes) {
      result.push(node);
      if (node.children.length > 0) walk(node.children);
    }
  }
  walk(tree);
  return result;
}

export function useVdrFolders(txnId: string) {
  return useQuery<VdrFolder[]>({
    queryKey: folderQK(txnId),
    queryFn: async () => {
      const { data } = await maApi.get(`/transactions/${txnId}/vdr/folders`);
      return flattenVdrFolders(data);
    },
    enabled: !!txnId,
  });
}

export function useCreateVdrFolder(txnId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: VdrFolderCreate) => {
      const { data } = await maApi.post(
        `/transactions/${txnId}/vdr/folders`,
        body,
      );
      return data as VdrFolder;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: folderQK(txnId) });
      toast.success("폴더가 생성되었습니다.");
    },
    onError: (err) => {
      toast.error(extractApiError(err, "폴더 생성에 실패했습니다."));
    },
  });
}

export function useUpdateVdrFolder(txnId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({
      folderId,
      body,
    }: {
      folderId: string;
      body: VdrFolderUpdate;
    }) => {
      const { data } = await maApi.put(
        `/transactions/${txnId}/vdr/folders/${folderId}`,
        body,
      );
      return data as VdrFolder;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: folderQK(txnId) });
      toast.success("폴더가 수정되었습니다.");
    },
    onError: (err) => {
      toast.error(extractApiError(err, "폴더 수정에 실패했습니다."));
    },
  });
}

export function useDeleteVdrFolder(txnId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (folderId: string) => {
      await maApi.delete(`/transactions/${txnId}/vdr/folders/${folderId}`);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: folderQK(txnId) });
      qc.invalidateQueries({ queryKey: summaryQK(txnId) });
      toast.success("폴더가 삭제되었습니다.");
    },
    onError: (err) => {
      toast.error(extractApiError(err, "폴더 삭제에 실패했습니다."));
    },
  });
}

// ── 문서 ────────────────────────────────────────────────

export function useVdrDocuments(txnId: string, folderId: string | null) {
  return useQuery<VdrDocument[]>({
    queryKey: docQK(txnId, folderId ?? ""),
    queryFn: async () => {
      const { data } = await maApi.get(
        `/transactions/${txnId}/vdr/folders/${folderId}/documents`,
      );
      return data;
    },
    enabled: !!txnId && !!folderId,
  });
}

export function useUploadVdrDocument(txnId: string, folderId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (file: File) => {
      const formData = new FormData();
      formData.append("file", file);
      const { data } = await maApi.post(
        `/transactions/${txnId}/vdr/folders/${folderId}/documents`,
        formData,
      );
      return data as VdrDocument;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: docQK(txnId, folderId) });
      qc.invalidateQueries({ queryKey: folderQK(txnId) });
      qc.invalidateQueries({ queryKey: summaryQK(txnId) });
      qc.invalidateQueries({ queryKey: allDocQK(txnId) });
      toast.success("파일이 업로드되었습니다.");
    },
    onError: (err) => {
      toast.error(extractApiError(err, "파일 업로드에 실패했습니다."));
    },
  });
}

export function useUpdateVdrDocument(txnId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({
      docId,
      body,
    }: {
      docId: string;
      body: VdrDocumentUpdate;
    }) => {
      const { data } = await maApi.put(
        `/transactions/${txnId}/vdr/documents/${docId}`,
        body,
      );
      return data as VdrDocument;
    },
    onSuccess: () => {
      // folderQK is a prefix of docQK → React Query prefix-matching
      // implicitly invalidates all docQK(txnId, *) queries as well.
      qc.invalidateQueries({ queryKey: folderQK(txnId) });
      qc.invalidateQueries({ queryKey: allDocQK(txnId) });
      toast.success("문서가 수정되었습니다.");
    },
    onError: (err) => {
      toast.error(extractApiError(err, "문서 수정에 실패했습니다."));
    },
  });
}

export function useDeleteVdrDocument(txnId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ docId }: { docId: string; folderId: string }) => {
      await maApi.delete(`/transactions/${txnId}/vdr/documents/${docId}`);
    },
    onSuccess: (_data, { folderId }) => {
      qc.invalidateQueries({ queryKey: docQK(txnId, folderId) });
      qc.invalidateQueries({ queryKey: folderQK(txnId) });
      qc.invalidateQueries({ queryKey: summaryQK(txnId) });
      toast.success("문서가 삭제되었습니다.");
    },
    onError: (err) => {
      toast.error(extractApiError(err, "문서 삭제에 실패했습니다."));
    },
  });
}

// ── Direct Upload ────────────────────────────────────────

/** 다중 파일 Direct Upload (폴더 미지정, AI 자동 분류) */
export function useDirectUpload(txnId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (files: File[]) => {
      const formData = new FormData();
      files.forEach((f) => formData.append("files", f));
      const { data } = await maApi.post(
        `/transactions/${txnId}/vdr/documents/direct-upload`,
        formData,
      );
      return data as DirectUploadBatchResult;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: folderQK(txnId) });
      qc.invalidateQueries({ queryKey: summaryQK(txnId) });
      qc.invalidateQueries({ queryKey: allDocQK(txnId) });
    },
    onError: (err) => {
      toast.error(extractApiError(err, "파일 업로드에 실패했습니다."));
    },
  });
}

/** 2차 심사 상태 폴링 */
export function useClassificationStatus(txnId: string, docIds: string[]) {
  return useQuery<ClassificationStatusItem[]>({
    queryKey: [
      "ma",
      "transactions",
      txnId,
      "vdr",
      "classification-status",
      [...docIds].sort(),
    ],
    queryFn: async () => {
      const params = new URLSearchParams();
      docIds.forEach((id) => params.append("doc_ids", id));
      const { data } = await maApi.get(
        `/transactions/${txnId}/vdr/documents/classification-status?${params}`,
      );
      return data;
    },
    enabled: docIds.length > 0,
    refetchInterval: (query) => {
      const data = query.state.data;
      if (!data) return CLASSIFICATION_POLL_INTERVAL_MS;
      const allResolved = data.every(
        (item) => item.classification_status !== "PENDING_REVIEW",
      );
      return allResolved ? false : CLASSIFICATION_POLL_INTERVAL_MS;
    },
    retry: 3,
    meta: {
      errorMessage: "분류 상태 조회에 실패했습니다.",
    },
  });
}

/** VDR 문서 다운로드 URL */
export function getVdrDownloadUrl(txnId: string, docId: string): string {
  return `/api/ma/transactions/${txnId}/vdr/documents/${docId}/download`;
}

/** 파일명 기반 VDR 폴더 카테고리 추천 */
export function useSuggestVdrCategory(txnId: string) {
  return useMutation({
    mutationFn: async (filename: string) => {
      const { data } = await maApi.post<{
        category: string | null;
        folder_name: string | null;
      }>(`/transactions/${txnId}/vdr/suggest-category`, { filename });
      return data;
    },
    onError: () => {
      // AI 카테고리 추천 실패는 조용히 무시 (선택적 기능)
    },
  });
}
