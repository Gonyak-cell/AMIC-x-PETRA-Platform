import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { maApi } from "@/api/maClient";
import type {
  TranscriptionJob,
  TranscriptionStartPayload,
  TranscriptionApprovalPayload,
} from "@/modules/ma/types/transcription";

const KEY = (txnId: string) => ["ma", "transactions", txnId, "transcription"];

/** 변환 작업 목록 조회. */
export function useTranscriptionJobs(txnId: string) {
  return useQuery<TranscriptionJob[]>({
    queryKey: KEY(txnId),
    queryFn: async () => {
      const { data } = await maApi.get(`/transactions/${txnId}/transcription`);
      return data;
    },
    enabled: !!txnId,
  });
}

/** 단일 작업 상태 폴링. refetchInterval로 폴링 간격을 지정할 수 있다. */
export function useTranscriptionStatus(
  txnId: string,
  jobId: string | null,
  opts?: { enabled?: boolean; refetchInterval?: number | false },
) {
  return useQuery<TranscriptionJob>({
    queryKey: [...KEY(txnId), jobId],
    queryFn: async () => {
      const { data } = await maApi.get(`/transactions/${txnId}/transcription/${jobId}`);
      return data;
    },
    enabled: !!txnId && !!jobId && (opts?.enabled !== false),
    refetchInterval: opts?.refetchInterval ?? false,
  });
}

/** 오디오 파일 업로드 + 변환 시작 (202 Accepted). */
export function useStartTranscription(txnId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: TranscriptionStartPayload) => {
      const formData = new FormData();
      formData.append("audio", payload.audio);
      formData.append("title", payload.title);
      formData.append("meeting_date", payload.meeting_date);
      formData.append("meeting_phase", payload.meeting_phase);
      if (payload.buyer_id) formData.append("buyer_id", payload.buyer_id);
      formData.append("attendees_json", payload.attendees_json);

      const { data } = await maApi.post(
        `/transactions/${txnId}/transcription`,
        formData,
        { headers: { "Content-Type": "multipart/form-data" } },
      );
      return data as TranscriptionJob;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: KEY(txnId) });
      toast.success("녹음 변환이 시작되었습니다.");
    },
    onError: () => {
      toast.error("녹음 변환 시작에 실패했습니다.");
    },
  });
}

/** 결과 확정 → meeting_log 생성. */
export function useApproveTranscription(txnId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({
      jobId,
      body,
    }: {
      jobId: string;
      body: TranscriptionApprovalPayload;
    }) => {
      const { data } = await maApi.post(
        `/transactions/${txnId}/transcription/${jobId}/approve`,
        body,
      );
      return data as TranscriptionJob;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: KEY(txnId) });
      // 미팅 로그도 무효화 (새 로그 생성됨)
      qc.invalidateQueries({ queryKey: ["ma", "transactions", txnId, "meeting-logs"] });
      toast.success("회의록이 확정되었습니다.");
    },
    onError: () => {
      toast.error("회의록 확정에 실패했습니다.");
    },
  });
}
