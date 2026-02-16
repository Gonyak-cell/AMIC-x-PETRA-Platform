import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import api from "@/api/client";
import type { DealDefinition, DefinitionData } from "@/modules/fdd/types/deal";

export function useDefinitions(dealId: string) {
  return useQuery<DealDefinition[]>({
    queryKey: ["fdd", "definitions", dealId],
    queryFn: async () => {
      const { data } = await api.get(`/deals/${dealId}/definitions`);
      return data;
    },
    enabled: !!dealId,
  });
}

export function useCreateDefinition(dealId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (defData: DefinitionData) => {
      const { data } = await api.post(`/deals/${dealId}/definitions`, {
        definition_data: defData,
      });
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["fdd", "definitions", dealId] });
    },
    onError: (error: Error) => {
      console.error("useCreateDefinition failed:", error);
    },
  });
}

export function useApproveDefinition(dealId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ version, approved_by }: { version: number; approved_by: string }) => {
      const { data } = await api.put(
        `/deals/${dealId}/definitions/${version}/approve`,
        { approved_by }
      );
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["fdd", "definitions", dealId] });
    },
    onError: (error: Error) => {
      console.error("useApproveDefinition failed:", error);
    },
  });
}
