import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import api from "@/api/client";
import type { Deal, DealCreate } from "@/modules/fdd/types/deal";

export function useDeals() {
  return useQuery<Deal[]>({
    queryKey: ["deals"],
    queryFn: async () => {
      const { data } = await api.get("/deals");
      return data;
    },
  });
}

export function useCreateDeal() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (body: DealCreate) => {
      const { data } = await api.post("/deals", body);
      return data as Deal;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["deals"] });
    },
  });
}

export function useDeal(dealId: string) {
  return useQuery<Deal>({
    queryKey: ["deals", dealId],
    queryFn: async () => {
      const { data } = await api.get(`/deals/${dealId}`);
      return data;
    },
    enabled: !!dealId,
  });
}

export function useUpdateDeal(dealId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (body: Partial<DealCreate>) => {
      const { data } = await api.put(`/deals/${dealId}`, body);
      return data as Deal;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["deals"] });
      queryClient.invalidateQueries({ queryKey: ["deals", dealId] });
    },
  });
}
