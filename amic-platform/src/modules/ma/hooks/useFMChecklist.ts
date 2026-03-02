import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { maApi } from "@/api/maClient";
import type {
  FMChecklist,
  FMChecklistItem,
  FMChecklistItemUpdate,
  FMChecklistBulkItem,
} from "@/modules/ma/types/financial_model";

const QK = (txnId: string, fmId: string) => [
  "ma",
  "transactions",
  txnId,
  "financial-models",
  fmId,
  "checklist",
];

export function useFMChecklist(txnId: string, fmId: string) {
  return useQuery<FMChecklist>({
    queryKey: QK(txnId, fmId),
    queryFn: async () => {
      const { data } = await maApi.get<FMChecklist>(
        `/transactions/${txnId}/financial-models/${fmId}/checklist`,
      );
      return data;
    },
    enabled: !!txnId && !!fmId,
    retry: false,
  });
}

export function useUpdateFMChecklistItem(txnId: string, fmId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({
      itemId,
      update,
    }: {
      itemId: string;
      update: FMChecklistItemUpdate;
    }) => {
      const { data } = await maApi.put<FMChecklistItem>(
        `/transactions/${txnId}/financial-models/${fmId}/checklist/items/${itemId}`,
        update,
      );
      return data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: QK(txnId, fmId) });
    },
    onError: () => {
      toast.error("체크리스트 항목 수정에 실패했습니다.");
    },
  });
}

export function useBulkUpdateFMItems(txnId: string, fmId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({
      checklistId,
      items,
    }: {
      checklistId: string;
      items: FMChecklistBulkItem[];
    }) => {
      const { data } = await maApi.put<FMChecklistItem[]>(
        `/transactions/${txnId}/financial-models/${fmId}/checklist/${checklistId}/bulk-update`,
        { items },
      );
      return data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: QK(txnId, fmId) });
      toast.success("일괄 수정이 반영되었습니다.");
    },
    onError: () => {
      toast.error("일괄 수정에 실패했습니다.");
    },
  });
}

export function useFinalizeFMChecklist(txnId: string, fmId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({
      checklistId,
      notes,
    }: {
      checklistId: string;
      notes?: string;
    }) => {
      const { data } = await maApi.post<FMChecklist>(
        `/transactions/${txnId}/financial-models/${fmId}/checklist/${checklistId}/finalize`,
        { notes },
      );
      return data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: QK(txnId, fmId) });
      // 모델 목록도 갱신 (status 변경됨)
      qc.invalidateQueries({
        queryKey: ["ma", "transactions", txnId, "financial-models"],
      });
      toast.success("체크리스트 Finalize 완료 — 최종 Excel 생성을 시작합니다.");
    },
    onError: () => {
      toast.error("Finalize에 실패했습니다.");
    },
  });
}
