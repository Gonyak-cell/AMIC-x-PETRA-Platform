import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { maApi } from "@/api/maClient";
import type {
  RFI,
  RFICreate,
  RFIDetail,
  RFIExcelImportResult,
  RFIItem,
  RFIItemCreate,
  RFIItemRespondInput,
  RFIItemReviewInput,
  RFIItemUpdate,
  RFISummary,
  RFIUpdate,
  RFIAutoGenerateResult,
} from "@/modules/ma/types/rfi";

const KEY = "ma";
const rfiKeys = (txnId: string) => [KEY, "transactions", txnId, "rfis"];

/** 서버 에러 응답에서 detail 메시지를 추출한다. */
function extractErrorDetail(err: unknown): string | undefined {
  return (err as { response?: { data?: { detail?: string } } })?.response?.data
    ?.detail;
}

// ── RFI 목록 ──────────────────────────────────────────

export function useRFIs(txnId: string, status?: string, roundNumber?: number) {
  return useQuery<RFI[]>({
    queryKey: [...rfiKeys(txnId), { status, roundNumber }],
    queryFn: async () => {
      const params: Record<string, string | number> = {};
      if (status) params.status = status;
      if (roundNumber) params.round_number = roundNumber;
      const { data } = await maApi.get(`/transactions/${txnId}/rfis`, {
        params,
      });
      return data;
    },
    enabled: !!txnId,
  });
}

// ── RFI 상세 ──────────────────────────────────────────

export function useRFI(txnId: string, rfiId: string) {
  return useQuery<RFIDetail>({
    queryKey: [...rfiKeys(txnId), rfiId],
    queryFn: async () => {
      const { data } = await maApi.get(
        `/transactions/${txnId}/rfis/${rfiId}`,
      );
      return data;
    },
    enabled: !!txnId && !!rfiId,
  });
}

// ── RFI Summary ───────────────────────────────────────

export function useRFISummary(txnId: string) {
  return useQuery<RFISummary>({
    queryKey: [...rfiKeys(txnId), "summary"],
    queryFn: async () => {
      const { data } = await maApi.get(
        `/transactions/${txnId}/rfis/summary`,
      );
      return data;
    },
    enabled: !!txnId,
  });
}

// ── RFI CRUD ──────────────────────────────────────────

export function useCreateRFI(txnId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: RFICreate) => {
      const { data } = await maApi.post(
        `/transactions/${txnId}/rfis`,
        body,
      );
      return data as RFI;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: rfiKeys(txnId) });
      toast.success("RFI가 생성되었습니다.");
    },
    onError: (err: unknown) =>
      toast.error(extractErrorDetail(err) || "RFI 생성에 실패했습니다."),
  });
}

export function useUpdateRFI(txnId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({
      rfiId,
      body,
    }: {
      rfiId: string;
      body: RFIUpdate;
    }) => {
      const { data } = await maApi.patch(
        `/transactions/${txnId}/rfis/${rfiId}`,
        body,
      );
      return data as RFI;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: rfiKeys(txnId) });
      toast.success("RFI가 수정되었습니다.");
    },
    onError: (err: unknown) =>
      toast.error(extractErrorDetail(err) || "RFI 수정에 실패했습니다."),
  });
}

export function useDeleteRFI(txnId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (rfiId: string) => {
      await maApi.delete(`/transactions/${txnId}/rfis/${rfiId}`);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: rfiKeys(txnId) });
      toast.success("RFI가 삭제되었습니다.");
    },
    onError: (err: unknown) =>
      toast.error(extractErrorDetail(err) || "RFI 삭제에 실패했습니다."),
  });
}

// ── RFI 워크플로우 ────────────────────────────────────

export function useSendRFI(txnId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (rfiId: string) => {
      const { data } = await maApi.post(
        `/transactions/${txnId}/rfis/${rfiId}/send`,
      );
      return data as RFI;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: rfiKeys(txnId) });
      toast.success("RFI가 발송되었습니다.");
    },
    onError: (err: unknown) =>
      toast.error(extractErrorDetail(err) || "RFI 발송에 실패했습니다."),
  });
}

export function useCloseRFI(txnId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (rfiId: string) => {
      const { data } = await maApi.post(
        `/transactions/${txnId}/rfis/${rfiId}/close`,
      );
      return data as RFI;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: rfiKeys(txnId) });
      toast.success("RFI가 마감되었습니다.");
    },
    onError: (err: unknown) =>
      toast.error(extractErrorDetail(err) || "RFI 마감에 실패했습니다."),
  });
}

export function useExtendRFIDeadline(txnId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({
      rfiId,
      dueDate,
    }: {
      rfiId: string;
      dueDate: string;
    }) => {
      const { data } = await maApi.patch(
        `/transactions/${txnId}/rfis/${rfiId}/extend-deadline`,
        { due_date: dueDate },
      );
      return data as RFI;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: rfiKeys(txnId) });
      toast.success("마감일이 연장되었습니다.");
    },
    onError: (err: unknown) =>
      toast.error(extractErrorDetail(err) || "마감일 연장에 실패했습니다."),
  });
}

// ── RFI Item CRUD ─────────────────────────────────────

export function useCreateRFIItem(txnId: string, rfiId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: RFIItemCreate) => {
      const { data } = await maApi.post(
        `/transactions/${txnId}/rfis/${rfiId}/items`,
        body,
      );
      return data as RFIItem;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: rfiKeys(txnId) });
      toast.success("질문이 추가되었습니다.");
    },
    onError: (err: unknown) =>
      toast.error(extractErrorDetail(err) || "질문 추가에 실패했습니다."),
  });
}

export function useBatchCreateRFIItems(txnId: string, rfiId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (items: RFIItemCreate[]) => {
      const { data } = await maApi.post(
        `/transactions/${txnId}/rfis/${rfiId}/items/batch`,
        { items },
      );
      return data as RFIItem[];
    },
    onSuccess: (items) => {
      qc.invalidateQueries({ queryKey: rfiKeys(txnId) });
      toast.success(`${items.length}개 질문이 추가되었습니다.`);
    },
    onError: (err: unknown) =>
      toast.error(extractErrorDetail(err) || "질문 일괄 추가에 실패했습니다."),
  });
}

export function useUpdateRFIItem(txnId: string, rfiId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({
      itemId,
      body,
    }: {
      itemId: string;
      body: RFIItemUpdate;
    }) => {
      const { data } = await maApi.patch(
        `/transactions/${txnId}/rfis/${rfiId}/items/${itemId}`,
        body,
      );
      return data as RFIItem;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: rfiKeys(txnId) });
      toast.success("질문이 수정되었습니다.");
    },
    onError: (err: unknown) =>
      toast.error(extractErrorDetail(err) || "질문 수정에 실패했습니다."),
  });
}

export function useDeleteRFIItem(txnId: string, rfiId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (itemId: string) => {
      await maApi.delete(
        `/transactions/${txnId}/rfis/${rfiId}/items/${itemId}`,
      );
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: rfiKeys(txnId) });
      toast.success("질문이 삭제되었습니다.");
    },
    onError: (err: unknown) =>
      toast.error(extractErrorDetail(err) || "질문 삭제에 실패했습니다."),
  });
}

// ── 응답 / 검토 ───────────────────────────────────────

export function useRespondRFIItem(txnId: string, rfiId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({
      itemId,
      body,
    }: {
      itemId: string;
      body: RFIItemRespondInput;
    }) => {
      const { data } = await maApi.post(
        `/transactions/${txnId}/rfis/${rfiId}/items/${itemId}/respond`,
        body,
      );
      return data as RFIItem;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: rfiKeys(txnId) });
      toast.success("응답이 저장되었습니다.");
    },
    onError: (err: unknown) =>
      toast.error(extractErrorDetail(err) || "응답 저장에 실패했습니다."),
  });
}

export function useReviewRFIItem(txnId: string, rfiId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({
      itemId,
      body,
    }: {
      itemId: string;
      body: RFIItemReviewInput;
    }) => {
      const { data } = await maApi.post(
        `/transactions/${txnId}/rfis/${rfiId}/items/${itemId}/review`,
        body,
      );
      return data as RFIItem;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: rfiKeys(txnId) });
      toast.success("검토가 완료되었습니다.");
    },
    onError: (err: unknown) =>
      toast.error(extractErrorDetail(err) || "검토에 실패했습니다."),
  });
}

// ── 자동 생성 ─────────────────────────────────────────

export function useGenerateRFIFromDD(txnId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (title?: string) => {
      const { data } = await maApi.post(
        `/transactions/${txnId}/rfis/generate-from-dd`,
        { title: title || "DD 체크리스트 기반 RFI" },
      );
      return data as RFIAutoGenerateResult;
    },
    onSuccess: (result) => {
      qc.invalidateQueries({ queryKey: rfiKeys(txnId) });
      toast.success(`RFI 생성 완료: ${result.items_created}개 질문`);
    },
    onError: (err: unknown) =>
      toast.error(extractErrorDetail(err) || "RFI 자동 생성에 실패했습니다."),
  });
}

// ── 동기화 ────────────────────────────────────────────

export function useSyncRFIToChecklists(txnId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (rfiId: string) => {
      const { data } = await maApi.post(
        `/transactions/${txnId}/rfis/${rfiId}/sync-to-checklists`,
      );
      return data as { synced: number };
    },
    onSuccess: (result) => {
      qc.invalidateQueries({ queryKey: rfiKeys(txnId) });
      toast.success(`${result.synced}개 항목이 체크리스트에 반영되었습니다.`);
    },
    onError: (err: unknown) =>
      toast.error(
        extractErrorDetail(err) || "체크리스트 동기화에 실패했습니다.",
      ),
  });
}

// ── Excel 내보내기 ────────────────────────────────────

export function useExportRFI(txnId: string) {
  return useMutation({
    mutationFn: async (rfiId: string) => {
      const { data } = await maApi.get(
        `/transactions/${txnId}/rfis/${rfiId}/export`,
        { responseType: "blob" },
      );
      const url = URL.createObjectURL(data);
      const a = document.createElement("a");
      a.href = url;
      a.download = `RFI_${rfiId}.xlsx`;
      a.click();
      setTimeout(() => URL.revokeObjectURL(url), 5000);
    },
    onSuccess: () => toast.success("Excel 파일이 다운로드되었습니다."),
    onError: (err: unknown) =>
      toast.error(extractErrorDetail(err) || "Excel 내보내기에 실패했습니다."),
  });
}

// ── Excel 가져오기 ────────────────────────────────────

export function useImportRFI(txnId: string, rfiId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (file: File) => {
      const formData = new FormData();
      formData.append("file", file);
      const { data } = await maApi.post<RFIExcelImportResult>(
        `/transactions/${txnId}/rfis/${rfiId}/import`,
        formData,
        { headers: { "Content-Type": "multipart/form-data" } },
      );
      return data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: rfiKeys(txnId) });
      toast.success("Excel 가져오기가 완료되었습니다.");
    },
    onError: (err: unknown) => {
      toast.error(
        extractErrorDetail(err) || "Excel 가져오기에 실패했습니다.",
      );
    },
  });
}
