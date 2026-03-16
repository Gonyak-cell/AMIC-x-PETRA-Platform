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

  it("폴더가 없으면 빈 상태 메시지를 표시한다", async () => {
    server.use(
      http.get("*/api/ma/transactions/:txnId/vdr/summary", () => {
        return HttpResponse.json(initializedSummary);
      }),
      http.get("*/api/ma/transactions/:txnId/vdr/folders", () => {
        return HttpResponse.json([]);
      }),
    );
    renderTab();

    await waitFor(() => {
      expect(
        screen.getByText("폴더를 생성하여 문서를 정리하세요"),
      ).toBeInTheDocument();
    });
  });

  it("폴더 클릭 시 하위 폴더와 브레드크럼을 함께 표시한다 (회귀)", async () => {
    // 실제 서버 응답 형태: 루트 폴더의 children 배열에 하위 폴더 중첩
    const foldersWithChild = [
      {
        id: "folder-1",
        transaction_id: "txn-1",
        name: "재무자료",
        category: "FINANCIAL",
        parent_id: null,
        children: [
          {
            id: "folder-2",
            transaction_id: "txn-1",
            name: "감사보고서",
            category: "FINANCIAL",
            parent_id: "folder-1",
            children: [],
            document_count: 0,
            is_required: false,
            order_index: 0,
            created_at: "2026-01-01T00:00:00Z",
            updated_at: "2026-01-01T00:00:00Z",
          },
        ],
        document_count: 1,
        is_required: false,
        order_index: 0,
        created_at: "2026-01-01T00:00:00Z",
        updated_at: "2026-01-01T00:00:00Z",
      },
    ];
    server.use(
      http.get("*/api/ma/transactions/:txnId/vdr/summary", () => {
        return HttpResponse.json(initializedSummary);
      }),
      http.get("*/api/ma/transactions/:txnId/vdr/folders", () => {
        return HttpResponse.json(foldersWithChild);
      }),
      http.get(
        "*/api/ma/transactions/:txnId/vdr/folders/:folderId/documents",
        () => {
          return HttpResponse.json([]);
        },
      ),
    );
    renderTab();

    // 루트에서 "재무자료" 폴더 렌더링 확인
    await waitFor(() => {
      expect(screen.getByText("재무자료")).toBeInTheDocument();
    });

    // 재무자료 폴더 클릭 → 하위 뷰로 진입
    fireEvent.click(screen.getByText("재무자료"));

    // 하위 폴더 "감사보고서" 가 렌더링되어야 함
    await waitFor(() => {
      expect(screen.getByText("감사보고서")).toBeInTheDocument();
    });

    // 브레드크럼에 "재무자료" 표시 확인
    expect(screen.getAllByText("재무자료").length).toBeGreaterThanOrEqual(1);
  });

  it("3단계 중첩 트리에서 손자 폴더까지 탐색된다", async () => {
    // 서버 응답: 루트 → 자식 → 손자 (3단계 중첩)
    const deepTree = [
      {
        id: "f-root",
        transaction_id: "txn-1",
        name: "재무자료",
        category: "FINANCIAL",
        parent_id: null,
        children: [
          {
            id: "f-child",
            transaction_id: "txn-1",
            name: "감사보고서",
            category: "FINANCIAL",
            parent_id: "f-root",
            children: [
              {
                id: "f-grandchild",
                transaction_id: "txn-1",
                name: "2023년도",
                category: "FINANCIAL",
                parent_id: "f-child",
                children: [],
                document_count: 0,
                is_required: false,
                order_index: 0,
                created_at: "2026-01-01T00:00:00Z",
                updated_at: "2026-01-01T00:00:00Z",
              },
            ],
            document_count: 0,
            is_required: false,
            order_index: 0,
            created_at: "2026-01-01T00:00:00Z",
            updated_at: "2026-01-01T00:00:00Z",
          },
        ],
        document_count: 0,
        is_required: false,
        order_index: 0,
        created_at: "2026-01-01T00:00:00Z",
        updated_at: "2026-01-01T00:00:00Z",
      },
    ];
    server.use(
      http.get("*/api/ma/transactions/:txnId/vdr/summary", () => {
        return HttpResponse.json(initializedSummary);
      }),
      http.get("*/api/ma/transactions/:txnId/vdr/folders", () => {
        return HttpResponse.json(deepTree);
      }),
      http.get(
        "*/api/ma/transactions/:txnId/vdr/folders/:folderId/documents",
        () => HttpResponse.json([]),
      ),
    );
    renderTab();

    // 루트 폴더 진입
    await waitFor(() =>
      expect(screen.getByText("재무자료")).toBeInTheDocument(),
    );
    fireEvent.click(screen.getByText("재무자료"));

    // 자식 폴더 표시 확인 후 진입
    await waitFor(() =>
      expect(screen.getByText("감사보고서")).toBeInTheDocument(),
    );
    fireEvent.click(screen.getByText("감사보고서"));

    // 손자 폴더 표시 확인
    await waitFor(() =>
      expect(screen.getByText("2023년도")).toBeInTheDocument(),
    );
  });

  it("브레드크럼 상위 폴더 클릭 시 해당 뷰로 복귀한다", async () => {
    const twoLevelTree = [
      {
        id: "f-root",
        transaction_id: "txn-1",
        name: "재무자료",
        category: "FINANCIAL",
        parent_id: null,
        children: [
          {
            id: "f-child",
            transaction_id: "txn-1",
            name: "감사보고서",
            category: "FINANCIAL",
            parent_id: "f-root",
            children: [],
            document_count: 0,
            is_required: false,
            order_index: 0,
            created_at: "2026-01-01T00:00:00Z",
            updated_at: "2026-01-01T00:00:00Z",
          },
        ],
        document_count: 0,
        is_required: false,
        order_index: 0,
        created_at: "2026-01-01T00:00:00Z",
        updated_at: "2026-01-01T00:00:00Z",
      },
    ];
    server.use(
      http.get("*/api/ma/transactions/:txnId/vdr/summary", () => {
        return HttpResponse.json(initializedSummary);
      }),
      http.get("*/api/ma/transactions/:txnId/vdr/folders", () => {
        return HttpResponse.json(twoLevelTree);
      }),
      http.get(
        "*/api/ma/transactions/:txnId/vdr/folders/:folderId/documents",
        () => HttpResponse.json([]),
      ),
    );
    renderTab();

    // 루트 → 재무자료 진입
    await waitFor(() =>
      expect(screen.getByText("재무자료")).toBeInTheDocument(),
    );
    fireEvent.click(screen.getByText("재무자료"));

    // 자식 폴더 표시 확인
    await waitFor(() =>
      expect(screen.getByText("감사보고서")).toBeInTheDocument(),
    );

    // 브레드크럼 홈(VDR 루트) 버튼 클릭 → 루트로 복귀
    fireEvent.click(screen.getByRole("button", { name: "홈" }));

    // 루트 폴더 그리드로 복귀 확인 (감사보고서는 사라짐)
    await waitFor(() =>
      expect(screen.queryByText("감사보고서")).not.toBeInTheDocument(),
    );
    expect(screen.getByText("재무자료")).toBeInTheDocument();
  });

  it("목록 보기 토글 시 탐색기 뷰(트리+파일 리스트)가 렌더된다", async () => {
    server.use(
      http.get("*/api/ma/transactions/:txnId/vdr/summary", () => {
        return HttpResponse.json(initializedSummary);
      }),
      http.get("*/api/ma/transactions/:txnId/vdr/folders", () => {
        return HttpResponse.json(mockFolders);
      }),
    );
    renderTab();

    // 초기 grid 뷰에서 폴더 카드 표시 확인
    await waitFor(() => {
      expect(screen.getByText("재무자료")).toBeInTheDocument();
    });

    // "목록 보기" 토글 클릭
    fireEvent.click(screen.getByTitle("목록 보기"));

    // list 뷰에서 폴더 행이 표시되는지 확인 (role="row")
    await waitFor(() => {
      expect(screen.getByRole("row")).toBeInTheDocument();
    });
    // 트리+리스트 양쪽에 폴더 이름이 표시되는지 확인
    expect(screen.getAllByText("재무자료").length).toBeGreaterThanOrEqual(1);
  });

  it("list 뷰에서 폴더 단일 클릭으로 하위 탐색된다", async () => {
    const foldersWithChild = [
      {
        id: "folder-1",
        transaction_id: "txn-1",
        name: "재무자료",
        category: "FINANCIAL",
        parent_id: null,
        children: [
          {
            id: "folder-2",
            transaction_id: "txn-1",
            name: "감사보고서",
            category: "FINANCIAL",
            parent_id: "folder-1",
            children: [],
            document_count: 0,
            is_required: false,
            order_index: 0,
            created_at: "2026-01-01T00:00:00Z",
            updated_at: "2026-01-01T00:00:00Z",
          },
        ],
        document_count: 1,
        is_required: false,
        order_index: 0,
        created_at: "2026-01-01T00:00:00Z",
        updated_at: "2026-01-01T00:00:00Z",
      },
    ];
    server.use(
      http.get("*/api/ma/transactions/:txnId/vdr/summary", () => {
        return HttpResponse.json(initializedSummary);
      }),
      http.get("*/api/ma/transactions/:txnId/vdr/folders", () => {
        return HttpResponse.json(foldersWithChild);
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

    // list 뷰로 전환
    fireEvent.click(screen.getByTitle("목록 보기"));

    // list 뷰에서 폴더 행 렌더 확인
    await waitFor(() => {
      expect(screen.getByRole("row")).toBeInTheDocument();
    });

    // 단일 클릭으로 폴더 행 진입 (grid와 동일한 UX)
    fireEvent.click(screen.getByRole("row"));

    // 하위 폴더 "감사보고서" 표시 확인
    await waitFor(() => {
      expect(screen.getByText("감사보고서")).toBeInTheDocument();
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
