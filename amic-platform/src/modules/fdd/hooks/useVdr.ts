import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import api from "@/api/client";
import type { VdrFolder } from "@/modules/fdd/types/vdr";

export function useVdrFolders(dealId: string) {
  return useQuery<VdrFolder[]>({
    queryKey: ["vdr", dealId],
    queryFn: async () => {
      const { data } = await api.get(`/deals/${dealId}/vdr/folders`);
      return data;
    },
    enabled: !!dealId,
  });
}

export function useInitializeVdr(dealId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async () => {
      const { data } = await api.post(`/deals/${dealId}/vdr/init`, {});
      return data as VdrFolder[];
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["vdr", dealId] });
    },
  });
}

export function useCreateVdrFolder(dealId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (body: { name: string; parent_id?: string; folder_type?: string }) => {
      const { data } = await api.post(`/deals/${dealId}/vdr/folders`, body);
      return data as VdrFolder;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["vdr", dealId] });
    },
  });
}
