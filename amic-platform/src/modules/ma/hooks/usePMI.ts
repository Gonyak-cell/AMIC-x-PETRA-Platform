import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { maApi } from "@/api/maClient";
import type {
  PMITask,
  PMITaskCreate,
  PMITaskUpdate,
  PMISummary,
} from "@/modules/ma/types/pmi";

export function usePMITasks(
  txnId: string,
  category?: string,
  priority?: string,
  active = true,
) {
  return useQuery<PMITask[]>({
    queryKey: ["ma", "transactions", txnId, "pmi", { category, priority }],
    queryFn: async () => {
      const params: Record<string, string> = {};
      if (category) params.category = category;
      if (priority) params.priority = priority;
      const { data } = await maApi.get(`/transactions/${txnId}/pmi`, {
        params,
      });
      return data;
    },
    enabled: !!txnId && active,
  });
}

export function usePMISummary(txnId: string, active = true) {
  return useQuery<PMISummary>({
    queryKey: ["ma", "transactions", txnId, "pmi", "summary"],
    queryFn: async () => {
      const { data } = await maApi.get(`/transactions/${txnId}/pmi/summary`);
      return data;
    },
    enabled: !!txnId && active,
  });
}

export function useCreatePMITask(txnId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: PMITaskCreate) => {
      const { data } = await maApi.post(`/transactions/${txnId}/pmi`, body);
      return data as PMITask;
    },
    onSuccess: () => {
      qc.invalidateQueries({
        queryKey: ["ma", "transactions", txnId, "pmi"],
      });
      toast.success("PMI 태스크가 생성되었습니다.");
    },
    onError: () => {
      toast.error("PMI 태스크 생성에 실패했습니다.");
    },
  });
}

export function useUpdatePMITask(txnId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({
      taskId,
      body,
    }: {
      taskId: string;
      body: PMITaskUpdate;
    }) => {
      const { data } = await maApi.patch(
        `/transactions/${txnId}/pmi/${taskId}`,
        body,
      );
      return data as PMITask;
    },
    onSuccess: () => {
      qc.invalidateQueries({
        queryKey: ["ma", "transactions", txnId, "pmi"],
      });
      toast.success("PMI 태스크가 수정되었습니다.");
    },
    onError: () => {
      toast.error("PMI 태스크 수정에 실패했습니다.");
    },
  });
}

export function useDeletePMITask(txnId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (taskId: string) => {
      await maApi.delete(`/transactions/${txnId}/pmi/${taskId}`);
    },
    onSuccess: () => {
      qc.invalidateQueries({
        queryKey: ["ma", "transactions", txnId, "pmi"],
      });
      toast.success("PMI 태스크가 삭제되었습니다.");
    },
    onError: () => {
      toast.error("PMI 태스크 삭제에 실패했습니다.");
    },
  });
}
