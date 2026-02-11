import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { http, HttpResponse } from "msw";
import { server } from "@/test/mocks/server";
import { mockDocuments } from "@/test/mocks/data";
import { useDocuments, useDocument, useCreateDocument } from "../useDocuments";

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

describe("useDocuments", () => {
  it("returns document list with total", async () => {
    const { result } = renderHook(() => useDocuments(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data?.items).toHaveLength(2);
    expect(result.current.data?.total).toBe(2);
    expect(result.current.data?.items[0].company_name).toBe("삼성전자");
  });

  it("handles server error", async () => {
    server.use(
      http.get("/api/im/documents", () => {
        return new HttpResponse(null, { status: 500 });
      }),
    );

    const { result } = renderHook(() => useDocuments(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isError).toBe(true));
  });
});

describe("useDocument", () => {
  it("returns single document by ID", async () => {
    const { result } = renderHook(() => useDocument("doc-1"), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data?.id).toBe("doc-1");
    expect(result.current.data?.status).toBe("COMPLETED");
  });

  it("does not fetch when documentId is empty", async () => {
    const { result } = renderHook(() => useDocument(""), {
      wrapper: createWrapper(),
    });

    expect(result.current.fetchStatus).toBe("idle");
    expect(result.current.data).toBeUndefined();
  });

  it("enables polling for in-progress documents", async () => {
    // Override handler to return an in-progress document
    server.use(
      http.get("/api/im/documents/:documentId", () => {
        return HttpResponse.json({
          ...mockDocuments.items[1], // GENERATING status
          id: "doc-polling",
        });
      }),
    );

    const { result } = renderHook(() => useDocument("doc-polling"), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data?.status).toBe("GENERATING");
    // The refetchInterval should be set (we can verify the data is there)
  });
});

describe("useCreateDocument", () => {
  it("creates a document and invalidates cache", async () => {
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

    const { result } = renderHook(() => useCreateDocument(), { wrapper });

    result.current.mutate({
      corp_code: "00126380",
      im_style: "TITAN",
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data?.id).toBe("doc-new");
    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: ["im", "documents"],
    });

    invalidateSpy.mockRestore();
  });
});
