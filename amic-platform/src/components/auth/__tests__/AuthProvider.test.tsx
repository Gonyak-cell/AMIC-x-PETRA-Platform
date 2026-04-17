import { render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { http, HttpResponse } from "msw";
import { useAuth } from "@/hooks/useAuth";
import { server } from "@/test/mocks/server";
import AuthProvider from "../AuthProvider";

function AuthProbe() {
  const { isAuthenticated, isLoading, user } = useAuth();
  return (
    <div>
      <div data-testid="auth-loading">{String(isLoading)}</div>
      <div data-testid="auth-authenticated">{String(isAuthenticated)}</div>
      <div data-testid="auth-user">{user?.email ?? "none"}</div>
    </div>
  );
}

function renderWithProviders(initialPath: string) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });

  return render(
    <MemoryRouter initialEntries={[initialPath]}>
      <QueryClientProvider client={queryClient}>
        <AuthProvider>
          <AuthProbe />
        </AuthProvider>
      </QueryClientProvider>
    </MemoryRouter>,
  );
}

describe("AuthProvider", () => {
  it("skips auth bootstrap on login routes", async () => {
    let authMeHits = 0;
    server.use(
      http.get("*/api/:module/auth/me", () => {
        authMeHits += 1;
        return new HttpResponse(null, { status: 401 });
      }),
    );

    renderWithProviders("/login");

    await waitFor(() => {
      expect(screen.getByTestId("auth-loading")).toHaveTextContent("false");
    });
    expect(screen.getByTestId("auth-authenticated")).toHaveTextContent("false");
    expect(authMeHits).toBe(0);
  });

  it("uses MA auth on MA routes", async () => {
    let maHits = 0;
    let fddHits = 0;

    server.use(
      http.get("*/api/ma/auth/me", () => {
        maHits += 1;
        return new HttpResponse(null, { status: 401 });
      }),
      http.get("*/api/fdd/auth/me", () => {
        fddHits += 1;
        return new HttpResponse(null, { status: 401 });
      }),
    );

    renderWithProviders("/ma/transactions");

    await waitFor(() => {
      expect(screen.getByTestId("auth-loading")).toHaveTextContent("false");
    });
    expect(screen.getByTestId("auth-authenticated")).toHaveTextContent("false");
    expect(maHits).toBe(1);
    expect(fddHits).toBe(0);
  });
});
