import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { http, HttpResponse } from "msw";
import { server } from "@/test/mocks/server";
import { mockImCompany } from "@/test/mocks/data";
import { useCompany, useFetchCompany } from "../useCompanies";

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

describe("useCompany", () => {
  it("returns company data by corp code", async () => {
    const { result } = renderHook(() => useCompany("00126380"), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data?.corp_name).toBe("삼성전자");
    expect(result.current.data?.fetch_status).toBe("COMPLETED");
  });

  it("does not fetch when corpCode is empty", async () => {
    const { result } = renderHook(() => useCompany(""), {
      wrapper: createWrapper(),
    });

    expect(result.current.fetchStatus).toBe("idle");
    expect(result.current.data).toBeUndefined();
  });

  it("enables polling for PENDING status", async () => {
    server.use(
      http.get("*/api/im/companies/:corpCode", () => {
        return HttpResponse.json({
          ...mockImCompany,
          fetch_status: "PENDING",
        });
      }),
    );

    const { result } = renderHook(() => useCompany("00126380"), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data?.fetch_status).toBe("PENDING");
  });
});

describe("useFetchCompany", () => {
  it("creates company and invalidates cache", async () => {
    const queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false, gcTime: 0 },
        mutations: { retry: false },
      },
    });

    const invalidateSpy = vi.spyOn(queryClient, "invalidateQueries");

    const wrapper = ({ children }: { children: React.ReactNode }) => (
      <QueryClientProvider client={queryClient}>
        {children}
      </QueryClientProvider>
    );

    const { result } = renderHook(() => useFetchCompany(), { wrapper });

    result.current.mutate("00126380");

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data?.corp_code).toBe("00126380");
    expect(result.current.data?.fetch_status).toBe("PENDING");
    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: ["im", "companies", "00126380"],
    });

    invalidateSpy.mockRestore();
  });
});
