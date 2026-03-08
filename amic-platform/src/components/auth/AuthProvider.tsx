/** 인증 Context Provider (Sprint 11). */

import {
  useState,
  useEffect,
  useCallback,
  type ReactNode,
} from "react";
import { useQueryClient } from "@tanstack/react-query";
import api from "@/api/client";
import { AUTH_LOGOUT_EVENT } from "@/lib/auth-events";
import type { AuthUser, AuthState } from "@/types/auth";
import { AuthContext } from "./AuthContext";

/** 사이드바 메뉴 상태(sessionStorage) 일괄 초기화 */
function clearSidebarStorage(): void {
  try {
    Object.keys(sessionStorage)
      .filter(k => k.startsWith("sidebar-module-") || k.startsWith("sidebar-section-"))
      .forEach(k => sessionStorage.removeItem(k));
  } catch {
    // sessionStorage unavailable
  }
}

export default function AuthProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient();
  const [state, setState] = useState<AuthState>({
    user: null,
    isAuthenticated: false,
    isLoading: true,
  });

  const setAuthState = useCallback((next: AuthState) => {
    setState(next);
  }, []);

  // M9: Listen for force-logout events from interceptor
  useEffect(() => {
    const handler = () => {
      // 쿠키는 백엔드가 삭제함
      queryClient.clear();
      clearSidebarStorage();
      setState({ user: null, isAuthenticated: false, isLoading: false });
    };
    window.addEventListener(AUTH_LOGOUT_EVENT, handler);
    return () => window.removeEventListener(AUTH_LOGOUT_EVENT, handler);
  }, [queryClient]);

  // On mount: check for existing token and fetch user profile (M12: AbortController cleanup)
  useEffect(() => {
    const controller = new AbortController();
    let cancelled = false;

    const fetchMe = () => {
      api
        .get<AuthUser>("/auth/me", { signal: controller.signal })
        .then(({ data }) => {
          if (cancelled) return;
          setState({ user: data, isAuthenticated: true, isLoading: false });
        })
        .catch(() => {
          if (cancelled) return;
          // 쿠키가 없거나 만료되면 401 반환, 로그아웃 상태로 전환
          setState({ user: null, isAuthenticated: false, isLoading: false });
        });
    };

    fetchMe();

    return () => {
      cancelled = true;
      controller.abort();
    };
  }, []);

  return (
    <AuthContext.Provider value={{ ...state, setAuthState }}>
      {children}
    </AuthContext.Provider>
  );
}
