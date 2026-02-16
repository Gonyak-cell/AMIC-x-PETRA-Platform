import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import api from "@/api/client";
import type {
  QoECalculationRead,
  AdjustmentItemRead,
} from "@/modules/fdd/types/qoe";

export function useQoECalculations(dealId: string) {
  return useQuery<QoECalculationRead[]>({
    queryKey: ["fdd", "qoe", dealId],
    queryFn: async () => {
      const { data } = await api.get(`/deals/${dealId}/qoe`);
      return data;
    },
    enabled: !!dealId,
  });
}

export function useRunQoE(dealId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (body: { snapshot_id: string }) => {
      const { data } = await api.post(`/deals/${dealId}/qoe/calculate`, body);
      return data as QoECalculationRead;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["fdd", "qoe", dealId] });
    },
    onError: (error: Error) => {
      console.error("useRunQoE failed:", error);
    },
  });
}

export function useApproveAdjustment(dealId: string, calcId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({
      adjustmentId,
      body,
    }: {
      adjustmentId: string;
      body: { approved_by: string };
    }) => {
      const { data } = await api.post(
        `/deals/${dealId}/qoe/${calcId}/adjustments/${adjustmentId}/approve`,
        body
      );
      return data as AdjustmentItemRead;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["fdd", "qoe", dealId] });
    },
    onError: (error: Error) => {
      console.error("useApproveAdjustment failed:", error);
    },
  });
}

export function useRecalculateBridge(dealId: string, calcId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async () => {
      const { data } = await api.post(
        `/deals/${dealId}/qoe/${calcId}/recalculate`
      );
      return data as QoECalculationRead;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["fdd", "qoe", dealId] });
    },
    onError: (error: Error) => {
      console.error("useRecalculateBridge failed:", error);
    },
  });
}
