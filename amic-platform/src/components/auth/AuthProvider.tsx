/** 인증 Context Provider (Sprint 11). */

import {
  useState,
  useEffect,
  useCallback,
  type ReactNode,
} from "react";
import api from "@/api/client";
import {
  getAccessToken,
  clearTokens,
} from "@/hooks/useAuth";
import type { AuthUser, AuthState } from "@/types/auth";
import { AuthContext } from "./AuthContext";

export default function AuthProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<AuthState>({
    user: null,
    isAuthenticated: false,
    isLoading: true,
  });

  const setAuthState = useCallback((next: AuthState) => {
    setState(next);
  }, []);

  // On mount: check for existing token and fetch user profile
  useEffect(() => {
    const token = getAccessToken();
    if (!token) {
      // No token — try unauthenticated /me (works when AUTH_ENABLED=False)
      api
        .get<AuthUser>("/auth/me")
        .then(({ data }) => {
          setState({
            user: data,
            isAuthenticated: true,
            isLoading: false,
          });
        })
        .catch(() => {
          setState({ user: null, isAuthenticated: false, isLoading: false });
        });
      return;
    }

    // Token exists — validate by fetching /me
    api
      .get<AuthUser>("/auth/me")
      .then(({ data }) => {
        setState({ user: data, isAuthenticated: true, isLoading: false });
      })
      .catch(() => {
        clearTokens();
        setState({ user: null, isAuthenticated: false, isLoading: false });
      });
  }, []);

  return (
    <AuthContext.Provider value={{ ...state, setAuthState }}>
      {children}
    </AuthContext.Provider>
  );
}
