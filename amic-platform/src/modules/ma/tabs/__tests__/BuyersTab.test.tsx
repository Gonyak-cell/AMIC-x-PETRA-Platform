import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { QueryClientProvider } from "@tanstack/react-query";
import { http, HttpResponse } from "msw";

import {
  AuthContext,
  type AuthContextValue,
} from "@/components/auth/AuthContext";
import { mockUser } from "@/test/mocks/data";
import { server } from "@/test/mocks/server";
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

function renderTab(
  props: Partial<{
    txnId: string;
    canWrite: boolean;
    headerActionPortalId: string;
  }> = {},
) {
  const queryClient = createTestQueryClient();
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <AuthContext.Provider value={defaultAuth}>
          {props.headerActionPortalId ? (
            <div id={props.headerActionPortalId} />
          ) : null}
          <BuyersTab
            txnId={props.txnId ?? "txn-1"}
            canWrite={props.canWrite ?? true}
            headerActionPortalId={props.headerActionPortalId}
          />
        </AuthContext.Provider>
      </MemoryRouter>
    </QueryClientProvider>
  );
}

describe("BuyersTab", () => {
  beforeEach(() => {
    server.resetHandlers();
  });

  it("shows a spinner while buyers are loading", () => {
    server.use(
      http.get("*/api/ma/transactions/:txnId/buyers", () => {
        return new Promise(() => {});
      }),
    );

    renderTab();

    expect(screen.getByRole("status")).toBeInTheDocument();
  });

  it("shows the empty long-list state when there are no buyers", async () => {
    renderTab();

    await waitFor(() => {
      expect(screen.getByText("Long List 후보 없음")).toBeInTheDocument();
    });
  });

  it("renders buyer data in the table", async () => {
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

  it("shows both Long List and Short List steps", async () => {
    renderTab();

    await waitFor(() => {
      expect(screen.getAllByText(/Long List/i).length).toBeGreaterThanOrEqual(
        1,
      );
    });

    expect(screen.getAllByText(/Short List/i).length).toBeGreaterThanOrEqual(1);
  });

  it("hides FI and SI automation buttons for read-only users", async () => {
    renderTab({ canWrite: false });

    await waitFor(() => {
      expect(screen.getByText("Long List 후보 없음")).toBeInTheDocument();
    });

    expect(screen.queryByText("FI 자동 추천")).not.toBeInTheDocument();
    expect(screen.queryByText("SI 자동 매핑")).not.toBeInTheDocument();
  });

  it("renders the Excel action into the workspace header slot on long list", async () => {
    renderTab({ headerActionPortalId: "workspace-tab-header-actions" });

    await waitFor(() => {
      expect(screen.getByText("Long List 후보 없음")).toBeInTheDocument();
    });

    const headerSlot = document.getElementById("workspace-tab-header-actions");
    expect(headerSlot).not.toBeNull();
    expect(
      within(headerSlot as HTMLElement).getByRole("button", { name: "Excel" }),
    ).toBeInTheDocument();
  });
});
