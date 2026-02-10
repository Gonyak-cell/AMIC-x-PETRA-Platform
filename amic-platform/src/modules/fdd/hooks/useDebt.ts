import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import api from "@/api/client";
import type {
  NetDebtBridgeSummary,
  DebtItemRead,
  NetDebtCalculationRead,
  DebtItemCreate,
} from "@/modules/fdd/types/debt";

export function useDebtCalculations(dealId: string) {
  return useQuery<NetDebtCalculationRead[]>({
    queryKey: ["debt", dealId],
    queryFn: async () => {
      const { data } = await api.get(`/deals/${dealId}/debt`);
      return data;
    },
    enabled: !!dealId,
  });
}

export function useRunDebt(dealId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (body: {
      snapshot_id: string;
      include_lease_liabilities?: boolean;
      include_deferred_revenue?: boolean;
    }) => {
      const { data } = await api.post(`/deals/${dealId}/debt/run`, body);
      return data as NetDebtCalculationRead;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["debt", dealId] });
    },
  });
}

export function useDebtBridge(dealId: string, calcId: string) {
  return useQuery<NetDebtBridgeSummary>({
    queryKey: ["debt", dealId, calcId, "bridge"],
    queryFn: async () => {
      const { data } = await api.get(
        `/deals/${dealId}/debt/${calcId}/bridge`
      );
      return data;
    },
    enabled: !!dealId && !!calcId,
  });
}

export function useApproveDebtItem(dealId: string, calcId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({
      itemId,
      body,
    }: {
      itemId: string;
      body: { approved_by: string };
    }) => {
      const { data } = await api.put(
        `/deals/${dealId}/debt/${calcId}/items/${itemId}/approve`,
        body
      );
      return data as DebtItemRead;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["debt", dealId] });
    },
  });
}

export function useRecalculateDebt(dealId: string, calcId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async () => {
      const { data } = await api.post(
        `/deals/${dealId}/debt/${calcId}/recalculate`,
        {}
      );
      return data as NetDebtCalculationRead;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["debt", dealId] });
    },
  });
}

export function useAddDebtItem(dealId: string, calcId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (body: DebtItemCreate) => {
      const { data } = await api.post(
        `/deals/${dealId}/debt/${calcId}/items`,
        body
      );
      return data as DebtItemRead;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["debt", dealId] });
    },
  });
}
