import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { http, HttpResponse } from "msw";
import { server } from "@/test/mocks/server";
import { mockDeals } from "@/test/mocks/data";
import { useDeals, useCreateDeal, useDeal } from "../useDeals";

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

describe("useDeals", () => {
  it("returns deal list on success", async () => {
    const { result } = renderHook(() => useDeals(), {
      wrapper: createWrapper(),
    });

    expect(result.current.isLoading).toBe(true);

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data).toHaveLength(2);
    expect(result.current.data![0].name).toBe("Project Alpha");
    expect(result.current.data![1].name).toBe("Project Beta");
  });

  it("returns error on server failure", async () => {
    server.use(
      http.get("/api/fdd/deals", () => {
        return new HttpResponse(null, { status: 500 });
      }),
    );

    const { result } = renderHook(() => useDeals(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isError).toBe(true));
  });
});

describe("useDeal", () => {
  it("returns single deal by ID", async () => {
    const { result } = renderHook(() => useDeal("deal-1"), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data?.id).toBe("deal-1");
    expect(result.current.data?.name).toBe("Project Alpha");
  });

  it("does not fetch when dealId is empty", async () => {
    const { result } = renderHook(() => useDeal(""), {
      wrapper: createWrapper(),
    });

    // With enabled: !!dealId, the query should not run
    expect(result.current.fetchStatus).toBe("idle");
    expect(result.current.data).toBeUndefined();
  });
});

describe("useCreateDeal", () => {
  it("creates a deal and invalidates cache", async () => {
    const queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false, gcTime: 0 },
        mutations: { retry: false },
      },
    });

    // Pre-populate the deals cache
    queryClient.setQueryData(["fdd", "deals"], mockDeals);

    const invalidateSpy = vi.spyOn(queryClient, "invalidateQueries");

    const wrapper = ({ children }: { children: React.ReactNode }) => (
      <QueryClientProvider client={queryClient}>
        {children}
      </QueryClientProvider>
    );

    const { result } = renderHook(() => useCreateDeal(), { wrapper });

    result.current.mutate({
      name: "New Deal",
      target_company_name: "Test Target Co",
      deal_type: "LOCKED_BOX",
      base_currency: "USD",
      reference_date: "2025-12-31",
      period_start: "2025-01-01",
      period_end: "2025-12-31",
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data?.id).toBe("deal-new");
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ["fdd", "deals"] });

    invalidateSpy.mockRestore();
  });
});
