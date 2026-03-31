import type { AxiosError } from "axios";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

import { extractApiError } from "@/api/errors";
import { maApi } from "@/api/maClient";
import type {
  Attachment,
  AttachmentEntityType,
  AttachmentListResponse,
} from "@/modules/ma/types/attachment";

const DEV_LOCAL_AUTH_ENABLED =
  (import.meta.env.VITE_DEV_LOCAL_AUTH ?? "").trim() === "true";
const DEV_MA_PROXY_TARGET =
  (import.meta.env.VITE_MA_API_PROXY_TARGET ?? "").trim() || "127.0.0.1:8003";

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

function getAttachmentErrorPayload(err: unknown) {
  const axiosErr = err as AxiosError<unknown>;

  return {
    hasResponse: Boolean(axiosErr?.response),
    status: axiosErr?.response?.status ?? null,
    rawBody:
      typeof axiosErr?.response?.data === "string"
        ? axiosErr.response.data
        : null,
    message: err instanceof Error ? err.message : "",
  };
}

export function shouldRetryAttachmentUpload(
  err: unknown,
  isLocalDev: boolean = DEV_LOCAL_AUTH_ENABLED,
) {
  if (!isLocalDev) {
    return false;
  }

  const { hasResponse, status, rawBody, message } = getAttachmentErrorPayload(
    err,
  );
  const probe = `${rawBody ?? ""}\n${message}`.toLowerCase();

  if (!hasResponse) {
    return true;
  }

  if (status == null || ![500, 502, 503, 504].includes(status)) {
    return false;
  }

  return (
    probe.includes("econnrefused") ||
    probe.includes("connect ") ||
    probe.includes("socket hang up") ||
    probe.includes("etimedout") ||
    probe.includes("proxy error")
  );
}

export function buildAttachmentUploadErrorMessage(
  err: unknown,
  isLocalDev: boolean = DEV_LOCAL_AUTH_ENABLED,
  proxyTarget: string = DEV_MA_PROXY_TARGET,
) {
  if (shouldRetryAttachmentUpload(err, isLocalDev)) {
    return `개발 MA 백엔드(${proxyTarget})에 연결하지 못했습니다. deal-mgmt dev server가 실행 중인지 확인해 주세요.`;
  }

  return extractApiError(err, "파일 업로드에 실패했습니다.");
}

async function postAttachment(
  txnId: string,
  {
    file,
    entityType,
    entityId,
    description,
  }: {
    file: File;
    entityType: AttachmentEntityType;
    entityId?: string;
    description?: string;
  },
) {
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
}

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
      try {
        return await postAttachment(txnId, {
          file,
          entityType,
          entityId,
          description,
        });
      } catch (error) {
        if (!shouldRetryAttachmentUpload(error)) {
          throw error;
        }

        await new Promise((resolve) => setTimeout(resolve, 400));
        return await postAttachment(txnId, {
          file,
          entityType,
          entityId,
          description,
        });
      }
    },
    onSuccess: (data) => {
      qc.invalidateQueries({ queryKey: attachmentQK(txnId) });
      qc.invalidateQueries({
        queryKey: ["ma", "transactions", txnId, "vdr"],
      });

      if (data.vdr_sync) {
        toast.success(
          `파일이 업로드되었습니다. VDR '${data.vdr_sync.folder_name}' 폴더로 자동 분류되었습니다.`,
        );
      } else {
        toast.success("파일이 업로드되었습니다.");
      }
    },
    onError: (err: unknown) => {
      toast.error(buildAttachmentUploadErrorMessage(err));
    },
  });
}

export function useDeleteAttachment(txnId: string) {
  const qc = useQueryClient();

  return useMutation({
    mutationFn: async (attachmentId: string) => {
      await maApi.delete(`/transactions/${txnId}/attachments/${attachmentId}`);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: attachmentQK(txnId) });
      qc.invalidateQueries({
        queryKey: ["ma", "transactions", txnId, "vdr"],
      });
      toast.success("파일을 삭제했습니다.");
    },
    onError: (err: unknown) => {
      toast.error(extractApiError(err, "파일 삭제에 실패했습니다."));
    },
  });
}

export function getAttachmentDownloadUrl(
  txnId: string,
  attachmentId: string,
): string {
  return `/api/ma/transactions/${txnId}/attachments/${attachmentId}/download`;
}
