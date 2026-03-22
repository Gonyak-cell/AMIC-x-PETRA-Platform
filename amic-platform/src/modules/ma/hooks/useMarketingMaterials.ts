import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { maApi } from "@/api/maClient";
import type {
  MarketingMaterial,
  MarketingMaterialCreate,
  DistributionUpdate,
  MarketingMaterialSourceRouting,
  MarketingDocType,
} from "@/modules/ma/types/marketing_material";

const QK = (txnId: string) => [
  "ma",
  "transactions",
  txnId,
  "marketing-materials",
];
const sourceRoutingPreviewQK = (txnId: string, docType: MarketingDocType) =>
  [...QK(txnId), "source-routing-preview", docType] as const;

export function useMarketingMaterials(txnId: string, active = true) {
  return useQuery<MarketingMaterial[]>({
    queryKey: QK(txnId),
    queryFn: async () => {
      const { data } = await maApi.get(
        `/transactions/${txnId}/marketing-materials`,
      );
      return data;
    },
    enabled: !!txnId && active,
    // GENERATING 상태 자료가 있으면 5초마다 폴링
    refetchInterval: (query) => {
      const items = query.state.data ?? [];
      const hasGenerating = items.some((m) => m.status === "GENERATING");
      return hasGenerating ? 5000 : false;
    },
  });
}

export function useMarketingMaterialSourceRoutingPreview(
  txnId: string,
  docType: MarketingDocType,
  active = true,
) {
  return useQuery<MarketingMaterialSourceRouting>({
    queryKey: sourceRoutingPreviewQK(txnId, docType),
    queryFn: async () => {
      const { data } = await maApi.get(
        `/transactions/${txnId}/marketing-materials/source-routing-preview`,
        {
          params: { doc_type: docType },
        },
      );
      return data;
    },
    enabled: !!txnId && active,
    staleTime: 30_000,
  });
}

export function useCreateMarketingMaterial(txnId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: MarketingMaterialCreate) => {
      const { data } = await maApi.post(
        `/transactions/${txnId}/marketing-materials`,
        body,
      );
      return data as MarketingMaterial;
    },
    onSuccess: (data) => {
      qc.invalidateQueries({ queryKey: QK(txnId) });
      const label =
        data.doc_type === "TM"
          ? "Teaser Memo"
          : data.doc_type === "DM"
            ? "Discussion Memo"
            : "Information Memo";
      toast.success(
        `${label} 생성을 시작했습니다. 완료 후 다운로드 가능합니다.`,
      );
    },
    onError: () => {
      toast.error("마케팅 자료 생성에 실패했습니다.");
    },
  });
}

export function useRegenerateMarketingMaterial(txnId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (matId: string) => {
      const { data } = await maApi.post(
        `/transactions/${txnId}/marketing-materials/${matId}/regenerate`,
      );
      return data as MarketingMaterial;
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

export function useUpdateDistribution(txnId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({
      matId,
      body,
    }: {
      matId: string;
      body: DistributionUpdate;
    }) => {
      const { data } = await maApi.put(
        `/transactions/${txnId}/marketing-materials/${matId}/distribute`,
        body,
      );
      return data as MarketingMaterial;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: QK(txnId) });
      toast.success("배포 기록이 업데이트되었습니다.");
    },
    onError: () => {
      toast.error("배포 기록 업데이트에 실패했습니다.");
    },
  });
}

export function useDeleteMarketingMaterial(txnId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (matId: string) => {
      await maApi.delete(`/transactions/${txnId}/marketing-materials/${matId}`);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: QK(txnId) });
      toast.success("마케팅 자료가 삭제되었습니다.");
    },
    onError: () => {
      toast.error("삭제에 실패했습니다.");
    },
  });
}

/** PPTX 다운로드 URL 반환 (FileResponse는 링크 직접 열기)
 * Vite 개발 프록시: /api/ma → http://localhost:8003
 */
export function getDownloadUrl(txnId: string, matId: string): string {
  return `/api/ma/transactions/${txnId}/marketing-materials/${matId}/download`;
}
