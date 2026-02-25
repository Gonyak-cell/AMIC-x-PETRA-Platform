import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { maApi } from "@/api/maClient";
import type {
  IndustryOption,
  PermitAnalysis,
  PermitAnalyzeRequest,
  PermitRequirement,
  PermitRequirementUpdate,
} from "@/modules/ma/types/permit";

export function usePermitAnalysis(txnId: string) {
  return useQuery<PermitAnalysis | null>({
    queryKey: ["ma", "transactions", txnId, "permits", "analysis"],
    queryFn: async () => {
      const { data } = await maApi.get(
        `/transactions/${txnId}/permits/analysis`,
      );
      return data;
    },
    enabled: !!txnId,
  });
}

export function usePermitRequirements(txnId: string) {
  return useQuery<PermitRequirement[]>({
    queryKey: ["ma", "transactions", txnId, "permits", "requirements"],
    queryFn: async () => {
      const { data } = await maApi.get(
        `/transactions/${txnId}/permits/requirements`,
      );
      return data;
    },
    enabled: !!txnId,
  });
}

export function usePermitIndustries() {
  return useQuery<IndustryOption[]>({
    queryKey: ["ma", "permits", "kb", "industries"],
    queryFn: async () => {
      const { data } = await maApi.get("/permits/kb/industries");
      return data;
    },
    staleTime: Infinity,
  });
}

export function useAnalyzePermits(txnId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: PermitAnalyzeRequest) => {
      const { data } = await maApi.post(
        `/transactions/${txnId}/permits/analyze`,
        body,
      );
      return data as PermitAnalysis;
    },
    onSuccess: () => {
      qc.invalidateQueries({
        queryKey: ["ma", "transactions", txnId, "permits"],
      });
      toast.success("인허가 분석이 완료되었습니다.");
    },
    onError: () => {
      toast.error("인허가 분석에 실패했습니다.");
    },
  });
}

export function useReanalyzePermits(txnId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: PermitAnalyzeRequest) => {
      const { data } = await maApi.post(
        `/transactions/${txnId}/permits/analysis/reanalyze`,
        body,
      );
      return data as PermitAnalysis;
    },
    onSuccess: () => {
      qc.invalidateQueries({
        queryKey: ["ma", "transactions", txnId, "permits"],
      });
      toast.success("인허가 재분석이 완료되었습니다.");
    },
    onError: () => {
      toast.error("인허가 재분석에 실패했습니다.");
    },
  });
}

export function useUpdatePermitRequirement(txnId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({
      reqId,
      body,
    }: {
      reqId: string;
      body: PermitRequirementUpdate;
    }) => {
      const { data } = await maApi.patch(
        `/transactions/${txnId}/permits/requirements/${reqId}`,
        body,
      );
      return data as PermitRequirement;
    },
    onSuccess: () => {
      qc.invalidateQueries({
        queryKey: ["ma", "transactions", txnId, "permits", "requirements"],
      });
      toast.success("인허가 요건이 수정되었습니다.");
    },
    onError: () => {
      toast.error("인허가 요건 수정에 실패했습니다.");
    },
  });
}
