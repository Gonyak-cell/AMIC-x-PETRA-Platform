import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

import { maApi } from "@/api/maClient";
import type {
  Attachment,
  AttachmentEntityType,
  AttachmentListResponse,
} from "@/modules/ma/types/attachment";

// ── Query Keys ──────────────────────────────────────────

const attachmentQK = (
  txnId: string,
  entityType?: AttachmentEntityType,
  entityId?: string,
) =>
  [
    "ma",
    "transactions",
    txnId,
    "attachments",
    ...(entityType ? [entityType] : []),
    ...(entityId ? [entityId] : []),
  ] as const;

// ── 목록 조회 ────────────────────────────────────────────

export function useAttachments(
  txnId: string,
  entityType?: AttachmentEntityType,
  entityId?: string,
) {
  return useQuery<AttachmentListResponse>({
    queryKey: attachmentQK(txnId, entityType, entityId),
    queryFn: async () => {
      const params = new URLSearchParams();
      if (entityType) params.set("entity_type", entityType);
      if (entityId) params.set("entity_id", entityId);
      const { data } = await maApi.get<AttachmentListResponse>(
        `/transactions/${txnId}/attachments?${params.toString()}`,
      );
      return data;
    },
    enabled: !!txnId,
  });
}

// ── 업로드 ───────────────────────────────────────────────

export function useUploadAttachment(txnId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({
      file,
      entityType,
      entityId,
      description,
    }: {
      file: File;
      entityType: AttachmentEntityType;
      entityId?: string;
      description?: string;
    }) => {
      const formData = new FormData();
      formData.append("file", file);
      formData.append("entity_type", entityType);
      if (entityId) formData.append("entity_id", entityId);
      if (description) formData.append("description", description);
      const { data } = await maApi.post<Attachment>(
        `/transactions/${txnId}/attachments`,
        formData,
      );
      return data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: attachmentQK(txnId) });
      toast.success("파일이 업로드되었습니다.");
    },
    onError: () => {
      toast.error("파일 업로드에 실패했습니다.");
    },
  });
}

// ── 삭제 ────────────────────────────────────────────────

export function useDeleteAttachment(txnId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (attachmentId: string) => {
      await maApi.delete(`/transactions/${txnId}/attachments/${attachmentId}`);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: attachmentQK(txnId) });
      toast.success("파일이 삭제되었습니다.");
    },
    onError: () => {
      toast.error("파일 삭제에 실패했습니다.");
    },
  });
}

// ── 다운로드 URL ────────────────────────────────────────

export function getAttachmentDownloadUrl(
  txnId: string,
  attachmentId: string,
): string {
  return `/api/ma/transactions/${txnId}/attachments/${attachmentId}/download`;
}
