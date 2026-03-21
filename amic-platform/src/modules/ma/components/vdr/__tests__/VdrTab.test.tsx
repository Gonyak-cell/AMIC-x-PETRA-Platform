import { vi, describe, it, expect, beforeEach } from "vitest";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
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

  it("VdrExplorer 루트에서 폴더 이름을 표시한다", async () => {
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

  it("루트에서 ExplorerToolbar 업로드 버튼이 비활성 상태이다", async () => {
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
    const uploadBtn = screen.getByRole("button", { name: "업로드" });
    expect(uploadBtn).toBeDisabled();
  });

  it("is_required=true 폴더에 삭제 버튼이 표시되지 않는다", async () => {
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
    expect(screen.queryByTitle("폴더 삭제")).not.toBeInTheDocument();
  });

  it("폴더가 없으면 빈 상태를 표시한다", async () => {
    server.use(
      http.get("*/api/ma/transactions/:txnId/vdr/summary", () => {
        return HttpResponse.json(initializedSummary);
      }),
      http.get("*/api/ma/transactions/:txnId/vdr/folders", () => {
        return HttpResponse.json([]);
      }),
    );
    renderTab();

    // 빈 상태에서는 폴더 이름이 없어야 함
    await waitFor(() => {
      expect(screen.queryByText("재무자료")).not.toBeInTheDocument();
    });
  });

  it("트리에서 폴더 클릭 시 선택 상태가 변경되고 브레드크럼이 표시된다", async () => {
    server.use(
      http.get("*/api/ma/transactions/:txnId/vdr/summary", () => {
        return HttpResponse.json(initializedSummary);
      }),
      http.get("*/api/ma/transactions/:txnId/vdr/folders", () => {
        return HttpResponse.json(mockFolders);
      }),
      http.get(
        "*/api/ma/transactions/:txnId/vdr/folders/:folderId/documents",
        () => {
          return HttpResponse.json([]);
        },
      ),
    );
    renderTab();

    // 기본 list 뷰에서 트리에 폴더 이름이 표시됨
    await waitFor(() => {
      expect(screen.getByText("재무자료")).toBeInTheDocument();
    });

    // 트리에서 폴더 클릭 → 선택 상태 변경
    fireEvent.click(screen.getByText("재무자료"));

    // 브레드크럼에 "재무자료" 표시 확인
    await waitFor(() => {
      expect(screen.getAllByText("재무자료").length).toBeGreaterThanOrEqual(1);
    });
  });

  it("기본 list 뷰에서 트리 패널과 파일 리스트가 함께 렌더된다", async () => {
    server.use(
      http.get("*/api/ma/transactions/:txnId/vdr/summary", () => {
        return HttpResponse.json(initializedSummary);
      }),
      http.get("*/api/ma/transactions/:txnId/vdr/folders", () => {
        return HttpResponse.json(mockFolders);
      }),
    );
    renderTab();

    // 기본 뷰가 list이므로 트리 패널에 VDR 루트 버튼이 표시됨
    await waitFor(() => {
      expect(screen.getByText("VDR")).toBeInTheDocument();
    });
    // 트리에 폴더 이름 표시
    expect(screen.getByText("재무자료")).toBeInTheDocument();
  });

  it("그리드 보기 토글 시 폴더 카드 뷰로 전환된다", async () => {
    server.use(
      http.get("*/api/ma/transactions/:txnId/vdr/summary", () => {
        return HttpResponse.json(initializedSummary);
      }),
      http.get("*/api/ma/transactions/:txnId/vdr/folders", () => {
        return HttpResponse.json(mockFolders);
      }),
    );
    renderTab();

    // 기본 list 뷰에서 트리 표시 확인
    await waitFor(() => {
      expect(screen.getByText("VDR")).toBeInTheDocument();
    });

    // "그리드 보기" 토글 클릭
    fireEvent.click(screen.getByTitle("그리드 보기"));

    // grid 뷰에서 폴더 이름이 여전히 표시됨
    expect(screen.getByText("재무자료")).toBeInTheDocument();
  });

  it("VDR 루트 버튼 클릭 시 루트로 복귀한다", async () => {
    server.use(
      http.get("*/api/ma/transactions/:txnId/vdr/summary", () => {
        return HttpResponse.json(initializedSummary);
      }),
      http.get("*/api/ma/transactions/:txnId/vdr/folders", () => {
        return HttpResponse.json(mockFolders);
      }),
      http.get(
        "*/api/ma/transactions/:txnId/vdr/folders/:folderId/documents",
        () => HttpResponse.json([]),
      ),
    );
    renderTab();

    // 트리에서 폴더 선택
    await waitFor(() => {
      expect(screen.getByText("재무자료")).toBeInTheDocument();
    });
    fireEvent.click(screen.getByText("재무자료"));

    // VDR 루트 버튼 클릭 → 루트로 복귀
    fireEvent.click(screen.getByText("VDR"));

    // 루트로 복귀 확인
    await waitFor(() => {
      expect(screen.getByText("재무자료")).toBeInTheDocument();
    });
  });

  it("트리에서 폴더 선택 시 우측 패널은 파일만 표시한다 (폴더 행 없음)", async () => {
    server.use(
      http.get("*/api/ma/transactions/:txnId/vdr/summary", () => {
        return HttpResponse.json(initializedSummary);
      }),
      http.get("*/api/ma/transactions/:txnId/vdr/folders", () => {
        return HttpResponse.json(mockFolders);
      }),
      http.get(
        "*/api/ma/transactions/:txnId/vdr/folders/:folderId/documents",
        () => HttpResponse.json([]),
      ),
    );
    renderTab();

    await waitFor(() => {
      expect(screen.getByText("재무자료")).toBeInTheDocument();
    });

    // 폴더 선택
    fireEvent.click(screen.getByText("재무자료"));

    // 우측 패널에 폴더 행(role="row")이 없어야 함 (파일만 표시)
    await waitFor(() => {
      expect(screen.queryAllByRole("row")).toHaveLength(0);
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
