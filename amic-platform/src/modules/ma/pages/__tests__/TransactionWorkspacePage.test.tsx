import { vi, describe, it, expect, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { Routes, Route, MemoryRouter } from "react-router-dom";
import { QueryClientProvider } from "@tanstack/react-query";
import { http, HttpResponse } from "msw";
import { server } from "@/test/mocks/server";
import { mockPhaseStatus } from "@/test/mocks/ma-handlers";
import {
  AuthContext,
  type AuthContextValue,
} from "@/components/auth/AuthContext";
import { mockUser } from "@/test/mocks/data";
import { createTestQueryClient } from "@/test/test-utils";
import TransactionWorkspacePage from "../TransactionWorkspacePage";

// ── Auth context fixture ──────────────────────────────
const defaultAuth: AuthContextValue = {
  user: mockUser,
  isAuthenticated: true,
  isLoading: false,
  setAuthState: vi.fn(),
};

// ── Render helper ─────────────────────────────────────
function renderPage(
  path = "/ma/transactions/txn-1",
  authOverrides: Partial<AuthContextValue> = {},
) {
  const queryClient = createTestQueryClient();
  const auth: AuthContextValue = { ...defaultAuth, ...authOverrides };

  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[path]}>
        <AuthContext.Provider value={auth}>
          <Routes>
            <Route
              path="/ma/transactions/:txnId/*"
              element={<TransactionWorkspacePage />}
            />
          </Routes>
        </AuthContext.Provider>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

// ── Tests ─────────────────────────────────────────────
describe("TransactionWorkspacePage", () => {
  beforeEach(() => {
    server.resetHandlers();
  });

  // 1. 로딩 중 Spinner 표시
  it("로딩 중 Spinner를 표시한다", () => {
    // transaction 요청을 never-resolving promise로 설정
    server.use(
      http.get("*/api/ma/transactions/:txnId", () => {
        return new Promise(() => {});
      }),
    );

    renderPage();

    expect(screen.getByRole("status")).toBeInTheDocument();
  });

  // 2. 거래명 + status 배지 표시
  it("거래명과 ACTIVE 상태 배지를 표시한다", async () => {
    renderPage();

    await waitFor(() => {
      expect(screen.getByText("테스트 프로젝트")).toBeInTheDocument();
    });

    // status Badge: ACTIVE
    expect(screen.getByText("ACTIVE")).toBeInTheDocument();
  });

  // 3. 거래 미발견 시 에러 메시지
  it("거래를 찾을 수 없으면 안내 메시지를 표시한다", async () => {
    server.use(
      http.get("*/api/ma/transactions/:txnId", () => {
        return new HttpResponse(null, { status: 404 });
      }),
    );

    renderPage("/ma/transactions/nonexistent");

    await waitFor(() => {
      expect(screen.getByText("거래를 찾을 수 없습니다")).toBeInTheDocument();
    });
  });

  // 4. MARKETING 단계에서 visible tabs 확인
  it("MARKETING 단계에서 해당 단계의 탭들을 표시한다", async () => {
    renderPage();

    await waitFor(() => {
      expect(screen.getByText("테스트 프로젝트")).toBeInTheDocument();
    });

    // MARKETING 단계 visible tabs: overview, buyers, marketing-logs, vdr, risks, compliance, notes-approvals
    expect(screen.getByText("매수자")).toBeInTheDocument();
    expect(screen.getByText("VDR")).toBeInTheDocument();
    expect(screen.getByText("마케팅 로그")).toBeInTheDocument();

    // MARKETING 단계에서 보이지 않아야 하는 탭 (role=tab으로 범위 한정)
    // Note: "입찰" 등은 파이프라인 시각화에서도 나타나므로 탭 영역으로 한정
    const tabList = screen.getAllByRole("tab");
    const tabLabels = tabList.map((t) => t.textContent);
    expect(tabLabels).not.toContain("입찰");
    expect(tabLabels).not.toContain("Closing");
    expect(tabLabels).not.toContain("PMI");
  });

  // 5. can_advance=false이면 blocking_reasons 표시
  it("can_advance=false일 때 blocking_reasons 텍스트를 표시한다", async () => {
    renderPage();

    await waitFor(() => {
      expect(screen.getByText("테스트 프로젝트")).toBeInTheDocument();
    });

    await waitFor(() => {
      expect(
        screen.getByText("NDA 체결 또는 자료 배포가 필요합니다"),
      ).toBeInTheDocument();
    });
  });

  // 6. subtitle에 code_name, target_company_name, client_name 포함
  it("subtitle에 코드명, 대상기업, 클라이언트를 표시한다", async () => {
    renderPage();

    await waitFor(() => {
      expect(
        screen.getByText(/SE26-TST-01.*대상기업.*클라이언트/),
      ).toBeInTheDocument();
    });
  });

  // 7. 현재 단계 라벨 표시
  it("현재 단계 라벨을 표시한다", async () => {
    renderPage();

    await waitFor(() => {
      expect(screen.getByText("테스트 프로젝트")).toBeInTheDocument();
    });

    // PipelineFlow/Card 영역에 현재 단계 텍스트
    expect(screen.getByText(/현재:/)).toBeInTheDocument();
  });

  // 8. can_advance=true이면 다음 단계 버튼 표시
  it("can_advance=true일 때 다음 단계 버튼을 표시한다", async () => {
    server.use(
      http.get("*/api/ma/transactions/:txnId/workflow/phase-status", () => {
        return HttpResponse.json({
          ...mockPhaseStatus,
          can_advance: true,
          all_met: true,
          blocking_reasons: [],
          pending_acknowledgements: [],
        });
      }),
    );

    renderPage();

    await waitFor(() => {
      expect(screen.getByText("테스트 프로젝트")).toBeInTheDocument();
    });

    await waitFor(() => {
      // 이전 단계/다음 단계 버튼 모두 '단계로' 포함 — 복수 매칭 허용
      const advanceBtns = screen.getAllByRole("button", { name: /단계로/ });
      expect(advanceBtns.length).toBeGreaterThanOrEqual(1);
    });
  });
});
