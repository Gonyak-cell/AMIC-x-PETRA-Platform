import type { AuthUser, LoginRequest } from "@/types/auth";

const DEV_AUTH_KEY = "amic-dev-auth-user";

const DEV_ACCOUNTS: Array<{ email: string; password: string; user: AuthUser }> = [
  {
    email: "ytkim@amic.kr",
    password: "1111",
    user: {
      id: "user-2",
      email: "ytkim@amic.kr",
      display_name: "Kim Yang Tae",
      title: "Admin / Team Lead",
      role: "ADMIN",
      is_active: true,
      created_at: "2025-01-01T00:00:00Z",
    },
  },
];

export const DEFAULT_DEV_LOGIN = {
  email: DEV_ACCOUNTS[0]?.email ?? "",
  password: DEV_ACCOUNTS[0]?.password ?? "",
};

export const DEV_LOCAL_AUTH_ENABLED =
  (import.meta.env.VITE_DEV_LOCAL_AUTH ?? "").trim() === "true";

export function loginWithDevCredentials(
  credentials: LoginRequest,
): AuthUser | null {
  const account = DEV_ACCOUNTS.find(
    (item) => item.email === credentials.email && item.password === credentials.password,
  );
  return account ? account.user : null;
}

export function getLocalAuthSession(): AuthUser | null {
  if (typeof sessionStorage === "undefined") return null;
  const raw = sessionStorage.getItem(DEV_AUTH_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as AuthUser;
  } catch {
    sessionStorage.removeItem(DEV_AUTH_KEY);
    return null;
  }
}

export function setLocalAuthSession(user: AuthUser): void {
  if (typeof sessionStorage === "undefined") return;
  sessionStorage.setItem(DEV_AUTH_KEY, JSON.stringify(user));
}

export function clearLocalAuthSession(): void {
  if (typeof sessionStorage === "undefined") return;
  sessionStorage.removeItem(DEV_AUTH_KEY);
}
