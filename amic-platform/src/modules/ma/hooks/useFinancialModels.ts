import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { maApi } from "@/api/maClient";
import type {
  FinancialModel,
  FinancialModelCreate,
} from "@/modules/ma/types/financial_model";
import { FM_IN_PROGRESS_STATUSES } from "@/modules/ma/types/financial_model";

const QK = (txnId: string) => ["ma", "transactions", txnId, "financial-models"];

export function useFinancialModels(txnId: string) {
  return useQuery<FinancialModel[]>({
    queryKey: QK(txnId),
    queryFn: async () => {
      const { data } = await maApi.get(
        `/transactions/${txnId}/financial-models`,
      );
      return data;
    },
    enabled: !!txnId,
    // GENERATING / FINALIZING 상태 모델이 있으면 5초마다 폴링
    refetchInterval: (query) => {
      const items = query.state.data ?? [];
      const hasInProgress = items.some((m) =>
        FM_IN_PROGRESS_STATUSES.includes(m.status),
      );
      return hasInProgress ? 5000 : false;
    },
  });
}

export function useCreateFinancialModel(txnId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: FinancialModelCreate) => {
      const { data } = await maApi.post(
        `/transactions/${txnId}/financial-models`,
        body,
      );
      return data as FinancialModel;
    },
    onSuccess: (data) => {
      qc.invalidateQueries({ queryKey: QK(txnId) });
      toast.success(`${data.title} 재무모델 생성을 시작했습니다.`);
    },
    onError: () => {
      toast.error("재무모델 생성에 실패했습니다.");
    },
  });
}

export function useRegenerateFinancialModel(txnId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (fmId: string) => {
      const { data } = await maApi.post(
        `/transactions/${txnId}/financial-models/${fmId}/regenerate`,
      );
      return data as FinancialModel;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: QK(txnId) });
      toast.success("재생성을 시작했습니다.");
    },
    onError: () => {
      toast.error("재생성에 실패했습니다.");
    },
  });
}

export function useDeleteFinancialModel(txnId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (fmId: string) => {
      await maApi.delete(
        `/transactions/${txnId}/financial-models/${fmId}`,
      );
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: QK(txnId) });
      toast.success("재무모델이 삭제되었습니다.");
    },
    onError: () => {
      toast.error("삭제에 실패했습니다.");
    },
  });
}

/** Excel 다운로드 URL 반환 (FileResponse는 링크 직접 열기) */
export function getFMDownloadUrl(txnId: string, fmId: string): string {
  return `/api/ma/transactions/${txnId}/financial-models/${fmId}/download`;
}
