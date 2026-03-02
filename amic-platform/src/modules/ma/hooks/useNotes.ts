import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { maApi } from "@/api/maClient";
import type {
  DealNote,
  NoteCreate,
  NoteUpdate,
  NoteListResponse,
  NoteType,
} from "@/modules/ma/types/note";

export function useNotes(
  txnId: string,
  opts?: { noteType?: NoteType; pinnedOnly?: boolean },
  active = true,
) {
  return useQuery<NoteListResponse>({
    queryKey: ["ma", "transactions", txnId, "notes", opts],
    queryFn: async () => {
      const params: Record<string, string> = {};
      if (opts?.noteType) params.note_type = opts.noteType;
      if (opts?.pinnedOnly) params.pinned_only = "true";
      const { data } = await maApi.get(`/transactions/${txnId}/notes`, {
        params,
      });
      return data;
    },
    enabled: !!txnId && active,
  });
}

export function useNoteReplies(txnId: string, noteId: string) {
  return useQuery<NoteListResponse>({
    queryKey: ["ma", "transactions", txnId, "notes", noteId, "replies"],
    queryFn: async () => {
      const { data } = await maApi.get(
        `/transactions/${txnId}/notes/${noteId}/replies`,
      );
      return data;
    },
    enabled: !!txnId && !!noteId,
  });
}

export function useCreateNote(txnId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: NoteCreate) => {
      const { data } = await maApi.post(`/transactions/${txnId}/notes`, body);
      return data as DealNote;
    },
    onSuccess: () => {
      qc.invalidateQueries({
        queryKey: ["ma", "transactions", txnId, "notes"],
      });
      toast.success("노트가 작성되었습니다.");
    },
    onError: () => {
      toast.error("노트 작성에 실패했습니다.");
    },
  });
}

export function useUpdateNote(txnId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({
      noteId,
      body,
    }: {
      noteId: string;
      body: NoteUpdate;
    }) => {
      const { data } = await maApi.patch(
        `/transactions/${txnId}/notes/${noteId}`,
        body,
      );
      return data as DealNote;
    },
    onSuccess: () => {
      qc.invalidateQueries({
        queryKey: ["ma", "transactions", txnId, "notes"],
      });
      toast.success("노트가 수정되었습니다.");
    },
    onError: () => {
      toast.error("노트 수정에 실패했습니다.");
    },
  });
}

export function useDeleteNote(txnId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (noteId: string) => {
      await maApi.delete(`/transactions/${txnId}/notes/${noteId}`);
    },
    onSuccess: () => {
      qc.invalidateQueries({
        queryKey: ["ma", "transactions", txnId, "notes"],
      });
      toast.success("노트가 삭제되었습니다.");
    },
    onError: () => {
      toast.error("노트 삭제에 실패했습니다.");
    },
  });
}
