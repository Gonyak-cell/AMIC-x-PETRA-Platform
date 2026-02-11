import { renderHook, act } from "@testing-library/react";
import type { ReactNode } from "react";
import { AuthContext, type AuthContextValue } from "@/components/auth/AuthContext";
import { useAuth, getAccessToken, setTokens, clearTokens } from "../useAuth";
import { mockUser, mockViewerUser } from "@/test/mocks/data";

function createAuthWrapper(overrides: Partial<AuthContextValue> = {}) {
  const value: AuthContextValue = {
    user: mockUser,
    isAuthenticated: true,
    isLoading: false,
    setAuthState: vi.fn(),
    ...overrides,
  };

  return {
    value,
    wrapper: ({ children }: { children: ReactNode }) => (
      <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
    ),
  };
}

describe("useAuth", () => {
  it("throws when used outside AuthProvider", () => {
    // Suppress console.error for the expected error
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

  it("logout clears tokens and resets state", () => {
    setTokens("access", "refresh");
    expect(getAccessToken()).toBe("access");

    const { wrapper, value } = createAuthWrapper();
    const { result } = renderHook(() => useAuth(), { wrapper });

    act(() => {
      result.current.logout();
    });

    expect(getAccessToken()).toBeNull();
    expect(value.setAuthState).toHaveBeenCalledWith({
      user: null,
      isAuthenticated: false,
      isLoading: false,
    });
  });

  describe("hasPermission", () => {
    it("ADMIN has all permissions", () => {
      const { wrapper } = createAuthWrapper({ user: mockUser }); // ADMIN
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

describe("token helpers", () => {
  it("setTokens and getAccessToken work", () => {
    setTokens("my-access", "my-refresh");
    expect(getAccessToken()).toBe("my-access");
  });

  it("clearTokens removes both tokens", () => {
    setTokens("a", "b");
    clearTokens();
    expect(getAccessToken()).toBeNull();
  });
});
