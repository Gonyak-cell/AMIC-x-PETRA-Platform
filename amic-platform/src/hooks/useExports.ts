import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useRef } from "react";
import api from "@/api/client";
import type {
  ExportRecord,
  ExportListParams,
  PaginatedExports,
} from "@/types/export";

const EMPTY_EXPORTS: PaginatedExports = { items: [], total: 0, page: 1, size: 20 };

export function useExports(params: ExportListParams = {}) {
  const endpointAvailableRef = useRef(true);

  const query = useQuery<PaginatedExports>({
    queryKey: ["exports", params],
    queryFn: async () => {
      try {
        const { data } = await api.get<PaginatedExports>("/exports", {
          params,
        });
        endpointAvailableRef.current = true;
        return data;
      } catch (error: unknown) {
        const status =
          error && typeof error === "object" && "response" in error
            ? (error as { response?: { status?: number } }).response?.status
            : undefined;
        if (status === 404 || status === 405) {
          endpointAvailableRef.current = false;
        }
        return EMPTY_EXPORTS;
      }
    },
    staleTime: 30_000,
  });

  return {
    ...query,
    endpointAvailable: endpointAvailableRef.current,
  };
}

export function useRedownload() {
  return useMutation({
    mutationFn: async (exportRecord: ExportRecord) => {
      const response = await api.get(
        `/exports/${exportRecord.id}/download`,
        { responseType: "blob" },
      );

      const blob = new Blob([response.data]);
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;

      const contentDisposition = response.headers["content-disposition"];
      const filename = contentDisposition
        ? contentDisposition.split("filename=")[1]?.replace(/"/g, "")
        : `${exportRecord.name}.${exportRecord.format}`;

      link.download = filename;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
    },
  });
}

export function useBatchDownload() {
  return useMutation({
    mutationFn: async (exportIds: string[]) => {
      const response = await api.post(
        "/exports/batch-download",
        { export_ids: exportIds },
        { responseType: "blob" },
      );

      const blob = new Blob([response.data]);
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = "exports-batch.zip";
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
    },
  });
}

export function useDeleteExport() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (exportId: string) => {
      await api.delete(`/exports/${exportId}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["exports"] });
    },
  });
}
