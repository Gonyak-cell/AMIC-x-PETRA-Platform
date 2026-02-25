import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import axios from "axios";
import { imApi } from "@/api/imClient";
import type {
  Document,
  DocumentCreate,
  DocumentListParams,
} from "@/modules/docs/types/document";
import { IN_PROGRESS_STATUSES } from "@/modules/docs/types/document";

const POLL_INTERVAL_MS = 3_000;

function sanitizeFilename(name: string): string {
  return name.replace(/[^\w.\-가-힣 ]/g, "_").slice(0, 255);
}

export function useDocuments(params: DocumentListParams = {}) {
  return useQuery<{ items: Document[]; total: number; offset: number; limit: number }>({
    queryKey: ["im", "documents", params],
    queryFn: async () => {
      const { data } = await imApi.get("/documents", { params });
      return data;
    },
  });
}

export function useDocument(documentId: string) {
  return useQuery<Document>({
    queryKey: ["im", "documents", documentId],
    queryFn: async () => {
      const { data } = await imApi.get(`/documents/${documentId}`);
      return data;
    },
    enabled: !!documentId,
    refetchInterval: (query): number | false => {
      const status = query.state.data?.status;
      if (status && IN_PROGRESS_STATUSES.includes(status)) {
        return POLL_INTERVAL_MS;
      }
      return false;
    },
  });
}

export function useCreateDocument() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (body: DocumentCreate) => {
      const { data } = await imApi.post("/documents", body);
      return data as Document;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["im", "documents"] });
    },
    onError: () => {
      toast.error("Failed to create document");
    },
  });
}

export function useUploadFinancials() {
  return useMutation({
    mutationFn: async ({ documentId, file }: { documentId: string; file: File }) => {
      const formData = new FormData();
      formData.append("file", file);
      const { data } = await imApi.post(
        `/documents/${documentId}/upload-financials`,
        formData,
        { headers: { "Content-Type": "multipart/form-data" } },
      );
      return data as { status: string; filename: string; size: number };
    },
    onError: () => {
      toast.error("Failed to upload financial data");
    },
  });
}

export function useDeleteDocument() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (documentId: string) => {
      await imApi.delete(`/documents/${documentId}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["im", "documents"] });
      toast.success("문서가 삭제되었습니다.");
    },
    onError: (error: unknown) => {
      if (axios.isAxiosError(error) && error.response?.status === 409) {
        toast.error("진행 중인 문서는 삭제할 수 없습니다. 완료 또는 실패 후 다시 시도해 주세요.");
      } else {
        toast.error("문서 삭제에 실패했습니다.");
      }
    },
  });
}

export function useDownloadDocument() {
  return useMutation({
    mutationFn: async ({
      documentId,
      format,
    }: {
      documentId: string;
      format: "pptx" | "pdf";
    }) => {
      const response = await imApi.get(
        `/documents/${documentId}/download`,
        {
          params: { format },
          responseType: "blob",
        },
      );

      if (!(response.data instanceof Blob)) {
        throw new Error("Expected Blob response from download endpoint");
      }

      const blob = response.data;
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");

      try {
        link.href = url;

        const contentDisposition = response.headers["content-disposition"];
        let filename = `document.${format}`;
        if (contentDisposition) {
          const utf8Match = contentDisposition.match(/filename\*=UTF-8''(.+?)(?:;|$)/i);
          const stdMatch = contentDisposition.match(/filename="?([^";\n]+)"?/i);
          const raw = utf8Match?.[1] ?? stdMatch?.[1];
          if (raw) {
            filename = sanitizeFilename(
              utf8Match ? decodeURIComponent(raw) : raw.trim(),
            );
          }
        }

        link.download = filename;
        document.body.appendChild(link);
        link.click();
      } finally {
        if (document.body.contains(link)) {
          document.body.removeChild(link);
        }
        setTimeout(() => window.URL.revokeObjectURL(url), 200);
      }
    },
    onError: () => {
      toast.error("Document download failed");
    },
  });
}
