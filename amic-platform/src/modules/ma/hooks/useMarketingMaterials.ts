import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

import { maApi } from "@/api/maClient";
import type {
  DistributionUpdate,
  MarketingDocType,
  MarketingMaterial,
  MarketingMaterialCreate,
  MarketingMaterialSourceRouting,
  UploadedMarketingMaterialInput,
} from "@/modules/ma/types/marketing_material";
import {
  buildUploadErrorMessage,
  DEV_LOCAL_AUTH_ENABLED,
  DEV_MA_PROXY_TARGET,
} from "./uploadErrors";

const QK = (txnId: string) => [
  "ma",
  "transactions",
  txnId,
  "marketing-materials",
];

const sourceRoutingPreviewQK = (txnId: string, docType: MarketingDocType) =>
  [...QK(txnId), "source-routing-preview", docType] as const;

function getMarketingMaterialLabel(docType: MarketingDocType) {
  switch (docType) {
    case "TM":
      return "Teaser Memo";
    case "DM":
      return "Discussion Memo";
    case "IM":
    default:
      return "Information Memo";
  }
}

function getUploadedMarketingMaterialLabel(docType: MarketingDocType) {
  switch (docType) {
    case "TM":
      return "Teaser";
    case "DM":
      return "DM";
    case "IM":
    default:
      return "IM";
  }
}

export function buildMarketingMaterialUploadErrorMessage(
  err: unknown,
  docType: MarketingDocType,
  isLocalDev: boolean = DEV_LOCAL_AUTH_ENABLED,
  proxyTarget: string = DEV_MA_PROXY_TARGET,
) {
  const label = getUploadedMarketingMaterialLabel(docType);
  return buildUploadErrorMessage(err, {
    fallback: `${label} 업로드에 실패했습니다. 잠시 후 다시 시도해 주세요.`,
    isLocalDev,
    proxyTarget,
  });
}

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
    refetchInterval: (query) => {
      const items = query.state.data ?? [];
      const hasGenerating = items.some((item) => item.status === "GENERATING");
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
    onSuccess: (data, variables) => {
      qc.invalidateQueries({ queryKey: QK(txnId) });
      qc.invalidateQueries({
        queryKey: ["ma", "transactions", txnId, "short-list", "overview"],
      });

      const label = getMarketingMaterialLabel(data.doc_type);

      if (data.source_mode === "UPLOADED" || variables.attachment_id) {
        toast.success(`${label} 업로드가 등록되었습니다.`);
        return;
      }

      if (data.status === "FAILED") {
        toast.error(
          data.error_message ?? `${label} 생성 요청이 시작되지 못했습니다.`,
        );
        return;
      }

      toast.success(
        `${label} 생성이 시작되었습니다. 완료 후 다운로드 가능합니다.`,
      );
    },
    onError: () => {
      toast.error("마케팅 자료 생성에 실패했습니다.");
    },
  });
}

export function useUploadMarketingMaterial(txnId: string) {
  const qc = useQueryClient();

  return useMutation({
    mutationFn: async ({
      file,
      docType,
      title,
      projectCode,
      distributedTo,
      distributedAt,
    }: UploadedMarketingMaterialInput) => {
      const formData = new FormData();
      formData.append("file", file);
      formData.append("doc_type", docType);
      formData.append("title", title);

      if (projectCode) {
        formData.append("project_code", projectCode);
      }

      for (const recipient of distributedTo ?? []) {
        formData.append("distributed_to", recipient);
      }

      if (distributedAt) {
        formData.append("distributed_at", distributedAt);
      }

      const { data } = await maApi.post(
        `/transactions/${txnId}/marketing-materials/uploaded`,
        formData,
      );
      return data as MarketingMaterial;
    },
    onSuccess: (data) => {
      qc.invalidateQueries({ queryKey: QK(txnId) });
      qc.invalidateQueries({
        queryKey: ["ma", "transactions", txnId, "short-list", "overview"],
      });

      const label = getUploadedMarketingMaterialLabel(data.doc_type);
      toast.success(`${label} 업로드가 등록되었습니다.`);
    },
    onError: (err, variables) => {
      toast.error(
        buildMarketingMaterialUploadErrorMessage(err, variables.docType),
      );
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

export function getDownloadUrl(txnId: string, matId: string): string {
  return `/api/ma/transactions/${txnId}/marketing-materials/${matId}/download`;
}
