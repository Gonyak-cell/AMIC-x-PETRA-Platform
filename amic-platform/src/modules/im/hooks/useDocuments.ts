import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { imApi } from "@/api/imClient";
import type {
  Document,
  DocumentCreate,
  DocumentListParams,
  DocumentStatus,
} from "@/modules/im/types/document";

const IN_PROGRESS_STATUSES: DocumentStatus[] = [
  "PENDING",
  "COLLECTING",
  "ANALYZING",
  "GENERATING",
  "RENDERING",
];

export function useDocuments(params: DocumentListParams = {}) {
  return useQuery<{ items: Document[]; total: number }>({
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
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      if (status && IN_PROGRESS_STATUSES.includes(status)) {
        return 3000;
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

      const blob = new Blob([response.data]);
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;

      const contentDisposition = response.headers["content-disposition"];
      const filename = contentDisposition
        ? contentDisposition.split("filename=")[1]?.replace(/"/g, "")
        : `document.${format}`;

      link.download = filename;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
    },
  });
}
