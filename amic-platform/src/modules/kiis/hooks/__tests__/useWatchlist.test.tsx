import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { http, HttpResponse } from "msw";
import { server } from "@/test/mocks/server";
import {
  useWatchlist,
  useAddToWatchlist,
  useRemoveFromWatchlist,
  useAlerts,
  useMarkAlertRead,
  useUnreadAlertCount,
} from "../useWatchlist";

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false, gcTime: 0 },
      mutations: { retry: false },
    },
  });
  return {
    wrapper: function Wrapper({ children }: { children: React.ReactNode }) {
      return (
        <QueryClientProvider client={queryClient}>
          {children}
        </QueryClientProvider>
      );
    },
    queryClient,
  };
}

// ── useWatchlist ──

describe("useWatchlist", () => {
  it("returns watchlist items", async () => {
    const { wrapper } = createWrapper();
    const { result } = renderHook(() => useWatchlist(), { wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data?.items).toHaveLength(2);
    expect(result.current.data!.items[0].company_name).toBe("삼성전자");
    expect(result.current.data!.items[1].company_name).toBe("SK하이닉스");
  });

  it("handles server error", async () => {
    server.use(
      http.get("*/api/kiis/watchlist", () => {
        return new HttpResponse(null, { status: 500 });
      }),
    );

    const { wrapper } = createWrapper();
    const { result } = renderHook(() => useWatchlist(), { wrapper });

    await waitFor(() => expect(result.current.isError).toBe(true));
  });
});

// ── useAddToWatchlist ──

describe("useAddToWatchlist", () => {
  it("adds company and invalidates watchlist cache", async () => {
    const { wrapper, queryClient } = createWrapper();
    const invalidateSpy = vi.spyOn(queryClient, "invalidateQueries");

    const { result } = renderHook(() => useAddToWatchlist(), { wrapper });

    result.current.mutate({ company_id: 3, alert_types: ["news"] });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data?.company_id).toBe(3);
    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: ["kiis", "watchlist"],
    });

    invalidateSpy.mockRestore();
  });

  it("handles mutation error", async () => {
    server.use(
      http.post("*/api/kiis/watchlist", () => {
        return new HttpResponse(null, { status: 409 });
      }),
    );

    const { wrapper } = createWrapper();
    const { result } = renderHook(() => useAddToWatchlist(), { wrapper });

    result.current.mutate({ company_id: 1 });

    await waitFor(() => expect(result.current.isError).toBe(true));
  });
});

// ── useRemoveFromWatchlist ──

describe("useRemoveFromWatchlist", () => {
  it("removes company and invalidates watchlist cache", async () => {
    const { wrapper, queryClient } = createWrapper();
    const invalidateSpy = vi.spyOn(queryClient, "invalidateQueries");

    const { result } = renderHook(() => useRemoveFromWatchlist(), { wrapper });

    result.current.mutate(1);

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: ["kiis", "watchlist"],
    });

    invalidateSpy.mockRestore();
  });
});

// ── useAlerts ──

describe("useAlerts", () => {
  it("returns alert items", async () => {
    const { wrapper } = createWrapper();
    const { result } = renderHook(() => useAlerts(), { wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data?.items).toHaveLength(2);
    expect(result.current.data!.items[0].alert_type).toBe("news");
    expect(result.current.data!.items[0].title).toBe("삼성전자 관련 뉴스");
  });

  it("passes pagination params", async () => {
    const { wrapper } = createWrapper();
    const { result } = renderHook(
      () => useAlerts({ page: 1, size: 10 }),
      { wrapper },
    );

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data).toBeDefined();
  });

  it("handles server error", async () => {
    server.use(
      http.get("*/api/kiis/alerts", () => {
        return new HttpResponse(null, { status: 500 });
      }),
    );

    const { wrapper } = createWrapper();
    const { result } = renderHook(() => useAlerts(), { wrapper });

    await waitFor(() => expect(result.current.isError).toBe(true));
  });
});

// ── useMarkAlertRead ──

describe("useMarkAlertRead", () => {
  it("marks alert as read and invalidates both alert caches", async () => {
    const { wrapper, queryClient } = createWrapper();
    const invalidateSpy = vi.spyOn(queryClient, "invalidateQueries");

    const { result } = renderHook(() => useMarkAlertRead(), { wrapper });

    result.current.mutate(101);

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: ["kiis", "alerts"],
    });
    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: ["kiis", "alerts", "unread-count"],
    });

    invalidateSpy.mockRestore();
  });
});

// ── useUnreadAlertCount ──

describe("useUnreadAlertCount", () => {
  it("returns unread alert count", async () => {
    const { wrapper } = createWrapper();
    const { result } = renderHook(() => useUnreadAlertCount(), { wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data?.count).toBe(3);
  });

  it("handles server error", async () => {
    server.use(
      http.get("*/api/kiis/alerts/unread-count", () => {
        return new HttpResponse(null, { status: 500 });
      }),
    );

    const { wrapper } = createWrapper();
    const { result } = renderHook(() => useUnreadAlertCount(), { wrapper });

    await waitFor(() => expect(result.current.isError).toBe(true));
  });
});
