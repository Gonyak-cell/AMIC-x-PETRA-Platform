import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import api from "@/api/client";
import type {
  MappingSuggestion,
  AccountMappingRead,
  AccountMappingCreate,
  StandardLineItem,
  TieOutResultRead,
} from "@/modules/fdd/types/mapping";

export function useMappings(dealId: string) {
  return useQuery<AccountMappingRead[]>({
    queryKey: ["fdd", "mappings", dealId],
    queryFn: async () => {
      const { data } = await api.get(`/deals/${dealId}/mappings`);
      return data;
    },
    enabled: !!dealId,
  });
}

export function useSuggestMappings(dealId: string) {
  return useMutation({
    mutationFn: async () => {
      const { data } = await api.post(
        `/deals/${dealId}/mappings/suggest`
      );
      return data as MappingSuggestion[];
    },
    onError: (error: Error) => {
      console.error("useSuggestMappings failed:", error);
    },
  });
}

export function useSaveMappings(dealId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (body: { mappings: AccountMappingCreate[] }) => {
      const { data } = await api.post(`/deals/${dealId}/mappings`, body);
      return data as AccountMappingRead[];
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["fdd", "mappings", dealId] });
      queryClient.invalidateQueries({ queryKey: ["fdd", "tie-out", dealId] });
    },
    onError: (error: Error) => {
      console.error("useSaveMappings failed:", error);
    },
  });
}

export function useApproveMapping(dealId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({
      mappingId,
      body,
    }: {
      mappingId: string;
      body: { approved_by: string };
    }) => {
      const { data } = await api.post(
        `/deals/${dealId}/mappings/${mappingId}/approve`,
        body
      );
      return data as AccountMappingRead;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["fdd", "mappings", dealId] });
      queryClient.invalidateQueries({ queryKey: ["fdd", "tie-out", dealId] });
    },
    onError: (error: Error) => {
      console.error("useApproveMapping failed:", error);
    },
  });
}

export function useApproveAllMappings(dealId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (body: { approved_by: string }) => {
      const { data } = await api.post(
        `/deals/${dealId}/mappings/approve-all`,
        body
      );
      return data as AccountMappingRead[];
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["fdd", "mappings", dealId] });
      queryClient.invalidateQueries({ queryKey: ["fdd", "tie-out", dealId] });
    },
    onError: (error: Error) => {
      console.error("useApproveAllMappings failed:", error);
    },
  });
}

export function useStandardLineItems() {
  return useQuery<StandardLineItem[]>({
    queryKey: ["fdd", "standard-line-items"],
    queryFn: async () => {
      const { data } = await api.get("/standard-line-items");
      return data;
    },
    staleTime: 60 * 60 * 1000, // 1 hour — reference data rarely changes
  });
}

export function useTieOutResults(dealId: string) {
  return useQuery<TieOutResultRead[]>({
    queryKey: ["fdd", "tie-out", dealId],
    queryFn: async () => {
      const { data } = await api.get(`/deals/${dealId}/tie-out`);
      return data;
    },
    enabled: !!dealId,
  });
}
