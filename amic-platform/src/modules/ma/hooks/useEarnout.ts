import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { maApi } from "@/api/maClient";
import type {
  EarnoutMilestone,
  EarnoutCreate,
  EarnoutUpdate,
  EarnoutSummary,
} from "@/modules/ma/types/earnout";

export function useEarnoutMilestones(txnId: string) {
  return useQuery<EarnoutMilestone[]>({
    queryKey: ["ma", "transactions", txnId, "earnout"],
    queryFn: async () => {
      const { data } = await maApi.get(`/transactions/${txnId}/earnout`);
      return data;
    },
    enabled: !!txnId,
  });
}

export function useEarnoutSummary(txnId: string) {
  return useQuery<EarnoutSummary>({
    queryKey: ["ma", "transactions", txnId, "earnout", "summary"],
    queryFn: async () => {
      const { data } = await maApi.get(
        `/transactions/${txnId}/earnout/summary`,
      );
      return data;
    },
    enabled: !!txnId,
  });
}

export function useCreateEarnout(txnId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: EarnoutCreate) => {
      const { data } = await maApi.post(
        `/transactions/${txnId}/earnout`,
        body,
      );
      return data as EarnoutMilestone;
    },
    onSuccess: () => {
      qc.invalidateQueries({
        queryKey: ["ma", "transactions", txnId, "earnout"],
      });
      toast.success("어닝아웃 마일스톤이 생성되었습니다.");
    },
    onError: () => {
      toast.error("어닝아웃 마일스톤 생성에 실패했습니다.");
    },
  });
}

export function useUpdateEarnout(txnId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({
      milestoneId,
      body,
    }: {
      milestoneId: string;
      body: EarnoutUpdate;
    }) => {
      const { data } = await maApi.patch(
        `/transactions/${txnId}/earnout/${milestoneId}`,
        body,
      );
      return data as EarnoutMilestone;
    },
    onSuccess: () => {
      qc.invalidateQueries({
        queryKey: ["ma", "transactions", txnId, "earnout"],
      });
      toast.success("어닝아웃 마일스톤이 수정되었습니다.");
    },
    onError: () => {
      toast.error("어닝아웃 마일스톤 수정에 실패했습니다.");
    },
  });
}

export function useDeleteEarnout(txnId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (milestoneId: string) => {
      await maApi.delete(`/transactions/${txnId}/earnout/${milestoneId}`);
    },
    onSuccess: () => {
      qc.invalidateQueries({
        queryKey: ["ma", "transactions", txnId, "earnout"],
      });
      toast.success("어닝아웃 마일스톤이 삭제되었습니다.");
    },
    onError: () => {
      toast.error("어닝아웃 마일스톤 삭제에 실패했습니다.");
    },
  });
}
