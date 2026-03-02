import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { maApi } from "@/api/maClient";
import type {
  Contract,
  ContractCreate,
  ContractUpdate,
  ContractVersion,
  ContractVersionCreate,
  ContractSummary,
  AIAnalysisResult,
} from "@/modules/ma/types/contract";

export function useContracts(txnId: string, active = true) {
  return useQuery<Contract[]>({
    queryKey: ["ma", "transactions", txnId, "contracts"],
    queryFn: async () => {
      const { data } = await maApi.get(`/transactions/${txnId}/contracts`);
      return data;
    },
    enabled: !!txnId && active,
  });
}

export function useContractSummary(txnId: string, active = true) {
  return useQuery<ContractSummary>({
    queryKey: ["ma", "transactions", txnId, "contracts", "summary"],
    queryFn: async () => {
      const { data } = await maApi.get(
        `/transactions/${txnId}/contracts/summary`,
      );
      return data;
    },
    enabled: !!txnId && active,
  });
}

export function useContractVersions(txnId: string, contractId: string) {
  return useQuery<ContractVersion[]>({
    queryKey: [
      "ma",
      "transactions",
      txnId,
      "contracts",
      contractId,
      "versions",
    ],
    queryFn: async () => {
      const { data } = await maApi.get(
        `/transactions/${txnId}/contracts/${contractId}/versions`,
      );
      return data;
    },
    enabled: !!txnId && !!contractId,
  });
}

export function useCreateContract(txnId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: ContractCreate) => {
      const { data } = await maApi.post(
        `/transactions/${txnId}/contracts`,
        body,
      );
      return data as Contract;
    },
    onSuccess: () => {
      qc.invalidateQueries({
        queryKey: ["ma", "transactions", txnId, "contracts"],
      });
      toast.success("계약서가 생성되었습니다.");
    },
    onError: () => {
      toast.error("계약서 생성에 실패했습니다.");
    },
  });
}

export function useUpdateContract(txnId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({
      contractId,
      body,
    }: {
      contractId: string;
      body: ContractUpdate;
    }) => {
      const { data } = await maApi.patch(
        `/transactions/${txnId}/contracts/${contractId}`,
        body,
      );
      return data as Contract;
    },
    onSuccess: () => {
      qc.invalidateQueries({
        queryKey: ["ma", "transactions", txnId, "contracts"],
      });
      toast.success("계약서가 수정되었습니다.");
    },
    onError: () => {
      toast.error("계약서 수정에 실패했습니다.");
    },
  });
}

export function useDeleteContract(txnId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (contractId: string) => {
      await maApi.delete(`/transactions/${txnId}/contracts/${contractId}`);
    },
    onSuccess: () => {
      qc.invalidateQueries({
        queryKey: ["ma", "transactions", txnId, "contracts"],
      });
      toast.success("계약서가 삭제되었습니다.");
    },
    onError: () => {
      toast.error("계약서 삭제에 실패했습니다.");
    },
  });
}

export function useCreateContractVersion(txnId: string, contractId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: ContractVersionCreate) => {
      const { data } = await maApi.post(
        `/transactions/${txnId}/contracts/${contractId}/versions`,
        body,
      );
      return data as ContractVersion;
    },
    onSuccess: () => {
      qc.invalidateQueries({
        queryKey: ["ma", "transactions", txnId, "contracts"],
      });
      toast.success("새 버전이 추가되었습니다.");
    },
    onError: () => {
      toast.error("버전 추가에 실패했습니다.");
    },
  });
}

export function useAnalyzeContract(txnId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (contractId: string) => {
      const { data } = await maApi.post(
        `/transactions/${txnId}/contracts/${contractId}/analyze`,
      );
      return data as AIAnalysisResult;
    },
    onSuccess: () => {
      qc.invalidateQueries({
        queryKey: ["ma", "transactions", txnId, "contracts"],
      });
      toast.info("AI 분석이 요청되었습니다.");
    },
    onError: () => {
      toast.error("AI 분석 요청에 실패했습니다.");
    },
  });
}
