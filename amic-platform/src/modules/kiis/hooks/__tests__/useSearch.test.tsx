import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { http, HttpResponse } from "msw";
import { server } from "@/test/mocks/server";
import { useUnifiedSearch } from "../useSearch";

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

describe("useUnifiedSearch", () => {
  it("returns search results for valid query", async () => {
    const { result } = renderHook(
      () => useUnifiedSearch({ q: "삼성" }),
      { wrapper: createWrapper() },
    );

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data?.total).toBe(2);
    expect(result.current.data?.query).toBe("삼성");
    expect(result.current.data?.items).toHaveLength(2);
    expect(result.current.data?.items[0].index).toBe("companies");
    expect(result.current.data?.items[1].index).toBe("funds");
  });

  it("does not fetch when query is empty", () => {
    const { result } = renderHook(
      () => useUnifiedSearch({ q: "" }),
      { wrapper: createWrapper() },
    );

    expect(result.current.fetchStatus).toBe("idle");
    expect(result.current.data).toBeUndefined();
  });

  it("does not fetch when query is shorter than 2 characters", () => {
    const { result } = renderHook(
      () => useUnifiedSearch({ q: "삼" }),
      { wrapper: createWrapper() },
    );

    expect(result.current.fetchStatus).toBe("idle");
    expect(result.current.data).toBeUndefined();
  });

  it("fetches when query has exactly 2 characters", async () => {
    const { result } = renderHook(
      () => useUnifiedSearch({ q: "삼성" }),
      { wrapper: createWrapper() },
    );

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data?.items).toBeDefined();
  });

  it("passes type filter param", async () => {
    const { result } = renderHook(
      () => useUnifiedSearch({ q: "삼성", type: "companies" }),
      { wrapper: createWrapper() },
    );

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data?.items).toBeDefined();
  });

  it("handles server error", async () => {
    server.use(
      http.get("*/api/kiis/search", () => {
        return new HttpResponse(null, { status: 500 });
      }),
    );

    const { result } = renderHook(
      () => useUnifiedSearch({ q: "삼성" }),
      { wrapper: createWrapper() },
    );

    await waitFor(() => expect(result.current.isError).toBe(true));
  });

  it("handles empty results", async () => {
    server.use(
      http.get("*/api/kiis/search", () => {
        return HttpResponse.json({
          total: 0,
          page: 1,
          size: 20,
          query: "없는검색",
          items: [],
        });
      }),
    );

    const { result } = renderHook(
      () => useUnifiedSearch({ q: "없는검색" }),
      { wrapper: createWrapper() },
    );

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data?.total).toBe(0);
    expect(result.current.data?.items).toHaveLength(0);
  });
});
