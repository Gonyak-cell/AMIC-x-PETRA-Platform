import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { maApi } from "@/api/maClient";
import type {
  MeetingPhase,
  MeetingStatus,
  MeetingLog,
  MeetingLogDetail,
  MeetingLogCreate,
  MeetingLogUpdate,
  MeetingLogListResponse,
  MeetingLogSummary,
  MeetingActionItem,
  MeetingActionItemCreate,
} from "@/modules/ma/types/meeting_log";

const KEY = (txnId: string) => ["ma", "transactions", txnId, "meeting-logs"];

export function useMeetingLogs(
  txnId: string,
  opts?: {
    meetingPhase?: MeetingPhase;
    status?: MeetingStatus;
    buyerId?: string;
  },
) {
  return useQuery<MeetingLogListResponse>({
    queryKey: [...KEY(txnId), opts],
    queryFn: async () => {
      const params: Record<string, string> = {};
      if (opts?.meetingPhase) params.meeting_phase = opts.meetingPhase;
      if (opts?.status) params.status = opts.status;
      if (opts?.buyerId) params.buyer_id = opts.buyerId;
      const { data } = await maApi.get(`/transactions/${txnId}/meeting-logs`, {
        params,
      });
      return data;
    },
    enabled: !!txnId,
  });
}

export function useMeetingLog(txnId: string, logId: string) {
  return useQuery<MeetingLogDetail>({
    queryKey: [...KEY(txnId), logId],
    queryFn: async () => {
      const { data } = await maApi.get(
        `/transactions/${txnId}/meeting-logs/${logId}`,
      );
      return data;
    },
    enabled: !!txnId && !!logId,
  });
}

export function useMeetingLogSummary(
  txnId: string,
  meetingPhase?: MeetingPhase,
) {
  return useQuery<MeetingLogSummary>({
    queryKey: [...KEY(txnId), "summary", meetingPhase],
    queryFn: async () => {
      const params: Record<string, string> = {};
      if (meetingPhase) params.meeting_phase = meetingPhase;
      const { data } = await maApi.get(
        `/transactions/${txnId}/meeting-logs/summary`,
        { params },
      );
      return data;
    },
    enabled: !!txnId,
  });
}

export function useCreateMeetingLog(txnId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: MeetingLogCreate) => {
      const { data } = await maApi.post(
        `/transactions/${txnId}/meeting-logs`,
        body,
      );
      return data as MeetingLog;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: KEY(txnId) });
      // 마케팅 로그 통합: marketing-log 관련 쿼리도 갱신
      qc.invalidateQueries({
        queryKey: ["ma", "transactions", txnId, "buyers"],
      });
      qc.invalidateQueries({
        queryKey: ["ma", "transactions", txnId, "short-list", "overview"],
      });
      toast.success("미팅 로그가 생성되었습니다.");
    },
    onError: () => {
      toast.error("미팅 로그 생성에 실패했습니다.");
    },
  });
}

export function useUpdateMeetingLog(txnId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({
      logId,
      body,
    }: {
      logId: string;
      body: MeetingLogUpdate;
    }) => {
      const { data } = await maApi.patch(
        `/transactions/${txnId}/meeting-logs/${logId}`,
        body,
      );
      return data as MeetingLog;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: KEY(txnId) });
      toast.success("미팅 로그가 수정되었습니다.");
    },
    onError: () => {
      toast.error("미팅 로그 수정에 실패했습니다.");
    },
  });
}

export function useDeleteMeetingLog(txnId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (logId: string) => {
      await maApi.delete(`/transactions/${txnId}/meeting-logs/${logId}`);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: KEY(txnId) });
      toast.success("미팅 로그가 삭제되었습니다.");
    },
    onError: () => {
      toast.error("미팅 로그 삭제에 실패했습니다.");
    },
  });
}

// ── Action Items ──────────────────────────────────────

export function useCreateActionItem(txnId: string, logId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: MeetingActionItemCreate) => {
      const { data } = await maApi.post(
        `/transactions/${txnId}/meeting-logs/${logId}/action-items`,
        body,
      );
      return data as MeetingActionItem;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: [...KEY(txnId), logId] });
      toast.success("액션아이템이 추가되었습니다.");
    },
    onError: () => {
      toast.error("액션아이템 추가에 실패했습니다.");
    },
  });
}

export function useUpdateActionItem(txnId: string, logId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({
      itemId,
      body,
    }: {
      itemId: string;
      body: Partial<MeetingActionItemCreate>;
    }) => {
      const { data } = await maApi.patch(
        `/transactions/${txnId}/meeting-logs/${logId}/action-items/${itemId}`,
        body,
      );
      return data as MeetingActionItem;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: [...KEY(txnId), logId] });
      toast.success("액션아이템이 수정되었습니다.");
    },
    onError: () => {
      toast.error("액션아이템 수정에 실패했습니다.");
    },
  });
}

export function useDeleteActionItem(txnId: string, logId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (itemId: string) => {
      await maApi.delete(
        `/transactions/${txnId}/meeting-logs/${logId}/action-items/${itemId}`,
      );
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: [...KEY(txnId), logId] });
      toast.success("액션아이템이 삭제되었습니다.");
    },
    onError: () => {
      toast.error("액션아이템 삭제에 실패했습니다.");
    },
  });
}
