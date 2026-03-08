import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { isAxiosError } from "axios";
import { toast } from "sonner";
import { maApi } from "@/api/maClient";
import type {
  RFIItemV2,
  RFIItemListOut,
  RFIItemCreate,
  RFIItemUpdate,
  RFIItemBatchCreate,
  RFIThreadCreate,
  RFIThread,
  RFIAttachment,
  RFIAttachmentMapInput,
  RFIDashboardSummary,
  RFIExcelImportResult,
  RFIAutoGenerateRequest,
  RFIAutoGenerateResult,
  RFIReportPayload,
} from "@/modules/ma/types/rfi";

const KEY = "ma";
const rfiKeys = (txnId: string) => [KEY, "transactions", txnId, "rfi"];

function extractErrorDetail(err: unknown): string | undefined {
  if (isAxiosError<{ detail?: string }>(err)) {
    return err.response?.data?.detail;
  }
  return undefined;
}

/* ------------------------------------------------------------------ */
/*  Queries                                                           */
/* ------------------------------------------------------------------ */

interface RFIItemFilters {
  category?: string;
  status?: string;
  priority?: string;
  search?: string;
}

/** 1. RFI 항목 목록 */
export function useRFIItems(txnId: string, filters?: RFIItemFilters) {
  return useQuery<RFIItemListOut[]>({
    queryKey: [...rfiKeys(txnId), "items", filters ?? {}],
    queryFn: async () => {
      const params: Record<string, string> = {};
      if (filters?.category) params.category = filters.category;
      if (filters?.status) params.status = filters.status;
      if (filters?.priority) params.priority = filters.priority;
      if (filters?.search) params.search = filters.search;
      const { data } = await maApi.get<RFIItemListOut[]>(
        `/transactions/${txnId}/rfi/items`,
        { params },
      );
      return data;
    },
    enabled: !!txnId,
    staleTime: 10_000,
  });
}

/** 2. RFI 항목 상세 */
export function useRFIItem(txnId: string, itemId: string) {
  return useQuery<RFIItemV2>({
    queryKey: [...rfiKeys(txnId), "items", itemId],
    queryFn: async () => {
      const { data } = await maApi.get<RFIItemV2>(
        `/transactions/${txnId}/rfi/items/${itemId}`,
      );
      return data;
    },
    enabled: !!txnId && !!itemId,
  });
}

/** 3. RFI 대시보드 요약 */
export function useRFIDashboard(txnId: string) {
  return useQuery<RFIDashboardSummary>({
    queryKey: [...rfiKeys(txnId), "dashboard"],
    queryFn: async () => {
      const { data } = await maApi.get<RFIDashboardSummary>(
        `/transactions/${txnId}/rfi/dashboard`,
      );
      return data;
    },
    enabled: !!txnId,
    staleTime: 30_000,
  });
}

/** 9. RFI 스레드 목록 */
export function useRFIThreads(txnId: string, itemId: string) {
  return useQuery<RFIThread[]>({
    queryKey: [...rfiKeys(txnId), "items", itemId, "threads"],
    queryFn: async () => {
      const { data } = await maApi.get<RFIThread[]>(
        `/transactions/${txnId}/rfi/items/${itemId}/threads`,
      );
      return data;
    },
    enabled: !!txnId && !!itemId,
  });
}

/** 11. 미매핑 첨부파일 목록 */
export function useUnassignedAttachments(txnId: string) {
  return useQuery<RFIAttachment[]>({
    queryKey: [...rfiKeys(txnId), "attachments", "unassigned"],
    queryFn: async () => {
      const { data } = await maApi.get<RFIAttachment[]>(
        `/transactions/${txnId}/rfi/attachments/unassigned`,
      );
      return data;
    },
    enabled: !!txnId,
  });
}

/** 18. RFI 리포트 페이로드 */
export function useRFIReportPayload(txnId: string) {
  return useQuery<RFIReportPayload[]>({
    queryKey: [...rfiKeys(txnId), "report-payload"],
    queryFn: async () => {
      const { data } = await maApi.get<RFIReportPayload[]>(
        `/transactions/${txnId}/rfi/report-payload`,
      );
      return data;
    },
    enabled: !!txnId,
    staleTime: 60_000,
  });
}

/* ------------------------------------------------------------------ */
/*  Mutations                                                         */
/* ------------------------------------------------------------------ */

/** 4. RFI 항목 생성 */
export function useCreateRFIItem(txnId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: RFIItemCreate) => {
      const { data } = await maApi.post<RFIItemV2>(
        `/transactions/${txnId}/rfi/items`,
        body,
      );
      return data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: rfiKeys(txnId) });
      toast.success("질의가 생성되었습니다");
    },
    onError: (err) => {
      toast.error(extractErrorDetail(err) ?? "질의 생성에 실패했습니다");
    },
  });
}

/** 5. RFI 항목 일괄 생성 */
export function useBatchCreateRFIItems(txnId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: RFIItemBatchCreate) => {
      const { data } = await maApi.post<RFIItemV2[]>(
        `/transactions/${txnId}/rfi/items/batch`,
        body,
      );
      return data;
    },
    onSuccess: (items) => {
      qc.invalidateQueries({ queryKey: rfiKeys(txnId) });
      toast.success(`${items.length}개 질의가 생성되었습니다`);
    },
    onError: (err) => {
      toast.error(extractErrorDetail(err) ?? "일괄 생성에 실패했습니다");
    },
  });
}

/** 6. RFI 항목 수정 */
export function useUpdateRFIItem(txnId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({
      itemId,
      body,
    }: {
      itemId: string;
      body: RFIItemUpdate;
    }) => {
      const { data } = await maApi.patch<RFIItemV2>(
        `/transactions/${txnId}/rfi/items/${itemId}`,
        body,
      );
      return data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: rfiKeys(txnId) });
      toast.success("질의가 수정되었습니다");
    },
    onError: (err) => {
      toast.error(extractErrorDetail(err) ?? "질의 수정에 실패했습니다");
    },
  });
}

/** 7. RFI 항목 삭제 */
export function useDeleteRFIItem(txnId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (itemId: string) => {
      await maApi.delete(`/transactions/${txnId}/rfi/items/${itemId}`);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: rfiKeys(txnId) });
      toast.success("질의가 삭제되었습니다");
    },
    onError: (err) => {
      toast.error(extractErrorDetail(err) ?? "질의 삭제에 실패했습니다");
    },
  });
}

/** 8. RFI 항목 마감 */
export function useCloseRFIItem(txnId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({
      itemId,
      version,
    }: {
      itemId: string;
      version: number;
    }) => {
      const { data } = await maApi.patch<RFIItemV2>(
        `/transactions/${txnId}/rfi/items/${itemId}/close`,
        undefined,
        { params: { version } },
      );
      return data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: rfiKeys(txnId) });
      toast.success("질의가 마감되었습니다");
    },
    onError: (err) => {
      toast.error(extractErrorDetail(err) ?? "질의 마감에 실패했습니다");
    },
  });
}

/** 10. 스레드(답변) 생성 */
export function useCreateThread(txnId: string, itemId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: RFIThreadCreate) => {
      const { data } = await maApi.post<RFIThread>(
        `/transactions/${txnId}/rfi/items/${itemId}/threads`,
        body,
      );
      return data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: rfiKeys(txnId) });
      toast.success("답변이 등록되었습니다");
    },
    onError: (err) => {
      toast.error(extractErrorDetail(err) ?? "답변 등록에 실패했습니다");
    },
  });
}

/** 12. 첨부파일 업로드 */
export function useUploadAttachments(txnId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (files: File[]) => {
      const form = new FormData();
      files.forEach((f) => form.append("files", f));
      const { data } = await maApi.post<RFIAttachment[]>(
        `/transactions/${txnId}/rfi/attachments`,
        form,
        { headers: { "Content-Type": "multipart/form-data" } },
      );
      return data;
    },
    onSuccess: (attachments) => {
      qc.invalidateQueries({
        queryKey: [...rfiKeys(txnId), "attachments"],
      });
      toast.success(`${attachments.length}개 파일이 업로드되었습니다`);
    },
    onError: (err) => {
      toast.error(extractErrorDetail(err) ?? "파일 업로드에 실패했습니다");
    },
  });
}

/** 13. 첨부파일 매핑 */
export function useMapAttachment(txnId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({
      fileId,
      body,
    }: {
      fileId: string;
      body: RFIAttachmentMapInput;
    }) => {
      const { data } = await maApi.post<RFIAttachment>(
        `/transactions/${txnId}/rfi/attachments/${fileId}/map`,
        body,
      );
      return data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: rfiKeys(txnId) });
      toast.success("파일이 매핑되었습니다");
    },
    onError: (err) => {
      toast.error(extractErrorDetail(err) ?? "파일 매핑에 실패했습니다");
    },
  });
}

/** 14. 첨부파일 삭제 */
export function useDeleteAttachment(txnId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (fileId: string) => {
      await maApi.delete(`/transactions/${txnId}/rfi/attachments/${fileId}`);
    },
    onSuccess: () => {
      qc.invalidateQueries({
        queryKey: [...rfiKeys(txnId), "attachments"],
      });
      toast.success("파일이 삭제되었습니다");
    },
    onError: (err) => {
      toast.error(extractErrorDetail(err) ?? "파일 삭제에 실패했습니다");
    },
  });
}

/** 15. Excel 내보내기 */
export function useExportRFI(txnId: string) {
  return useMutation({
    mutationFn: async () => {
      const { data } = await maApi.get(`/transactions/${txnId}/rfi/export`, {
        responseType: "blob",
      });
      return data as Blob;
    },
    onSuccess: (blob) => {
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `rfi_export_${txnId}.xlsx`;
      a.click();
      URL.revokeObjectURL(url);
      toast.success("Excel 파일이 다운로드되었습니다");
    },
    onError: (err) => {
      toast.error(extractErrorDetail(err) ?? "Excel 내보내기에 실패했습니다");
    },
  });
}

/** 16. Excel 가져오기 */
export function useImportRFI(txnId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (file: File) => {
      const form = new FormData();
      form.append("file", file);
      const { data } = await maApi.post<RFIExcelImportResult>(
        `/transactions/${txnId}/rfi/import`,
        form,
        { headers: { "Content-Type": "multipart/form-data" } },
      );
      return data;
    },
    onSuccess: (result) => {
      qc.invalidateQueries({ queryKey: rfiKeys(txnId) });

      const errorCount = result.errors?.length ?? 0;
      const conflictCount = result.conflicts?.length ?? 0;

      if (errorCount > 0 || conflictCount > 0) {
        toast.warning(
          `가져오기 실패: ${errorCount}건 오류, ${conflictCount}건 충돌`,
        );
      } else {
        const updated = result.items_updated ?? 0;
        const mapped = result.files_matched ?? 0;
        toast.success(
          `가져오기 완료: ${updated}건 업데이트, ${mapped}건 파일 매핑`,
        );
      }
    },
    onError: (err) => {
      toast.error(extractErrorDetail(err) ?? "Excel 가져오기에 실패했습니다");
    },
  });
}

/** 17. AI RFI 자동 생성 */
export function useGenerateRFI(txnId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: RFIAutoGenerateRequest) => {
      const { data } = await maApi.post<RFIAutoGenerateResult>(
        `/transactions/${txnId}/rfi/generate`,
        body,
      );
      return data;
    },
    onSuccess: (result) => {
      qc.invalidateQueries({ queryKey: rfiKeys(txnId) });
      const count = result.items_created;
      toast.success(`AI 생성 완료: ${count}개 질의`);
    },
    onError: (err) => {
      toast.error(extractErrorDetail(err) ?? "AI RFI 생성에 실패했습니다");
    },
  });
}
