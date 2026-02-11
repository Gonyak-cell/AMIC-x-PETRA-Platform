import { type ReactElement, type ReactNode } from "react";
import { render, type RenderOptions } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { AuthContext, type AuthContextValue } from "@/components/auth/AuthContext";
import { mockUser } from "./mocks/data";

export function createTestQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false, gcTime: 0 },
      mutations: { retry: false },
    },
  });
}

export function createMockAuthContext(
  overrides: Partial<AuthContextValue> = {},
): AuthContextValue {
  return {
    user: mockUser,
    isAuthenticated: true,
    isLoading: false,
    setAuthState: vi.fn(),
    ...overrides,
  };
}

interface WrapperOptions {
  queryClient?: QueryClient;
  authContext?: Partial<AuthContextValue>;
  initialEntries?: string[];
}

function createWrapper({
  queryClient,
  authContext,
  initialEntries = ["/"],
}: WrapperOptions = {}) {
  const client = queryClient ?? createTestQueryClient();
  const auth = createMockAuthContext(authContext);

  return function Wrapper({ children }: { children: ReactNode }) {
    return (
      <QueryClientProvider client={client}>
        <MemoryRouter initialEntries={initialEntries}>
          <AuthContext.Provider value={auth}>{children}</AuthContext.Provider>
        </MemoryRouter>
      </QueryClientProvider>
    );
  };
}

export function renderWithProviders(
  ui: ReactElement,
  options: WrapperOptions & Omit<RenderOptions, "wrapper"> = {},
) {
  const { queryClient, authContext, initialEntries, ...renderOptions } = options;
  const wrapper = createWrapper({ queryClient, authContext, initialEntries });
  return {
    ...render(ui, { wrapper, ...renderOptions }),
    queryClient: queryClient ?? createTestQueryClient(),
  };
}

// Re-export everything from RTL for convenience
export { screen, waitFor, within, act } from "@testing-library/react";
export { default as userEvent } from "@testing-library/user-event";
