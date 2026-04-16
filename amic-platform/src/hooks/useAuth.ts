import { useContext, useCallback } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { AuthContext } from "@/components/auth/AuthContext";
import { authApi } from "@/api/client";
import {
  DEV_LOCAL_AUTH_ENABLED,
  loginWithDevCredentials,
  clearLocalAuthSession,
  setLocalAuthSession,
} from "@/lib/devAuth";
import type {
  LoginRequest,
  AuthUser,
  Permission,
} from "@/types/auth";
import { ROLE_PERMISSIONS } from "@/types/auth";

// ?뭭 auth?쒓굅?? Main hook ?뭭

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used within <AuthProvider>");
  }

  const queryClient = useQueryClient();
  const { user, isAuthenticated, isLoading, setAuthState } = ctx;

  const login = useCallback(
    async (credentials: LoginRequest) => {
      if (DEV_LOCAL_AUTH_ENABLED) {
        const user = loginWithDevCredentials(credentials);
        if (!user) {
          throw new Error("Invalid email or password.");
        }
        setLocalAuthSession(user);
        setAuthState({ user, isAuthenticated: true, isLoading: false });
        return;
      }

      await authApi.post<{ message: string }>(
        "/auth/login",
        credentials,
      );
      // ?좏겙? 荑좏궎濡??먮룞 ?ㅼ젙??

      try {
        const { data: me } = await authApi.get<AuthUser>("/auth/me");
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
      await authApi.post("/auth/logout");
    } finally {
      // 荑좏궎??諛깆뿏?쒓? ??젣??
      queryClient.clear();
      // ?ъ씠?쒕컮 硫붾돱 ?곹깭 珥덇린??(濡쒓렇?꾩썐 ???섏쐞 硫붾돱 ?묓옒)
      Object.keys(sessionStorage)
        .filter(k => k.startsWith("sidebar-module-") || k.startsWith("sidebar-section-"))
        .forEach(k => sessionStorage.removeItem(k));
      clearLocalAuthSession();
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

  return {
    user,
    isAuthenticated,
    isLoading,
    login,
    logout,
    hasPermission,
    isClient,
    canWrite,
  };
}
