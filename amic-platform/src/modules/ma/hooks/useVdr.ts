import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

import { maApi } from "@/api/maClient";
import type {
  VdrDocument,
  VdrDocumentUpdate,
  VdrFolder,
  VdrFolderCreate,
  VdrFolderUpdate,
  VdrSummary,
} from "@/modules/ma/types/vdr";

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

export function useVdrFolders(txnId: string) {
  return useQuery<VdrFolder[]>({
    queryKey: folderQK(txnId),
    queryFn: async () => {
      const { data } = await maApi.get(`/transactions/${txnId}/vdr/folders`);
      return data;
    },
    enabled: !!txnId,
  });
}

export function useInitVdr(txnId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async () => {
      const { data } = await maApi.post(`/transactions/${txnId}/vdr/init`, {});
      return data as VdrFolder[];
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: folderQK(txnId) });
      qc.invalidateQueries({ queryKey: summaryQK(txnId) });
      toast.success("VDR이 초기화되었습니다.");
    },
    onError: () => {
      toast.error("VDR 초기화에 실패했습니다.");
    },
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
    onError: () => {
      toast.error("폴더 생성에 실패했습니다.");
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
    onError: () => {
      toast.error("폴더 수정에 실패했습니다.");
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
    onError: () => {
      toast.error("폴더 삭제에 실패했습니다.");
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
      toast.success("파일이 업로드되었습니다.");
    },
    onError: () => {
      toast.error("파일 업로드에 실패했습니다.");
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
      qc.invalidateQueries({
        queryKey: ["ma", "transactions", txnId, "vdr"],
      });
      toast.success("문서가 수정되었습니다.");
    },
    onError: () => {
      toast.error("문서 수정에 실패했습니다.");
    },
  });
}

export function useDeleteVdrDocument(txnId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (docId: string) => {
      await maApi.delete(`/transactions/${txnId}/vdr/documents/${docId}`);
    },
    onSuccess: () => {
      qc.invalidateQueries({
        queryKey: ["ma", "transactions", txnId, "vdr"],
      });
      toast.success("문서가 삭제되었습니다.");
    },
    onError: () => {
      toast.error("문서 삭제에 실패했습니다.");
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
      const { data } = await maApi.post(
        `/transactions/${txnId}/vdr/suggest-category`,
        { filename },
      );
      return data as { category: string | null; folder_name: string | null };
    },
  });
}
