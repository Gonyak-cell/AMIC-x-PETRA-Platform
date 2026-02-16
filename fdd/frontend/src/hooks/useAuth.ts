/** 인증 훅 — 로그인, 로그아웃, 토큰 관리 (Sprint 11). */

import { useContext, useCallback } from "react";
import { AuthContext } from "@/components/auth/AuthContext";
import api from "@/api/client";
import type {
  LoginRequest,
  TokenResponse,
  AuthUser,
  Permission,
} from "@/types/auth";
import { ROLE_PERMISSIONS } from "@/types/auth";

const ACCESS_TOKEN_KEY = "autofdd_access_token";
const REFRESH_TOKEN_KEY = "autofdd_refresh_token";

// ── Token storage helpers ──

export function getAccessToken(): string | null {
  return localStorage.getItem(ACCESS_TOKEN_KEY);
}

export function getRefreshToken(): string | null {
  return localStorage.getItem(REFRESH_TOKEN_KEY);
}

export function setTokens(access: string, refresh: string): void {
  localStorage.setItem(ACCESS_TOKEN_KEY, access);
  localStorage.setItem(REFRESH_TOKEN_KEY, refresh);
}

export function clearTokens(): void {
  localStorage.removeItem(ACCESS_TOKEN_KEY);
  localStorage.removeItem(REFRESH_TOKEN_KEY);
}

// ── Main hook ──

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used within <AuthProvider>");
  }

  const { user, isAuthenticated, isLoading, setAuthState } = ctx;

  const login = useCallback(
    async (credentials: LoginRequest) => {
      const { data } = await api.post<TokenResponse>(
        "/auth/login",
        credentials,
      );
      setTokens(data.access_token, data.refresh_token);

      // Fetch user profile
      const { data: me } = await api.get<AuthUser>("/auth/me");
      setAuthState({ user: me, isAuthenticated: true, isLoading: false });
    },
    [setAuthState],
  );

  const logout = useCallback(() => {
    clearTokens();
    setAuthState({ user: null, isAuthenticated: false, isLoading: false });
  }, [setAuthState]);

  const hasPermission = useCallback(
    (permission: Permission): boolean => {
      if (!user) return false;
      return ROLE_PERMISSIONS[user.role]?.has(permission) ?? false;
    },
    [user],
  );

  return { user, isAuthenticated, isLoading, login, logout, hasPermission };
}
