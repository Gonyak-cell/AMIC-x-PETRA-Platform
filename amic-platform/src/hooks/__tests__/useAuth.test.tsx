import { renderHook, act } from "@testing-library/react";
import type { ReactNode } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { http, HttpResponse } from "msw";
import {
  AuthContext,
  type AuthContextValue,
} from "@/components/auth/AuthContext";
import { useAuth } from "../useAuth";
import { mockUser, mockViewerUser } from "@/test/mocks/data";
import { server } from "@/test/mocks/server";

function createAuthWrapper(
  overrides: Partial<AuthContextValue> = {},
  initialPath = "/ma/transactions",
) {
  const value: AuthContextValue = {
    user: mockUser,
    isAuthenticated: true,
    isLoading: false,
    setAuthState: vi.fn(),
    ...overrides,
  };

  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });

  return {
    value,
    wrapper: ({ children }: { children: ReactNode }) => (
      <MemoryRouter initialEntries={[initialPath]}>
        <QueryClientProvider client={queryClient}>
          <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
        </QueryClientProvider>
      </MemoryRouter>
    ),
  };
}

describe("useAuth", () => {
  it("throws when used outside AuthProvider", () => {
    const spy = vi.spyOn(console, "error").mockImplementation(() => {});

    expect(() => {
      renderHook(() => useAuth());
    }).toThrow("useAuth must be used within <AuthProvider>");

    spy.mockRestore();
  });

  it("returns user and auth state", () => {
    const { wrapper } = createAuthWrapper();
    const { result } = renderHook(() => useAuth(), { wrapper });

    expect(result.current.user).toEqual(mockUser);
    expect(result.current.isAuthenticated).toBe(true);
    expect(result.current.isLoading).toBe(false);
  });

  it("logout resets auth state", async () => {
    const { wrapper, value } = createAuthWrapper();
    const { result } = renderHook(() => useAuth(), { wrapper });

    server.use(
      http.post("*/api/ma/auth/logout", () =>
        HttpResponse.json({ message: "logged out" }),
      ),
    );

    await act(async () => {
      await result.current.logout();
    });

    expect(value.setAuthState).toHaveBeenCalledWith({
      user: null,
      isAuthenticated: false,
      isLoading: false,
    });
  });

  describe("hasPermission", () => {
    it("ADMIN has all permissions", () => {
      const { wrapper } = createAuthWrapper({ user: mockUser });
      const { result } = renderHook(() => useAuth(), { wrapper });

      expect(result.current.hasPermission("deal:create")).toBe(true);
      expect(result.current.hasPermission("user:manage")).toBe(true);
      expect(result.current.hasPermission("audit:view")).toBe(true);
    });

    it("VIEWER has limited permissions", () => {
      const { wrapper } = createAuthWrapper({ user: mockViewerUser });
      const { result } = renderHook(() => useAuth(), { wrapper });

      expect(result.current.hasPermission("deal:read")).toBe(true);
      expect(result.current.hasPermission("report:download")).toBe(true);
      expect(result.current.hasPermission("deal:create")).toBe(false);
      expect(result.current.hasPermission("user:manage")).toBe(false);
    });

    it("returns false when no user", () => {
      const { wrapper } = createAuthWrapper({ user: null });
      const { result } = renderHook(() => useAuth(), { wrapper });

      expect(result.current.hasPermission("deal:read")).toBe(false);
    });
  });
});
