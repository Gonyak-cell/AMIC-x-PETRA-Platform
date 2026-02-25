import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { fddApi } from "@/api/fddClient";
import type { Deal, DealCreate } from "@/modules/fdd/types/deal";

export function useDeals(params?: { skip?: number; limit?: number }) {
  return useQuery<Deal[]>({
    queryKey: ["fdd", "deals", params],
    queryFn: async () => {
      const { data } = await fddApi.get("/deals", { params });
      // Backend returns { items, total, skip, limit } — extract the array
      return Array.isArray(data) ? data : data.items ?? [];
    },
  });
}

export function useCreateDeal() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (body: DealCreate) => {
      const { data } = await fddApi.post("/deals", body);
      return data as Deal;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["fdd", "deals"] });
      toast.success("딜이 성공적으로 생성되었습니다.");
    },
    onError: (error: Error) => {
      console.error("useCreateDeal failed:", error);
      toast.error("딜 생성 중 오류가 발생했습니다.");
    },
  });
}

export function useDeal(dealId: string) {
  return useQuery<Deal>({
    queryKey: ["fdd", "deals", dealId],
    queryFn: async () => {
      const { data } = await fddApi.get(`/deals/${dealId}`);
      return data;
    },
    enabled: !!dealId,
  });
}

export function useUpdateDeal(dealId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (body: Partial<DealCreate>) => {
      const { data } = await fddApi.put(`/deals/${dealId}`, body);
      return data as Deal;
    },
    onMutate: async (body) => {
      await queryClient.cancelQueries({ queryKey: ["fdd", "deals", dealId] });
      const previous = queryClient.getQueryData<Deal>(["fdd", "deals", dealId]);
      if (previous) {
        queryClient.setQueryData<Deal>(["fdd", "deals", dealId], {
          ...previous,
          ...body,
        });
      }
      return { previous };
    },
    onError: (error, _body, context) => {
      console.error("useUpdateDeal failed:", error);
      toast.error("딜 수정 중 오류가 발생했습니다.");
      if (context?.previous) {
        queryClient.setQueryData(["fdd", "deals", dealId], context.previous);
      }
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ["fdd", "deals"] });
      queryClient.invalidateQueries({ queryKey: ["fdd", "deals", dealId] });
    },
  });
}
