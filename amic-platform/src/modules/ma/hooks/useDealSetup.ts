import { useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { maApi } from "@/api/maClient";
import type {
  DealSetupRequest,
  DealSetupPreview,
  DealSetupConfirm,
  DealSetupResult,
} from "@/modules/ma/types/dealSetup";

/** 자연어 설명 → AI 미리보기 */
export function useDealSetupFromText() {
  return useMutation<DealSetupPreview, Error, DealSetupRequest>({
    mutationFn: async (body) => {
      const { data } = await maApi.post("/transactions/ai-setup", body);
      return data;
    },
    onError: () => {
      toast.error("AI 분석에 실패했습니다. 다시 시도해 주세요.");
    },
  });
}

/** 엑셀 파일 → AI 미리보기 */
export function useDealSetupFromExcel() {
  return useMutation<DealSetupPreview, Error, File>({
    mutationFn: async (file) => {
      const formData = new FormData();
      formData.append("file", file);
      const { data } = await maApi.post(
        "/transactions/ai-setup/excel",
        formData,
        { headers: { "Content-Type": "multipart/form-data" } },
      );
      return data;
    },
    onError: () => {
      toast.error("엑셀 AI 분석에 실패했습니다. 다시 시도해 주세요.");
    },
  });
}

/** 미리보기 확인 → DB 저장 */
export function useConfirmDealSetup() {
  const qc = useQueryClient();
  return useMutation<DealSetupResult, Error, DealSetupConfirm>({
    mutationFn: async (body) => {
      const { data } = await maApi.post("/transactions/ai-setup/confirm", body);
      return data;
    },
    onSuccess: (result) => {
      qc.invalidateQueries({ queryKey: ["ma", "transactions"] });
      toast.success(
        `거래가 생성되었습니다 (DD ${result.dd_checklist_count}건, 타임라인 ${result.timeline_count}건)`,
      );
    },
    onError: () => {
      toast.error("거래 생성에 실패했습니다.");
    },
  });
}
