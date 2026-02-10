import { createContext } from "react";
import type { AuthState } from "@/types/auth";

export interface AuthContextValue extends AuthState {
  setAuthState: (state: AuthState) => void;
}

export const AuthContext = createContext<AuthContextValue | null>(null);
