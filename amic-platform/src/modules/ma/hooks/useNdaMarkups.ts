import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { maApi } from "@/api/maClient";
import type {
  NdaMarkup,
  NdaMarkupListResponse,
} from "@/modules/ma/types/nda_markup";

const KEY = (txnId: string, ndaId: string) => [
  "ma",
  "transactions",
  txnId,
  "ndas",
  ndaId,
  "markups",
];

export function useNdaMarkups(txnId: string, ndaId: string) {
  return useQuery<NdaMarkupListResponse>({
    queryKey: KEY(txnId, ndaId),
    queryFn: async () => {
      const { data } = await maApi.get(
        `/transactions/${txnId}/ndas/${ndaId}/markups`,
      );
      return data;
    },
    enabled: !!txnId && !!ndaId,
  });
}

export function useCreateNdaMarkup(txnId: string, ndaId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (formData: FormData) => {
      const { data } = await maApi.post(
        `/transactions/${txnId}/ndas/${ndaId}/markups`,
        formData,
        { headers: { "Content-Type": "multipart/form-data" } },
      );
      return data as NdaMarkup;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: KEY(txnId, ndaId) });
      toast.success("NDA 마크업 버전이 업로드되었습니다.");
    },
    onError: () => {
      toast.error("NDA 마크업 업로드에 실패했습니다.");
    },
  });
}

export function useDeleteNdaMarkup(txnId: string, ndaId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (markupId: string) => {
      await maApi.delete(
        `/transactions/${txnId}/ndas/${ndaId}/markups/${markupId}`,
      );
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: KEY(txnId, ndaId) });
      toast.success("NDA 마크업 버전이 삭제되었습니다.");
    },
    onError: () => {
      toast.error("NDA 마크업 삭제에 실패했습니다.");
    },
  });
}

export function useGenerateNdaRedline(txnId: string, ndaId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({
      markupId,
      baseMarkupId,
      partySide,
    }: {
      markupId: string;
      baseMarkupId?: string;
      partySide?: string;
    }) => {
      const formData = new FormData();
      if (baseMarkupId) formData.append("base_markup_id", baseMarkupId);
      formData.append("party_side", partySide ?? "SELL");

      const response = await maApi.post(
        `/transactions/${txnId}/ndas/${ndaId}/markups/${markupId}/generate-redline`,
        formData,
        {
          headers: { "Content-Type": "multipart/form-data" },
          responseType: "blob",
        },
      );

      const issuesCount = response.headers["x-issues-count"];
      const blob = new Blob([response.data], {
        type: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
      });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download =
        response.headers["content-disposition"]?.match(
          /filename="(.+)"/,
        )?.[1] ?? "NDA_redline.docx";
      a.click();
      URL.revokeObjectURL(url);

      return { issuesCount: issuesCount ? Number(issuesCount) : 0 };
    },
    onSuccess: (result) => {
      qc.invalidateQueries({ queryKey: KEY(txnId, ndaId) });
      toast.success(`Redline 생성 완료 (${result.issuesCount}건 이슈 검출)`);
    },
    onError: () => {
      toast.error("Redline 생성에 실패했습니다.");
    },
  });
}

export function getNdaMarkupDownloadUrl(
  txnId: string,
  ndaId: string,
  markupId: string,
): string {
  return `/api/v1/transactions/${txnId}/ndas/${ndaId}/markups/${markupId}/download`;
}
