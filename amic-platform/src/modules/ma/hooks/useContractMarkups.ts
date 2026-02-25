import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { maApi } from "@/api/maClient";
import type {
  ContractMarkup,
  ContractMarkupListResponse,
} from "@/modules/ma/types/contract_markup";

const KEY = (txnId: string, contractId: string) => [
  "ma", "transactions", txnId, "contracts", contractId, "markups",
];

export function useContractMarkups(txnId: string, contractId: string) {
  return useQuery<ContractMarkupListResponse>({
    queryKey: KEY(txnId, contractId),
    queryFn: async () => {
      const { data } = await maApi.get(
        `/transactions/${txnId}/contracts/${contractId}/markups`,
      );
      return data;
    },
    enabled: !!txnId && !!contractId,
  });
}

export function useCreateContractMarkup(txnId: string, contractId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (formData: FormData) => {
      const { data } = await maApi.post(
        `/transactions/${txnId}/contracts/${contractId}/markups`,
        formData,
        { headers: { "Content-Type": "multipart/form-data" } },
      );
      return data as ContractMarkup;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: KEY(txnId, contractId) });
      toast.success("마크업 버전이 업로드되었습니다.");
    },
    onError: () => {
      toast.error("마크업 업로드에 실패했습니다.");
    },
  });
}

export function useDeleteContractMarkup(txnId: string, contractId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (markupId: string) => {
      await maApi.delete(
        `/transactions/${txnId}/contracts/${contractId}/markups/${markupId}`,
      );
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: KEY(txnId, contractId) });
      toast.success("마크업 버전이 삭제되었습니다.");
    },
    onError: () => {
      toast.error("마크업 삭제에 실패했습니다.");
    },
  });
}

/** 마크업 파일 다운로드 URL 반환 */
export function getMarkupDownloadUrl(txnId: string, contractId: string, markupId: string): string {
  return `/api/v1/transactions/${txnId}/contracts/${contractId}/markups/${markupId}/download`;
}
