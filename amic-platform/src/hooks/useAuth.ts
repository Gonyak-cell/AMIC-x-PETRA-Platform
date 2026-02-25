/** 인증 훅 — 로그인, 로그아웃, 토큰 관리 (Sprint 11). */

import { useContext, useCallback } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { AuthContext } from "@/components/auth/AuthContext";
import api from "@/api/client";
import type {
  LoginRequest,
  AuthUser,
  Permission,
} from "@/types/auth";
import { ROLE_PERMISSIONS } from "@/types/auth";

// ── Main hook ──

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used within <AuthProvider>");
  }

  const queryClient = useQueryClient();
  const { user, isAuthenticated, isLoading, setAuthState } = ctx;

  const login = useCallback(
    async (credentials: LoginRequest) => {
      await api.post<{ message: string }>(
        "/auth/login",
        credentials,
      );
      // 토큰은 쿠키로 자동 설정됨

      try {
        const { data: me } = await api.get<AuthUser>("/auth/me");
        setAuthState({ user: me, isAuthenticated: true, isLoading: false });
      } catch (err) {
        setAuthState({ user: null, isAuthenticated: false, isLoading: false });
        throw err;
      }
    },
    [setAuthState],
  );

  const logout = useCallback(async () => {
    try {
      await api.post("/auth/logout");
    } finally {
      // 쿠키는 백엔드가 삭제함
      queryClient.clear();
      setAuthState({ user: null, isAuthenticated: false, isLoading: false });
    }
  }, [setAuthState, queryClient]);

  const hasPermission = useCallback(
    (permission: Permission): boolean => {
      if (!user) return false;
      return ROLE_PERMISSIONS[user.role]?.has(permission) ?? false;
    },
    [user],
  );

  const isClient = user?.role === "CLIENT";

  const canWrite = useCallback(
    (): boolean => {
      if (!user) return false;
      return user.role !== "CLIENT";
    },
    [user],
  );

  return { user, isAuthenticated, isLoading, login, logout, hasPermission, isClient, canWrite };
}
