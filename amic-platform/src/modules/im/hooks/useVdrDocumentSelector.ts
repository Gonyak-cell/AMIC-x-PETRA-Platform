import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { maApi } from "@/api/maClient";
import { imApi } from "@/api/imClient";
import type { VdrDocument, VdrFolder } from "@/modules/ma/types/vdr";
import type { CreateFromVdrRequest, CreateFromVdrResponse } from "@/modules/im/types/checklist";

// ── Query Keys ──────────────────────────────────────────────

const txnVdrFoldersQK = (txnId: string) =>
  ["ma", "transactions", txnId, "vdr", "folders"] as const;

const txnVdrDocsQK = (txnId: string, folderId: string) =>
  ["ma", "transactions", txnId, "vdr", "folders", folderId, "documents"] as const;

// ── Queries ─────────────────────────────────────────────────

/** Fetch VDR folders for a given M&A transaction. */
export function useTransactionVdrFolders(txnId: string) {
  return useQuery<VdrFolder[]>({
    queryKey: txnVdrFoldersQK(txnId),
    queryFn: async () => {
      const { data } = await maApi.get(`/transactions/${txnId}/vdr/folders`);
      return data;
    },
    enabled: !!txnId,
  });
}

/** Fetch VDR documents inside a specific folder. */
export function useTransactionVdrDocuments(txnId: string, folderId: string) {
  return useQuery<VdrDocument[]>({
    queryKey: txnVdrDocsQK(txnId, folderId),
    queryFn: async () => {
      const { data } = await maApi.get(
        `/transactions/${txnId}/vdr/folders/${folderId}/documents`,
      );
      return data;
    },
    enabled: !!txnId && !!folderId,
  });
}

// ── Mutations ───────────────────────────────────────────────

/** Create an IM document from VDR documents (kicks off extraction). */
export function useCreateFromVdr() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: CreateFromVdrRequest) => {
      const { data } = await imApi.post("/documents/from-vdr", body);
      return data as CreateFromVdrResponse;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["im", "documents"] });
      toast.success("VDR extraction started");
    },
    onError: () => {
      toast.error("Failed to create IM from VDR");
    },
  });
}
