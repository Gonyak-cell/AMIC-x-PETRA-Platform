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
    queryKey: ["mappings", dealId],
    queryFn: async () => {
      const { data } = await api.get(`/deals/${dealId}/mappings`);
      return data;
    },
    enabled: !!dealId,
  });
}

export function useSuggestMappings(dealId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (body: { snapshot_id?: string } | void = {}) => {
      const { data } = await api.post(
        `/deals/${dealId}/mappings/suggest`,
        body ?? {}
      );
      return data as MappingSuggestion[];
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["mappings", dealId] });
    },
  });
}

export function useSaveMappings(dealId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (body: { mappings: AccountMappingCreate[] }) => {
      const { data } = await api.put(`/deals/${dealId}/mappings`, body);
      return data as AccountMappingRead[];
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["mappings", dealId] });
      queryClient.invalidateQueries({ queryKey: ["tie-out", dealId] });
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
      const { data } = await api.put(
        `/deals/${dealId}/mappings/${mappingId}/approve`,
        body
      );
      return data as AccountMappingRead;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["mappings", dealId] });
    },
  });
}

export function useApproveAllMappings(dealId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (body: { approved_by: string }) => {
      const { data } = await api.put(
        `/deals/${dealId}/mappings/approve-all`,
        body
      );
      return data as AccountMappingRead[];
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["mappings", dealId] });
    },
  });
}

export function useStandardLineItems() {
  return useQuery<StandardLineItem[]>({
    queryKey: ["standard-line-items"],
    queryFn: async () => {
      const { data } = await api.get("/standard-line-items");
      return data;
    },
  });
}

export function useTieOutResults(dealId: string) {
  return useQuery<TieOutResultRead[]>({
    queryKey: ["tie-out", dealId],
    queryFn: async () => {
      const { data } = await api.get(`/deals/${dealId}/tie-out`);
      return data;
    },
    enabled: !!dealId,
  });
}
