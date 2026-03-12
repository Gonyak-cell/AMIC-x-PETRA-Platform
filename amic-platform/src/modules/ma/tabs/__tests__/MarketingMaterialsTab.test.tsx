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
import MarketingMaterialsTab from "../MarketingMaterialsTab";

const defaultAuth: AuthContextValue = {
  user: mockUser,
  isAuthenticated: true,
  isLoading: false,
  setAuthState: vi.fn(),
};

function renderTab(props: Partial<{ txnId: string; canWrite: boolean }> = {}) {
  const queryClient = createTestQueryClient();
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <AuthContext.Provider value={defaultAuth}>
          <MarketingMaterialsTab
            txnId={props.txnId ?? "txn-1"}
            canWrite={props.canWrite ?? true}
          />
        </AuthContext.Provider>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

const mockMaterial = {
  id: "mat-1",
  transaction_id: "txn-1",
  doc_type: "TM",
  title: "테스트 티저",
  project_code: "SE26-TST-01",
  status: "READY",
  error_message: null,
  parameters: null,
  file_path: "/files/teaser.pptx",
  file_name: "teaser.pptx",
  file_size_bytes: 102400,
  distributed_to: null,
  distributed_at: null,
  created_by_email: "test@amic.kr",
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
};

describe("MarketingMaterialsTab", () => {
  beforeEach(() => {
    server.resetHandlers();
  });

  it("로딩 중 Spinner를 표시한다", () => {
    server.use(
      http.get("*/api/ma/transactions/:txnId/marketing-materials", () => {
        return new Promise(() => {}); // never resolves
      }),
    );
    renderTab();
    expect(screen.getByText("마케팅 자료")).toBeInTheDocument();
  });

  it("마케팅 자료가 없으면 빈 상태를 표시한다", async () => {
    server.use(
      http.get("*/api/ma/transactions/:txnId/marketing-materials", () => {
        return HttpResponse.json([]);
      }),
    );
    renderTab();
    await waitFor(() => {
      expect(screen.getByText("마케팅 자료 없음")).toBeInTheDocument();
    });
  });

  it("마케팅 자료를 테이블에 표시한다", async () => {
    server.use(
      http.get("*/api/ma/transactions/:txnId/marketing-materials", () => {
        return HttpResponse.json([mockMaterial]);
      }),
    );
    renderTab();
    await waitFor(() => {
      expect(screen.getByText("테스트 티저")).toBeInTheDocument();
    });
    expect(screen.getByText("TM")).toBeInTheDocument();
    expect(screen.getByText("100 KB")).toBeInTheDocument();
  });

  it("canWrite=true이면 생성 버튼을 표시한다", async () => {
    renderTab({ canWrite: true });
    await waitFor(() => {
      expect(screen.getByText("+ Teaser (TM)")).toBeInTheDocument();
    });
    expect(screen.getByText("+ Discussion (DM)")).toBeInTheDocument();
    expect(screen.getByText("+ Information (IM)")).toBeInTheDocument();
  });

  it("canWrite=false이면 생성 버튼을 숨긴다", async () => {
    renderTab({ canWrite: false });
    await waitFor(() => {
      expect(screen.getByText("마케팅 자료")).toBeInTheDocument();
    });
    expect(screen.queryByText("+ Teaser (TM)")).not.toBeInTheDocument();
    expect(screen.queryByText("+ Discussion (DM)")).not.toBeInTheDocument();
    expect(screen.queryByText("+ Information (IM)")).not.toBeInTheDocument();
  });

  it("READY 상태 자료에 다운로드 버튼을 표시한다", async () => {
    server.use(
      http.get("*/api/ma/transactions/:txnId/marketing-materials", () => {
        return HttpResponse.json([mockMaterial]);
      }),
    );
    renderTab();
    await waitFor(() => {
      expect(screen.getByText("다운로드")).toBeInTheDocument();
    });
  });
});
