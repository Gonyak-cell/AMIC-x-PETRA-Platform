import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import api from "@/api/client";
import type {
  Comment,
  CommentCreate,
  CommentEntityType,
} from "@/types/collaboration";

export function useComments(entityType: CommentEntityType, entityId: string) {
  return useQuery<Comment[]>({
    queryKey: ["comments", entityType, entityId],
    queryFn: async () => {
      try {
        const { data } = await api.get<Comment[]>("/comments", {
          params: { entity_type: entityType, entity_id: entityId },
        });
        return data;
      } catch {
        // Backend not implemented yet
        return [];
      }
    },
    enabled: !!entityId,
  });
}

export function useCreateComment(
  entityType: CommentEntityType,
  entityId: string,
) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (body: CommentCreate) => {
      const { data } = await api.post<Comment>("/comments", {
        entity_type: entityType,
        entity_id: entityId,
        ...body,
      });
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["comments", entityType, entityId],
      });
      toast.success("Comment posted");
    },
    onError: () => {
      toast.error("Failed to post comment");
    },
  });
}

export function useUpdateComment(
  entityType: CommentEntityType,
  entityId: string,
) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      commentId,
      content,
    }: {
      commentId: string;
      content: string;
    }) => {
      const { data } = await api.patch<Comment>(`/comments/${commentId}`, {
        content,
      });
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["comments", entityType, entityId],
      });
      toast.success("Comment updated");
    },
    onError: () => {
      toast.error("Failed to update comment");
    },
  });
}

export function useDeleteComment(
  entityType: CommentEntityType,
  entityId: string,
) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (commentId: string) => {
      await api.delete(`/comments/${commentId}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["comments", entityType, entityId],
      });
      toast.success("Comment deleted");
    },
    onError: () => {
      toast.error("Failed to delete comment");
    },
  });
}
