/** 초대(Invite) 관련 훅 — 생성, 토큰 검증, 수락. */

import { useMutation, useQuery } from "@tanstack/react-query";
import api from "@/api/client";
import type {
  InviteCreatePayload,
  InviteCreateResult,
  InviteTokenInfo,
  InviteAcceptPayload,
  InviteAcceptResult,
} from "@/types/invite";

export function useCreateInvite() {
  return useMutation({
    mutationFn: async (payload: InviteCreatePayload) => {
      const { data } = await api.post<InviteCreateResult>(
        "/auth/invite",
        payload,
      );
      return data;
    },
  });
}

/** 토큰 검증 — POST 방식 사용 (GET 시 URL/로그에 토큰 노출 방지). */
export function useVerifyInvite(token: string | null) {
  return useQuery({
    queryKey: ["invite-verify", token],
    queryFn: async () => {
      const { data } = await api.post<InviteTokenInfo>("/auth/invite/verify", {
        token,
      });
      return data;
    },
    enabled: !!token,
    retry: false,
  });
}

export function useAcceptInvite() {
  return useMutation({
    mutationFn: async (payload: InviteAcceptPayload) => {
      const { data } = await api.post<InviteAcceptResult>(
        "/auth/invite/accept",
        payload,
      );
      return data;
    },
  });
}
