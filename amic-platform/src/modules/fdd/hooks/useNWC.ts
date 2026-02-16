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
    queryKey: ["fdd", "nwc", dealId],
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
      const { data } = await api.post(`/deals/${dealId}/nwc/calculate`, body);
      return data as NWCCalculationRead;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["fdd", "nwc", dealId] });
    },
    onError: (error: Error) => {
      console.error("useRunNWC failed:", error);
    },
  });
}

// NOTE: Uses POST inside useQuery intentionally — the /peg-simulate endpoint is a
// pure computation (no DB writes) that returns simulation results. POST is required
// because the BE accepts a body payload. Auto-refetch is disabled to prevent
// unintended re-computation on window focus or mount.
export function usePegSimulation(dealId: string, nwcId: string) {
  return useQuery<{ reference_nwc: string; scenarios: PegSimulationResult[] }>({
    queryKey: ["fdd", "nwc", dealId, nwcId, "peg-simulation"],
    queryFn: async () => {
      const { data } = await api.post(
        `/deals/${dealId}/nwc/${nwcId}/peg-simulate`
      );
      return data;
    },
    enabled: !!dealId && !!nwcId,
    refetchOnWindowFocus: false,
    refetchOnMount: false,
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
        `/deals/${dealId}/nwc/${nwcId}/recalculate-peg`,
        body
      );
      return data as NWCCalculationRead;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["fdd", "nwc", dealId] });
    },
    onError: (error: Error) => {
      console.error("useRecalculatePeg failed:", error);
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
        `/deals/${dealId}/nwc/${nwcId}/items/${itemId}`,
        body
      );
      return data as NWCLineItemRead;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["fdd", "nwc", dealId] });
    },
    onError: (error: Error) => {
      console.error("useUpdateNWCLineItem failed:", error);
    },
  });
}
