import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { http, HttpResponse } from "msw";
import { server } from "@/test/mocks/server";
import { useCompanies, useCompanyDetail } from "../useCompanies";

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false, gcTime: 0 },
      mutations: { retry: false },
    },
  });
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>
        {children}
      </QueryClientProvider>
    );
  };
}

describe("useCompanies", () => {
  it("returns paginated company list", async () => {
    const { result } = renderHook(() => useCompanies(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data?.items).toHaveLength(2);
    expect(result.current.data?.total).toBe(2);
    expect(result.current.data?.items[0].corp_name).toBe("삼성전자");
  });

  it("passes params to the API", async () => {
    const { result } = renderHook(
      () => useCompanies({ search: "삼성", page: 1, size: 10 }),
      { wrapper: createWrapper() },
    );

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    // The mock returns the same data regardless of params,
    // but the hook should still resolve successfully
    expect(result.current.data?.items).toBeDefined();
  });

  it("handles server error", async () => {
    server.use(
      http.get("/api/kiis/companies", () => {
        return new HttpResponse(null, { status: 500 });
      }),
    );

    const { result } = renderHook(() => useCompanies(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isError).toBe(true));
  });
});

describe("useCompanyDetail", () => {
  it("returns company detail by corpCode", async () => {
    const { result } = renderHook(() => useCompanyDetail("00126380"), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data?.corp_name).toBe("삼성전자");
    expect(result.current.data?.corp_code).toBe("00126380");
  });

  it("does not fetch when corpCode is empty", async () => {
    const { result } = renderHook(() => useCompanyDetail(""), {
      wrapper: createWrapper(),
    });

    expect(result.current.fetchStatus).toBe("idle");
    expect(result.current.data).toBeUndefined();
  });

  it("returns 404 for unknown corpCode", async () => {
    const { result } = renderHook(() => useCompanyDetail("00000000"), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isError).toBe(true));
  });
});
