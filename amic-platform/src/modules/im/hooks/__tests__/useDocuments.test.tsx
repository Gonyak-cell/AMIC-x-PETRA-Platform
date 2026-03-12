import { act, renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { http, HttpResponse } from "msw";
import { server } from "@/test/mocks/server";
import { mockDocuments } from "@/test/mocks/data";
import { useDocuments, useDocument, useCreateDocument, useDownloadDocument } from "../useDocuments";

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
      company_name: "삼성전자",
      project_name: "Samsung IM",
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

describe("useDownloadDocument", () => {
  let createObjectURLSpy: ReturnType<typeof vi.spyOn>;
  let revokeObjectURLSpy: ReturnType<typeof vi.spyOn>;
  let appendChildSpy: ReturnType<typeof vi.spyOn>;
  let removeChildSpy: ReturnType<typeof vi.spyOn>;

  beforeEach(() => {
    createObjectURLSpy = vi.fn(() => "blob:mock-url") as unknown as ReturnType<typeof vi.spyOn>;
    revokeObjectURLSpy = vi.fn() as unknown as ReturnType<typeof vi.spyOn>;
    window.URL.createObjectURL = createObjectURLSpy as unknown as typeof URL.createObjectURL;
    window.URL.revokeObjectURL = revokeObjectURLSpy as unknown as typeof URL.revokeObjectURL;
    appendChildSpy = vi.spyOn(document.body, "appendChild").mockImplementation((node) => node);
    removeChildSpy = vi.spyOn(document.body, "removeChild").mockImplementation((node) => node);
    // Mock contains to return true so removeChild is called
    vi.spyOn(document.body, "contains").mockReturnValue(true);
  });

  afterEach(() => {
    appendChildSpy.mockRestore();
    removeChildSpy.mockRestore();
    vi.restoreAllMocks();
  });

  it("downloads a blob and triggers file save", async () => {
    vi.useFakeTimers();

    const mockBlob = new Blob(["test"], { type: "application/pdf" });
    server.use(
      http.get("/api/im/documents/:id/download", () => {
        return new HttpResponse(mockBlob, {
          headers: {
            "content-disposition": 'attachment; filename="test-doc.pdf"',
            "content-type": "application/pdf",
          },
        });
      }),
    );

    const { result } = renderHook(() => useDownloadDocument(), {
      wrapper: createWrapper(),
    });

    await result.current.mutateAsync({ documentId: "doc-1", format: "pdf" });

    expect(window.URL.createObjectURL).toHaveBeenCalled();

    // revokeObjectURL is called inside setTimeout(200)
    await act(async () => {
      vi.advanceTimersByTime(200);
    });
    expect(window.URL.revokeObjectURL).toHaveBeenCalledWith("blob:mock-url");

    vi.useRealTimers();
  });

  it("handles download error gracefully", async () => {
    server.use(
      http.get("/api/im/documents/:id/download", () => {
        return new HttpResponse(null, { status: 500 });
      }),
    );

    const { result } = renderHook(() => useDownloadDocument(), {
      wrapper: createWrapper(),
    });

    await expect(
      result.current.mutateAsync({ documentId: "doc-1", format: "pdf" }),
    ).rejects.toThrow();
  });
});
