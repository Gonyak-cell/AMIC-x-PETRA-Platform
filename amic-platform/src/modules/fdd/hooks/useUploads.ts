import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import api from "@/api/client";
import type {
  UploadFile,
  UploadType,
  UploadFileDetail,
} from "@/modules/fdd/types/deal";

export function useUploads(dealId: string) {
  return useQuery<UploadFile[]>({
    queryKey: ["fdd", "uploads", dealId],
    queryFn: async () => {
      const { data } = await api.get(`/deals/${dealId}/uploads`);
      return data;
    },
    enabled: !!dealId,
  });
}

export function useUploadFile(dealId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (file: File) => {
      const formData = new FormData();
      formData.append("file", file);
      // No Content-Type header — axios auto-detects FormData and sets multipart/form-data with boundary
      const { data } = await api.post(`/deals/${dealId}/uploads`, formData);
      return data as UploadFile;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["fdd", "uploads", dealId] });
    },
    onError: (error: Error) => {
      console.error("useUploadFile failed:", error);
    },
  });
}

export function useConfirmType(dealId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({
      uploadId,
      confirmedType,
    }: {
      uploadId: string;
      confirmedType: UploadType;
    }) => {
      const { data } = await api.put(
        `/deals/${dealId}/uploads/${uploadId}/confirm-type`,
        { confirmed_type: confirmedType }
      );
      return data as UploadFile;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["fdd", "uploads", dealId] });
    },
    onError: (error: Error) => {
      console.error("useConfirmType failed:", error);
    },
  });
}

export function useIngestUpload(dealId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      const { data } = await api.post(
        `/deals/${dealId}/uploads/${id}/ingest`
      );
      return data as UploadFile;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["fdd", "uploads", dealId] });
    },
    onError: (error: Error) => {
      console.error("useIngestUpload failed:", error);
    },
  });
}

export function useUploadDetail(dealId: string, uploadId: string | null) {
  return useQuery<UploadFileDetail>({
    queryKey: ["fdd", "uploads", dealId, uploadId],
    queryFn: async () => {
      const { data } = await api.get(
        `/deals/${dealId}/uploads/${uploadId}`
      );
      return data;
    },
    enabled: !!dealId && !!uploadId,
  });
}
