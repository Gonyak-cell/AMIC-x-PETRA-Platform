import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import api from "@/api/client";
import type {
  NWCCalculationRead,
  NWCLineItemRead,
  NWCClassification,
  PegMethod,
  PegSimulationResult,
} from "@/modules/fdd/types/nwc";

export function useNWCCalculations(dealId: string) {
  return useQuery<NWCCalculationRead[]>({
    queryKey: ["nwc", dealId],
    queryFn: async () => {
      const { data } = await api.get(`/deals/${dealId}/nwc`);
      return data;
    },
    enabled: !!dealId,
  });
}

export function useRunNWC(dealId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (body: {
      snapshot_id: string;
      peg_method?: PegMethod;
      custom_peg_value?: string | null;
    }) => {
      const { data } = await api.post(`/deals/${dealId}/nwc/run`, body);
      return data as NWCCalculationRead;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["nwc", dealId] });
    },
  });
}

export function usePegSimulation(
  dealId: string,
  nwcId: string
) {
  return useQuery<{ reference_nwc: string; scenarios: PegSimulationResult[] }>({
    queryKey: ["nwc", dealId, nwcId, "peg-simulation"],
    queryFn: async () => {
      const { data } = await api.get(
        `/deals/${dealId}/nwc/${nwcId}/peg-simulate`
      );
      return data;
    },
    enabled: !!dealId && !!nwcId,
  });
}

export function useRecalculatePeg(dealId: string, nwcId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (body: {
      peg_method: PegMethod;
      custom_value?: string | null;
    }) => {
      const { data } = await api.post(
        `/deals/${dealId}/nwc/${nwcId}/peg-recalculate`,
        body
      );
      return data as NWCCalculationRead;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["nwc", dealId] });
    },
  });
}

export function useUpdateNWCLineItem(dealId: string, nwcId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({
      itemId,
      body,
    }: {
      itemId: string;
      body: { classification: NWCClassification };
    }) => {
      const { data } = await api.put(
        `/deals/${dealId}/nwc/${nwcId}/line-items/${itemId}`,
        body
      );
      return data as NWCLineItemRead;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["nwc", dealId] });
    },
  });
}
