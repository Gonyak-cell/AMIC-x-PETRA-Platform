/** 인증/인가 타입 정의 (Sprint 11). */

export type UserRole = "ADMIN" | "MANAGER" | "ANALYST" | "VIEWER";

export type Permission =
  | "deal:create"
  | "deal:read"
  | "deal:update"
  | "deal:delete"
  | "definition:approve"
  | "upload:create"
  | "mapping:approve"
  | "report:generate"
  | "report:download"
  | "audit:view"
  | "user:manage";

/** Backend ROLE_PERMISSIONS 미러링. */
export const ROLE_PERMISSIONS: Record<UserRole, Set<Permission>> = {
  ADMIN: new Set<Permission>([
    "deal:create",
    "deal:read",
    "deal:update",
    "deal:delete",
    "definition:approve",
    "upload:create",
    "mapping:approve",
    "report:generate",
    "report:download",
    "audit:view",
    "user:manage",
  ]),
  MANAGER: new Set<Permission>([
    "deal:create",
    "deal:read",
    "deal:update",
    "deal:delete",
    "definition:approve",
    "upload:create",
    "mapping:approve",
    "report:generate",
    "report:download",
    "audit:view",
  ]),
  ANALYST: new Set<Permission>([
    "deal:read",
    "deal:update",
    "upload:create",
    "report:generate",
    "report:download",
  ]),
  VIEWER: new Set<Permission>(["deal:read", "report:download"]),
};

export interface AuthUser {
  id: string;
  email: string;
  display_name: string;
  role: UserRole;
  is_active: boolean;
  created_at: string;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: "bearer";
  expires_in: number;
}

export interface RefreshRequest {
  refresh_token: string;
}

export interface AuthState {
  user: AuthUser | null;
  isAuthenticated: boolean;
  isLoading: boolean;
}
