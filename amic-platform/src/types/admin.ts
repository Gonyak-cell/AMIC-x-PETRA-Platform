import type { AuthUser, UserRole } from "./auth";

export interface AdminUser extends AuthUser {
  last_login_at?: string;
}

export interface UserCreate {
  email: string;
  display_name: string;
  password: string;
  role: UserRole;
}

export interface UserUpdate {
  display_name?: string;
  role?: UserRole;
  is_active?: boolean;
}
