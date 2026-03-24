import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
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

const defaultAuth: AuthContextValue = {
  user: mockUser,
  isAuthenticated: true,
  isLoading: false,
  setAuthState: vi.fn(),
};

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

const clientAuth: Partial<AuthContextValue> = {
  user: {
    ...mockUser,
    email: "client.demo@amic.kr",
    display_name: "Client Demo",
    role: "CLIENT",
  },
};

describe("TransactionWorkspacePage", () => {
  beforeEach(() => {
    server.resetHandlers();
  });

  it("loading 동안 spinner를 표시한다", () => {
    server.use(
      http.get("*/api/ma/transactions/:txnId", () => {
        return new Promise(() => {});
      }),
    );

    renderPage();

    expect(screen.getByRole("status")).toBeInTheDocument();
  });

  it("거래명과 ACTIVE 상태 배지를 표시한다", async () => {
    renderPage();

    await waitFor(() => {
      expect(screen.getByText("테스트 프로젝트")).toBeInTheDocument();
    });

    expect(screen.getAllByText("ACTIVE").length).toBeGreaterThanOrEqual(1);
  });

  it("히어로 우측 내부에 단계 액션 바를 렌더링한다", async () => {
    renderPage();

    await waitFor(() => {
      expect(screen.getByText("테스트 프로젝트")).toBeInTheDocument();
    });

    const heroActions = screen.getByTestId("workspace-hero-actions");
    const heroShortcuts = screen.getByTestId("workspace-hero-shortcuts");
    const heroSection = screen.getByText("테스트 프로젝트").closest("section");

    expect(heroSection).not.toBeNull();
    expect(heroSection).toContainElement(heroActions);
    expect(heroSection).toContainElement(heroShortcuts);
    expect(
      within(heroShortcuts).getByRole("button", { name: "Overview" }),
    ).toBeInTheDocument();
    expect(
      within(heroShortcuts).getByRole("button", { name: "Upload to VDR" }),
    ).toBeInTheDocument();
    expect(screen.getAllByText("Upload to VDR")).toHaveLength(1);
    expect(within(heroActions).queryByText("ACTIVE")).not.toBeInTheDocument();
    expect(within(heroActions).queryByText("마케팅")).not.toBeInTheDocument();
  });

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

  it("MARKETING 단계에서는 해당 단계 탭만 표시한다", async () => {
    renderPage();

    await waitFor(() => {
      expect(screen.getByText("테스트 프로젝트")).toBeInTheDocument();
    });

    expect(screen.getByText("매수자")).toBeInTheDocument();
    expect(screen.getByText("마케팅 로그")).toBeInTheDocument();

    const tabList = screen.getAllByRole("tab");
    const tabLabels = tabList.map((tab) => tab.textContent);
    expect(tabLabels).not.toContain("VDR");
    expect(tabLabels).not.toContain("입찰");
    expect(tabLabels).not.toContain("Closing");
    expect(tabLabels).not.toContain("PMI");
  });

  it("VDR 경로에서도 primary 탭바에 VDR를 노출하지 않는다", async () => {
    renderPage("/ma/transactions/txn-1/vdr");

    await waitFor(() => {
      expect(screen.getByText("테스트 프로젝트")).toBeInTheDocument();
    });

    const tabList = screen.getAllByRole("tab");
    const tabLabels = tabList.map((tab) => tab.textContent);
    const activeTab = tabList.find(
      (tab) => tab.getAttribute("aria-selected") === "true",
    );

    expect(tabLabels).not.toContain("VDR");
    expect(activeTab?.textContent).toContain("매수자");
  });

  it("단계별 hurdle UI를 표시하지 않는다", async () => {
    renderPage();

    await waitFor(() => {
      expect(screen.getByText("테스트 프로젝트")).toBeInTheDocument();
    });

    expect(screen.queryByText("NDA 체결 또는 자료 배포가 필요합니다")).not.toBeInTheDocument();
  });

  it("subtitle에 코드명, 대상기업, 클라이언트를 표시한다", async () => {
    renderPage();

    await waitFor(() => {
      expect(
        screen.getByText(/SE26-TST-01.*대상기업.*클라이언트/),
      ).toBeInTheDocument();
    });
  });

  it("현재 단계 라벨을 표시한다", async () => {
    renderPage();

    await waitFor(() => {
      expect(screen.getByText("테스트 프로젝트")).toBeInTheDocument();
    });

    expect(screen.getByText(/현재:/)).toBeInTheDocument();
  });

  it("can_advance=true면 다음 단계 버튼을 표시한다", async () => {
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
      const advanceButtons = screen.getAllByRole("button", {
        name: /단계로/,
      });
      expect(advanceButtons.length).toBeGreaterThanOrEqual(1);
    });
  });

  it("/timeline?baseTab=buyers 접근 시 buyers tab이 primary이고 panel이 열린다", async () => {
    renderPage("/ma/transactions/txn-1/timeline?baseTab=buyers");

    await waitFor(() => {
      expect(screen.getByText("테스트 프로젝트")).toBeInTheDocument();
    });

    const tabs = screen.getAllByRole("tab");
    const activeTab = tabs.find(
      (tab) => tab.getAttribute("aria-selected") === "true",
    );
    expect(activeTab?.textContent).toContain("매수자");

    await waitFor(() => {
      expect(screen.getByRole("dialog")).toBeInTheDocument();
    });
  });

  it("/timeline 접근 시 phase 기본 탭이 primary이고 panel이 열린다", async () => {
    renderPage("/ma/transactions/txn-1/timeline");

    await waitFor(() => {
      expect(screen.getByText("테스트 프로젝트")).toBeInTheDocument();
    });

    const tabs = screen.getAllByRole("tab");
    const activeTab = tabs.find(
      (tab) => tab.getAttribute("aria-selected") === "true",
    );
    expect(activeTab?.textContent).toContain("매수자");

    await waitFor(() => {
      expect(screen.getByRole("dialog")).toBeInTheDocument();
    });
  });

  it("timeline rail URL의 query context를 보존한다", async () => {
    renderPage(
      "/ma/transactions/txn-1/timeline?baseTab=marketing-logs&buyerId=b1&viewPhase=MARKETING",
    );

    await waitFor(() => {
      expect(screen.getByText("테스트 프로젝트")).toBeInTheDocument();
    });

    await waitFor(() => {
      expect(screen.getByRole("dialog")).toBeInTheDocument();
    });
  });

  it("제거된 tool URL은 기존 문맥으로 돌아가고 panel을 열지 않는다", async () => {
    renderPage("/ma/transactions/txn-1/risks?baseTab=buyers");

    await waitFor(() => {
      expect(screen.getByText("테스트 프로젝트")).toBeInTheDocument();
    });

    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();

    const tabs = screen.getAllByRole("tab");
    const activeTab = tabs.find(
      (tab) => tab.getAttribute("aria-selected") === "true",
    );
    expect(activeTab?.textContent).toContain("매수자");
  });
  it("preparation phase 기본 진입에서는 VDR preview hero를 붙이지 않는다", async () => {
    server.use(
      http.get("*/api/ma/transactions/:txnId", () =>
        HttpResponse.json({
          id: "txn-1",
          code_name: "SE26-TST-01",
          name: "테스트 프로젝트",
          deal_type: "SE",
          side: "SELL",
          phase: "PREPARATION",
          status: "ACTIVE",
          target_company_name: "대상기업",
          target_corp_code: null,
          client_name: "클라이언트",
          estimated_deal_value: "50000000000",
          currency: "KRW",
          deal_structure: null,
          investment_type: null,
          industry: "general",
          lead_advisor_email: "jwsuh@amic.kr",
          deal_captain_email: null,
          target_close_date: null,
          sale_process: null,
          control_transfer: null,
          target_stake: null,
          new_share_ratio: null,
          old_share_ratio: null,
          valuation_basis: null,
          cross_border: null,
          target_buyer_types: null,
          exclusivity: null,
          exclusivity_deadline: null,
          fdd_deal_id: null,
          im_document_id: null,
          notes: null,
          corporate_info: null,
          financial_summary: null,
          is_deleted: false,
          created_at: "2026-01-01T00:00:00Z",
          updated_at: "2026-01-01T00:00:00Z",
        }),
      ),
      http.get("*/api/ma/transactions/:txnId/workflow/phase-status", () =>
        HttpResponse.json({
          ...mockPhaseStatus,
          current_phase: "PREPARATION",
          next_phase: "MARKETING",
          previous_phase: "ENGAGEMENT",
        }),
      ),
    );

    renderPage("/ma/transactions/txn-1");

    await waitFor(() => {
      expect(screen.getByText("테스트 프로젝트")).toBeInTheDocument();
    });

    expect(
      screen.queryByTestId("workspace-source-preview-hero"),
    ).not.toBeInTheDocument();

    const tabLabels = screen.queryAllByRole("tab").map((tab) => tab.textContent);
    expect(tabLabels).not.toContain("Overview");
    expect(screen.getByTestId("workspace-hero-shortcuts")).toHaveTextContent(
      "Overview",
    );
  });

  it("수임/준비 뷰에서는 hero shortcut에 overview를 노출하지 않는다", async () => {
    renderPage("/ma/transactions/txn-1?viewPhase=ENGAGEMENT");

    await waitFor(() => {
      return void expect(
        screen.getByTestId("workspace-hero-shortcuts"),
      ).toBeInTheDocument();
      expect(
        screen.getByRole("heading", { name: "테스트 프로젝트" }),
      ).toBeInTheDocument();
    });

    expect(screen.getByTestId("workspace-hero-shortcuts")).toHaveTextContent(
      "Overview",
    );
  });

  it("marketing materials route에서도 VDR preview hero를 붙이지 않는다", async () => {
    renderPage("/ma/transactions/txn-1/marketing-materials?viewPhase=PREPARATION");

    await waitFor(() => {
      expect(screen.getByText("테스트 프로젝트")).toBeInTheDocument();
    });

    expect(
      screen.queryByTestId("workspace-source-preview-hero"),
    ).not.toBeInTheDocument();
  });

  it("models route에서도 VDR preview hero를 붙이지 않는다", async () => {
    renderPage("/ma/transactions/txn-1/models?viewPhase=PREPARATION");

    await waitFor(() => {
      expect(screen.getByText("테스트 프로젝트")).toBeInTheDocument();
    });

    expect(
      screen.queryByTestId("workspace-source-preview-hero"),
    ).not.toBeInTheDocument();
  });
  it("buyers tab에서는 Excel action이 Timeline 왼쪽 헤더에 배치된다", async () => {
    renderPage("/ma/transactions/txn-1/buyers");

    await waitFor(() => {
      expect(
        screen.getByRole("heading", { name: "테스트 프로젝트" }),
      ).toBeInTheDocument();
    });

    const excelButtonInHeader = await within(
      screen.getByTestId("workspace-tab-header-actions-slot"),
    ).findByRole("button", { name: "Excel" }, { timeout: 10000 });

    expect(excelButtonInHeader).toBeInTheDocument();

    const actions = within(screen.getByTestId("workspace-tabs-actions"));
    const orderedButtons = actions.getAllByRole("button");
    const excelButton = actions.getByRole("button", { name: "Excel" });
    const timelineButton = actions.getByRole("button", { name: "Timeline" });

    expect(orderedButtons.indexOf(excelButton)).toBeLessThan(
      orderedButtons.indexOf(timelineButton),
    );
  }, 20000);

  it("closing 단계에서는 다음 버튼이 거래종결 단계로 표시된다", async () => {
    server.use(
      http.get("*/api/ma/transactions/:txnId", () =>
        HttpResponse.json({
          id: "txn-1",
          code_name: "SE26-TST-01",
          name: "Project Next",
          deal_type: "SE",
          side: "SELL",
          phase: "CLOSING",
          status: "ACTIVE",
          target_company_name: "NX Games",
          target_corp_code: null,
          client_name: "Client Lead",
          estimated_deal_value: "50000000000",
          currency: "KRW",
          deal_structure: null,
          investment_type: null,
          industry: "general",
          lead_advisor_email: "jwsuh@amic.kr",
          deal_captain_email: null,
          target_close_date: null,
          sale_process: null,
          control_transfer: null,
          target_stake: null,
          new_share_ratio: null,
          old_share_ratio: null,
          valuation_basis: null,
          cross_border: null,
          target_buyer_types: null,
          exclusivity: null,
          exclusivity_deadline: null,
          fdd_deal_id: null,
          im_document_id: null,
          notes: null,
          corporate_info: null,
          financial_summary: null,
          is_deleted: false,
          created_at: "2026-01-01T00:00:00Z",
          updated_at: "2026-03-22T00:00:00Z",
        }),
      ),
      http.get("*/api/ma/transactions/:txnId/workflow/phase-status", () =>
        HttpResponse.json({
          ...mockPhaseStatus,
          current_phase: "CLOSING",
          next_phase: "POST_CLOSING",
          previous_phase: "NEGOTIATION",
          can_advance: true,
          all_met: true,
          blocking_reasons: [],
          pending_acknowledgements: [],
          requires_user_acknowledgement: false,
        }),
      ),
    );

    renderPage("/ma/transactions/txn-1/closing");

    await waitFor(() => {
      expect(
        screen.getByRole("button", { name: "거래종결 단계로" }),
      ).toBeInTheDocument();
    });
  });

  it("거래종결 단계에서는 축하 메시지와 overview만 보여준다", async () => {
    server.use(
      http.get("*/api/ma/transactions/:txnId", () =>
        HttpResponse.json({
          id: "txn-1",
          code_name: "SE26-TST-01",
          name: "Project Next",
          deal_type: "SE",
          side: "SELL",
          phase: "POST_CLOSING",
          status: "ACTIVE",
          target_company_name: "NX Games",
          target_corp_code: null,
          client_name: "Client Lead",
          estimated_deal_value: "50000000000",
          currency: "KRW",
          deal_structure: null,
          investment_type: null,
          industry: "general",
          lead_advisor_email: "jwsuh@amic.kr",
          deal_captain_email: null,
          target_close_date: "2026-03-22",
          sale_process: null,
          control_transfer: null,
          target_stake: null,
          new_share_ratio: null,
          old_share_ratio: null,
          valuation_basis: null,
          cross_border: null,
          target_buyer_types: null,
          exclusivity: null,
          exclusivity_deadline: null,
          fdd_deal_id: null,
          im_document_id: null,
          notes: null,
          corporate_info: null,
          financial_summary: null,
          is_deleted: false,
          created_at: "2026-01-01T00:00:00Z",
          updated_at: "2026-03-22T00:00:00Z",
        }),
      ),
      http.get("*/api/ma/transactions/:txnId/workflow/phase-status", () =>
        HttpResponse.json({
          ...mockPhaseStatus,
          current_phase: "POST_CLOSING",
          next_phase: null,
          previous_phase: "CLOSING",
          can_advance: false,
          all_met: true,
          blocking_reasons: [],
          pending_acknowledgements: [],
          requires_user_acknowledgement: false,
        }),
      ),
    );

    renderPage("/ma/transactions/txn-1/pmi");

    expect(
      await screen.findByText(
        "클로징까지 정말 고생 많으셨습니다.",
        {},
        { timeout: 10000 },
      ),
    ).toBeInTheDocument();

    const tabLabels = screen.queryAllByRole("tab").map((tab) => tab.textContent);
    expect(tabLabels).toEqual([]);
    expect(
      screen.getByTestId("workspace-hero-shortcuts"),
    ).toHaveTextContent("Overview");
    expect(screen.queryByText("PMI")).not.toBeInTheDocument();
    expect(screen.queryByText("어닝아웃")).not.toBeInTheDocument();
  });
  it("CLIENT sees a VDR shortcut in the workspace hero", async () => {
    Object.defineProperty(window.HTMLElement.prototype, "scrollIntoView", {
      configurable: true,
      value: vi.fn(),
    });

    renderPage("/ma/transactions/txn-1", clientAuth);

    await waitFor(() => {
      expect(screen.getByTestId("workspace-hero-shortcuts")).toBeInTheDocument();
      return;
    });

    const heroShortcuts = screen.getByTestId("workspace-hero-shortcuts");
    expect(
      within(heroShortcuts).getByRole("button", { name: "VDR" }),
    ).toBeInTheDocument();
    expect(
      within(heroShortcuts).getByRole("button", { name: "Upload to VDR" }),
    ).toBeInTheDocument();
  });
});
