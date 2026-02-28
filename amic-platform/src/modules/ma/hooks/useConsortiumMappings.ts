import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { maApi } from "@/api/maClient";
import type {
  ConsortiumMapping,
  ConsortiumMappingCreate,
  ConsortiumMappingUpdate,
} from "@/modules/ma/types/consortium";

const KEY = (txnId: string) => ["ma", "transactions", txnId, "consortium"];

export function useConsortiumMappings(txnId: string) {
  return useQuery<ConsortiumMapping[]>({
    queryKey: KEY(txnId),
    queryFn: async () => {
      const { data } = await maApi.get(`/transactions/${txnId}/consortium/`);
      return data;
    },
    enabled: !!txnId,
  });
}

export function useCreateConsortiumMapping(txnId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: ConsortiumMappingCreate) => {
      const { data } = await maApi.post(
        `/transactions/${txnId}/consortium/`,
        body,
      );
      return data as ConsortiumMapping;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: KEY(txnId) });
      toast.success("컨소시엄 매핑이 생성되었습니다.");
    },
    onError: () => {
      toast.error("컨소시엄 매핑 생성에 실패했습니다.");
    },
  });
}

export function useUpdateConsortiumMapping(txnId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({
      mappingId,
      body,
    }: {
      mappingId: string;
      body: ConsortiumMappingUpdate;
    }) => {
      const { data } = await maApi.patch(
        `/transactions/${txnId}/consortium/${mappingId}`,
        body,
      );
      return data as ConsortiumMapping;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: KEY(txnId) });
      toast.success("컨소시엄 매핑이 수정되었습니다.");
    },
    onError: () => {
      toast.error("컨소시엄 매핑 수정에 실패했습니다.");
    },
  });
}

export function useDeleteConsortiumMapping(txnId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (mappingId: string) => {
      await maApi.delete(`/transactions/${txnId}/consortium/${mappingId}`);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: KEY(txnId) });
      toast.success("컨소시엄 매핑이 삭제되었습니다.");
    },
    onError: () => {
      toast.error("컨소시엄 매핑 삭제에 실패했습니다.");
    },
  });
}
