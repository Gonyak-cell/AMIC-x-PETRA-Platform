import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { imApi } from "@/api/imClient";
import type {
  Diagram,
  DiagramListItem,
  DiagramType,
  ExcalidrawData,
} from "@/components/diagrams/types";

// ── Query Keys ──────────────────────────────────────────────

const diagramsQK = (documentId: string) =>
  ["im", "documents", documentId, "diagrams"] as const;

const diagramQK = (documentId: string, diagramId: string) =>
  ["im", "documents", documentId, "diagrams", diagramId] as const;

// ── Queries ─────────────────────────────────────────────────

/** Fetch all diagrams for a document (excalidraw_data 생략). */
export function useDiagrams(documentId: string) {
  return useQuery<DiagramListItem[]>({
    queryKey: diagramsQK(documentId),
    queryFn: async () => {
      const { data } = await imApi.get(`/documents/${documentId}/diagrams`);
      return data;
    },
    enabled: !!documentId,
  });
}

/** Fetch a single diagram with full Excalidraw data. */
export function useDiagram(documentId: string, diagramId: string) {
  return useQuery<Diagram>({
    queryKey: diagramQK(documentId, diagramId),
    queryFn: async () => {
      const { data } = await imApi.get(
        `/documents/${documentId}/diagrams/${diagramId}`,
      );
      return data;
    },
    enabled: !!documentId && !!diagramId,
  });
}

// ── Mutations ───────────────────────────────────────────────

/** Create a new diagram (from template or custom). */
export function useCreateDiagram(documentId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: {
      diagram_type: DiagramType;
      title: string;
      excalidraw_data: ExcalidrawData;
    }) => {
      const { data } = await imApi.post(
        `/documents/${documentId}/diagrams`,
        body,
      );
      return data as Diagram;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: diagramsQK(documentId) });
      toast.success("Diagram created");
    },
    onError: () => {
      toast.error("Failed to create diagram");
    },
  });
}

/** Update a diagram's Excalidraw data (auto-save / manual save). */
export function useUpdateDiagram(documentId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({
      diagramId,
      excalidraw_data,
    }: {
      diagramId: string;
      excalidraw_data: ExcalidrawData;
    }) => {
      const { data } = await imApi.put(
        `/documents/${documentId}/diagrams/${diagramId}`,
        { excalidraw_data },
      );
      return data as Diagram;
    },
    onSuccess: (_data, variables) => {
      qc.invalidateQueries({
        queryKey: diagramQK(documentId, variables.diagramId),
      });
      qc.invalidateQueries({ queryKey: diagramsQK(documentId) });
    },
    onError: () => {
      toast.error("Failed to save diagram");
    },
  });
}

/** Delete a diagram. */
export function useDeleteDiagram(documentId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (diagramId: string) => {
      await imApi.delete(`/documents/${documentId}/diagrams/${diagramId}`);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: diagramsQK(documentId) });
      toast.success("Diagram deleted");
    },
    onError: () => {
      toast.error("Failed to delete diagram");
    },
  });
}

/** Export diagram as PNG and upload to backend. */
export function useExportDiagramPng(documentId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({
      diagramId,
      pngBlob,
    }: {
      diagramId: string;
      pngBlob: Blob;
    }) => {
      const formData = new FormData();
      formData.append("file", pngBlob, "diagram.png");
      const { data } = await imApi.post(
        `/documents/${documentId}/diagrams/${diagramId}/export-png`,
        formData,
        { headers: { "Content-Type": "multipart/form-data" } },
      );
      return data as { png_path: string };
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: diagramsQK(documentId) });
      toast.success("PNG exported to server");
    },
    onError: () => {
      toast.error("Failed to export PNG");
    },
  });
}
