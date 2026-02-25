import { useQuery } from "@tanstack/react-query";
import { imApi } from "@/api/imClient";
import type {
  IMRalphSession,
  RalphProgressData,
} from "@/modules/im/types/ralph";
import { RALPH_ACTIVE_STATUSES } from "@/modules/im/types/ralph";

const POLL_MS = 3_000;

/** 문서의 Ralph Loop 세션 목록 조회. */
export function useIMRalphSessions(documentId: string | undefined) {
  return useQuery<IMRalphSession[]>({
    queryKey: ["im", "ralph", "sessions", documentId],
    queryFn: async () => {
      const { data } = await imApi.get("/ralph/sessions", {
        params: { document_id: documentId },
      });
      return data;
    },
    enabled: !!documentId,
    refetchInterval: (query): number | false => {
      const sessions = query.state.data;
      if (sessions?.some((s) => RALPH_ACTIVE_STATUSES.includes(s.status))) {
        return POLL_MS;
      }
      return false;
    },
  });
}

/** Ralph Loop 세션 상세 조회. */
export function useIMRalphSession(sessionId: string | undefined) {
  return useQuery<IMRalphSession>({
    queryKey: ["im", "ralph", "session", sessionId],
    queryFn: async () => {
      const { data } = await imApi.get(`/ralph/sessions/${sessionId}`);
      return data;
    },
    enabled: !!sessionId,
  });
}

/** Ralph Loop 실시간 프로그레스 (활성 세션만 폴링). */
export function useIMRalphProgress(sessionId: string | undefined, active: boolean) {
  return useQuery<RalphProgressData>({
    queryKey: ["im", "ralph", "progress", sessionId],
    queryFn: async () => {
      const { data } = await imApi.get(`/ralph/sessions/${sessionId}/progress`);
      return data;
    },
    enabled: !!sessionId && active,
    refetchInterval: active ? POLL_MS : false,
  });
}
