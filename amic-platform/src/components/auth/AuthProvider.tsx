import { useState, useEffect, useCallback, type ReactNode } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { useLocation } from "react-router-dom";
import { getAuthApiForPath, shouldSkipAuthBootstrapPath } from "@/api/client";
import { AUTH_LOGOUT_EVENT } from "@/lib/auth-events";
import type { AuthUser, AuthState } from "@/types/auth";
import { AuthContext } from "./AuthContext";
import {
  DEV_LOCAL_AUTH_ENABLED,
  clearLocalAuthSession,
  getLocalAuthSession,
} from "@/lib/devAuth";

/** ?뭭 ?꾩슂 ?뚯씠?? Context Provider (Sprint 11). */

function getInitialAuthState(): AuthState {
  if (DEV_LOCAL_AUTH_ENABLED) {
    const user = getLocalAuthSession();
    return {
      user,
      isAuthenticated: Boolean(user),
      isLoading: false,
    };
  }

  return {
    user: null,
    isAuthenticated: false,
    isLoading: true,
  };
}

function clearSidebarStorage(): void {
  try {
    Object.keys(sessionStorage)
      .filter(
        (k) =>
          k.startsWith("sidebar-module-") || k.startsWith("sidebar-section-"),
      )
      .forEach((k) => sessionStorage.removeItem(k));
  } catch {
    // sessionStorage unavailable
  }
}

export default function AuthProvider({ children }: { children: ReactNode }) {
  const location = useLocation();
  const queryClient = useQueryClient();
  const [state, setState] = useState<AuthState>(getInitialAuthState);
  const authApi = getAuthApiForPath(location.pathname);
  const skipBootstrap = shouldSkipAuthBootstrapPath(location.pathname);

  const setAuthState = useCallback((next: AuthState) => {
    setState(next);
  }, []);

  // M9: Listen for force-logout events from interceptor
  useEffect(() => {
    const handler = () => {
      queryClient.clear();
      clearSidebarStorage();
      clearLocalAuthSession();
      setState({ user: null, isAuthenticated: false, isLoading: false });
    };
    window.addEventListener(AUTH_LOGOUT_EVENT, handler);
    return () => window.removeEventListener(AUTH_LOGOUT_EVENT, handler);
  }, [queryClient]);

  // On mount: check local auth state first (DEV mode), otherwise fetch me profile
  useEffect(() => {
    if (DEV_LOCAL_AUTH_ENABLED) {
      const user = getLocalAuthSession();
      setState({
        user,
        isAuthenticated: Boolean(user),
        isLoading: false,
      });
      return;
    }

    if (skipBootstrap) {
      setState((current) =>
        current.isLoading ? { ...current, isLoading: false } : current,
      );
      return;
    }

    const controller = new AbortController();
    let cancelled = false;

    const fetchMe = () => {
      authApi
        .get<AuthUser>("/auth/me", { signal: controller.signal })
        .then(({ data }) => {
          if (cancelled) return;
          setState({ user: data, isAuthenticated: true, isLoading: false });
        })
        .catch(() => {
          if (cancelled) return;
          setState({ user: null, isAuthenticated: false, isLoading: false });
        });
    };

    fetchMe();

    return () => {
      cancelled = true;
      controller.abort();
    };
  }, [authApi, skipBootstrap]);

  return (
    <AuthContext.Provider value={{ ...state, setAuthState }}>
      {children}
    </AuthContext.Provider>
  );
}
