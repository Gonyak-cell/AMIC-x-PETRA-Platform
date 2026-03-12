import { vi, describe, it, expect, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { QueryClientProvider } from "@tanstack/react-query";
import { http, HttpResponse } from "msw";
import { server } from "@/test/mocks/server";
import {
  AuthContext,
  type AuthContextValue,
} from "@/components/auth/AuthContext";
import { mockUser } from "@/test/mocks/data";
import { createTestQueryClient } from "@/test/test-utils";
import VdrTab from "../VdrTab";

const defaultAuth: AuthContextValue = {
  user: mockUser,
  isAuthenticated: true,
  isLoading: false,
  setAuthState: vi.fn(),
};

/** VDR summary: 초기화 완료 + 폴더/문서 존재 */
const initializedSummary = {
  total_folders: 2,
  total_documents: 5,
  total_size_bytes: 1024000,
  vdr_initialized: true,
  initialized: true,
};

const mockFolders = [
  {
    id: "folder-1",
    transaction_id: "txn-1",
    name: "재무자료",
    category: "FINANCIAL",
    parent_id: null,
    children: [],
    document_count: 3,
    is_required: true,
    order_index: 0,
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
  },
];

function renderTab(txnId = "txn-1") {
  const queryClient = createTestQueryClient();
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <AuthContext.Provider value={defaultAuth}>
          <VdrTab txnId={txnId} />
        </AuthContext.Provider>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  server.resetHandlers();
});

describe("VdrTab", () => {
  it("로딩 중 '불러오는 중...' 텍스트를 표시한다", () => {
    server.use(
      http.get("*/api/ma/transactions/:txnId/vdr/summary", () => {
        return new Promise(() => {}); // never resolves
      }),
    );
    renderTab();
    expect(screen.getByText("불러오는 중...")).toBeInTheDocument();
  });

  it("초기화 완료 시 '문서 관리'와 '접근 현황' 서브탭을 표시한다", async () => {
    server.use(
      http.get("*/api/ma/transactions/:txnId/vdr/summary", () => {
        return HttpResponse.json(initializedSummary);
      }),
      http.get("*/api/ma/transactions/:txnId/vdr/folders", () => {
        return HttpResponse.json(mockFolders);
      }),
    );
    renderTab();

    await waitFor(() => {
      expect(screen.getByText("문서 관리")).toBeInTheDocument();
    });
    expect(screen.getByText("접근 현황")).toBeInTheDocument();
  });

  it("초기화 완료 시 '빠른 업로드' 버튼을 표시한다", async () => {
    server.use(
      http.get("*/api/ma/transactions/:txnId/vdr/summary", () => {
        return HttpResponse.json(initializedSummary);
      }),
      http.get("*/api/ma/transactions/:txnId/vdr/folders", () => {
        return HttpResponse.json(mockFolders);
      }),
    );
    renderTab();

    await waitFor(() => {
      expect(screen.getByText("빠른 업로드")).toBeInTheDocument();
    });
  });

  it("폴더 트리에 폴더 이름을 표시한다", async () => {
    server.use(
      http.get("*/api/ma/transactions/:txnId/vdr/summary", () => {
        return HttpResponse.json(initializedSummary);
      }),
      http.get("*/api/ma/transactions/:txnId/vdr/folders", () => {
        return HttpResponse.json(mockFolders);
      }),
    );
    renderTab();

    await waitFor(() => {
      expect(screen.getByText("재무자료")).toBeInTheDocument();
    });
  });

  it("미초기화 상태에서 vdr/init을 호출한다", async () => {
    let initCalled = false;
    server.use(
      http.get("*/api/ma/transactions/:txnId/vdr/summary", () => {
        return HttpResponse.json({
          total_folders: 0,
          total_documents: 0,
          total_size_bytes: 0,
          vdr_initialized: false,
          initialized: false,
        });
      }),
      http.post("*/api/ma/transactions/:txnId/vdr/init", () => {
        initCalled = true;
        return HttpResponse.json({ initialized: true });
      }),
    );
    renderTab();

    await waitFor(
      () => {
        expect(initCalled).toBe(true);
      },
      { timeout: 3000 },
    );
  });
});
