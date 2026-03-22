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
  VdrRoutingOverride,
  VdrRoutingOverrideUpsert,
  VdrRoutingQueueResponse,
  VdrRoutingQueueStatus,
  VdrSummary,
} from "@/modules/ma/types/vdr";
import { CLASSIFICATION_POLL_INTERVAL_MS } from "@/modules/ma/types/vdr";

const vdrBaseQK = (txnId: string) => ["ma", "transactions", txnId, "vdr"] as const;
const folderQK = (txnId: string) => [...vdrBaseQK(txnId), "folders"] as const;
const docQK = (txnId: string, folderId: string) =>
  [...folderQK(txnId), folderId, "documents"] as const;
const allDocQK = (txnId: string) => [...vdrBaseQK(txnId), "all-documents"] as const;
const summaryQK = (txnId: string) => [...vdrBaseQK(txnId), "summary"] as const;
const routingQueueQK = (txnId: string, status: VdrRoutingQueueStatus) =>
  [...vdrBaseQK(txnId), "routing-queue", status] as const;

function invalidateRoutingQueue(qc: ReturnType<typeof useQueryClient>, txnId: string) {
  qc.invalidateQueries({ queryKey: [...vdrBaseQK(txnId), "routing-queue"] });
}

function flattenVdrFolders(tree: VdrFolder[]): VdrFolder[] {
  const result: VdrFolder[] = [];

  function walk(nodes: VdrFolder[]) {
    for (const node of nodes) {
      result.push(node);
      if (node.children.length > 0) {
        walk(node.children);
      }
    }
  }

  walk(tree);
  return result;
}

export async function uploadFilesToVdr(
  txnId: string,
  files: File[],
  options?: { folderId?: string },
): Promise<DirectUploadBatchResult> {
  const formData = new FormData();
  files.forEach((file) => formData.append("files", file));
  if (options?.folderId) {
    formData.append("folder_id", options.folderId);
  }

  const { data } = await maApi.post(`/transactions/${txnId}/vdr/uploads`, formData);
  return data as DirectUploadBatchResult;
}

function getUploadErrorMessage(err: unknown, fallback: string): string {
  if (err instanceof Error && err.message) {
    return err.message;
  }
  return extractApiError(err, fallback);
}

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
      const { data } = await maApi.post(`/transactions/${txnId}/vdr/folders`, body);
      return data as VdrFolder;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: folderQK(txnId) });
      toast.success("Folder created.");
    },
    onError: (err) => {
      toast.error(extractApiError(err, "Failed to create folder."));
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
      toast.success("Folder updated.");
    },
    onError: (err) => {
      toast.error(extractApiError(err, "Failed to update folder."));
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
      invalidateRoutingQueue(qc, txnId);
      toast.success("Folder deleted.");
    },
    onError: (err) => {
      toast.error(extractApiError(err, "Failed to delete folder."));
    },
  });
}

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
      const result = await uploadFilesToVdr(txnId, [file], { folderId });
      const document = result.results[0]?.document;
      if (!document) {
        throw new Error(result.failed_files[0]?.reason ?? "Failed to upload file.");
      }
      return document;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: docQK(txnId, folderId) });
      qc.invalidateQueries({ queryKey: folderQK(txnId) });
      qc.invalidateQueries({ queryKey: summaryQK(txnId) });
      qc.invalidateQueries({ queryKey: allDocQK(txnId) });
      invalidateRoutingQueue(qc, txnId);
      toast.success("File uploaded.");
    },
    onError: (err) => {
      toast.error(getUploadErrorMessage(err, "Failed to upload file."));
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
      qc.invalidateQueries({ queryKey: folderQK(txnId) });
      qc.invalidateQueries({ queryKey: allDocQK(txnId) });
      invalidateRoutingQueue(qc, txnId);
      toast.success("Document updated.");
    },
    onError: (err) => {
      toast.error(extractApiError(err, "Failed to update document."));
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
      invalidateRoutingQueue(qc, txnId);
      toast.success("Document deleted.");
    },
    onError: (err) => {
      toast.error(extractApiError(err, "Failed to delete document."));
    },
  });
}

export function useVdrRoutingQueue(
  txnId: string,
  status: VdrRoutingQueueStatus,
) {
  return useQuery<VdrRoutingQueueResponse>({
    queryKey: routingQueueQK(txnId, status),
    queryFn: async () => {
      const { data } = await maApi.get(
        `/transactions/${txnId}/vdr/routing-queue`,
        { params: { status } },
      );
      return data;
    },
    enabled: !!txnId,
  });
}

export function useUpsertVdrRoutingOverride(txnId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({
      docId,
      body,
    }: {
      docId: string;
      body: VdrRoutingOverrideUpsert;
    }) => {
      const { data } = await maApi.put(
        `/transactions/${txnId}/vdr/documents/${docId}/routing-override`,
        body,
      );
      return data as VdrRoutingOverride;
    },
    onSuccess: () => {
      invalidateRoutingQueue(qc, txnId);
      toast.success("Routing override saved.");
    },
    onError: (err) => {
      toast.error(extractApiError(err, "Failed to save routing override."));
    },
  });
}

export function useDeleteVdrRoutingOverride(txnId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (docId: string) => {
      await maApi.delete(
        `/transactions/${txnId}/vdr/documents/${docId}/routing-override`,
      );
    },
    onSuccess: () => {
      invalidateRoutingQueue(qc, txnId);
      toast.success("Routing override removed.");
    },
    onError: (err) => {
      toast.error(extractApiError(err, "Failed to remove routing override."));
    },
  });
}

export function useDirectUpload(txnId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (files: File[]) => uploadFilesToVdr(txnId, files),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: folderQK(txnId) });
      qc.invalidateQueries({ queryKey: summaryQK(txnId) });
      qc.invalidateQueries({ queryKey: allDocQK(txnId) });
      invalidateRoutingQueue(qc, txnId);
    },
    onError: (err) => {
      toast.error(extractApiError(err, "Failed to upload files."));
    },
  });
}

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
      if (!data) {
        return CLASSIFICATION_POLL_INTERVAL_MS;
      }
      const allResolved = data.every(
        (item) => item.classification_status !== "PENDING_REVIEW",
      );
      return allResolved ? false : CLASSIFICATION_POLL_INTERVAL_MS;
    },
    retry: 3,
    meta: {
      errorMessage: "Failed to load classification status.",
    },
  });
}

export function getVdrDownloadUrl(txnId: string, docId: string): string {
  return `/api/ma/transactions/${txnId}/vdr/documents/${docId}/download`;
}

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
      // Optional hint feature. Fail silently.
    },
  });
}
