import { vi, describe, it, expect, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { QueryClientProvider } from "@tanstack/react-query";
import { http, HttpResponse } from "msw";
import { server } from "@/test/mocks/server";
import { mockTransaction } from "@/test/mocks/ma-handlers";
import {
  AuthContext,
  type AuthContextValue,
} from "@/components/auth/AuthContext";
import { mockUser } from "@/test/mocks/data";
import { createTestQueryClient } from "@/test/test-utils";
import BuyersTab from "../BuyersTab";

const defaultAuth: AuthContextValue = {
  user: mockUser,
  isAuthenticated: true,
  isLoading: false,
  setAuthState: vi.fn(),
};

const mockBuyer = {
  id: "buyer-1",
  transaction_id: "txn-1",
  company_name: "테스트매수자",
  buyer_type: "STRATEGIC",
  tier: "TIER_1",
  status: "INTERESTED",
  deal_role: "BIDDER",
  short_listed: false,
  contact_name: "홍길동",
  contact_email: "hong@test.com",
  notes: null,
  extra_data: null,
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
};

function renderTab(props: Partial<{ txnId: string; canWrite: boolean }> = {}) {
  const queryClient = createTestQueryClient();
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <AuthContext.Provider value={defaultAuth}>
          <BuyersTab
            txnId={props.txnId ?? "txn-1"}
            canWrite={props.canWrite ?? true}
          />
        </AuthContext.Provider>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  server.resetHandlers();
});

describe("BuyersTab", () => {
  it("로딩 중 Spinner를 표시한다", () => {
    server.use(
      http.get("*/api/ma/transactions/:txnId/buyers", () => {
        return new Promise(() => {}); // never resolves
      }),
    );
    renderTab();
    expect(screen.getByRole("status")).toBeInTheDocument();
  });

  it("매수자가 없으면 빈 테이블을 표시한다", async () => {
    renderTab();
    await waitFor(() => {
      expect(screen.getByText("Long List 후보 없음")).toBeInTheDocument();
    });
  });

  it("매수자 데이터를 테이블에 표시한다", async () => {
    server.use(
      http.get("*/api/ma/transactions/:txnId/buyers", () => {
        return HttpResponse.json({ items: [mockBuyer], total: 1 });
      }),
    );
    renderTab();
    await waitFor(() => {
      expect(screen.getByText("테스트매수자")).toBeInTheDocument();
    });
  });

  it("FunnelNav에 Long List/Short List 탭을 표시한다", async () => {
    renderTab();
    await waitFor(() => {
      // 'Long List' 텍스트가 FunnelNav + 제목 등 여러 곳에 표시됨
      expect(screen.getAllByText(/Long List/i).length).toBeGreaterThanOrEqual(1);
    });
    expect(screen.getAllByText(/Short List/i).length).toBeGreaterThanOrEqual(1);
  });

  it("canWrite=false이면 FI/SI 자동 매핑 버튼이 숨겨진다", async () => {
    renderTab({ canWrite: false });
    await waitFor(() => {
      expect(screen.getByText("Long List 후보 없음")).toBeInTheDocument();
    });
    expect(screen.queryByText("FI 자동 추천")).not.toBeInTheDocument();
    expect(screen.queryByText("SI 자동 매핑")).not.toBeInTheDocument();
  });
});
