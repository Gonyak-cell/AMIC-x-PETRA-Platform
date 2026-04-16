import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { QueryClientProvider } from "@tanstack/react-query";
import { http, HttpResponse } from "msw";

import {
  AuthContext,
  type AuthContextValue,
} from "@/components/auth/AuthContext";
import { mockUser } from "@/test/mocks/data";
import { server } from "@/test/mocks/server";
import { createTestQueryClient } from "@/test/test-utils";
import { mockPhaseStatus } from "@/test/mocks/ma-handlers";

import TransactionWorkspacePage from "../TransactionWorkspacePage";

const defaultAuth: AuthContextValue = {
  user: mockUser,
  isAuthenticated: true,
  isLoading: false,
  setAuthState: vi.fn(),
};

function renderPage(path: string) {
  const queryClient = createTestQueryClient();
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[path]}>
        <AuthContext.Provider value={defaultAuth}>
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

describe("TransactionWorkspacePage setup mode", () => {
  beforeEach(() => {
    server.resetHandlers();
  });

  it("keeps the overview open when setup=company-info is present", async () => {
    server.use(
      http.get("*/api/ma/transactions/:txnId", () =>
        HttpResponse.json({
          id: "txn-setup",
          code_name: "SE26-SET-01",
          name: "Project Guided",
          deal_type: "SE",
          side: "SELL",
          phase: "ENGAGEMENT",
          status: "DRAFT",
          target_company_name: "Target Co",
          target_corp_code: null,
          client_name: "Client Co",
          estimated_deal_value: null,
          currency: "KRW",
          deal_structure: null,
          investment_type: null,
          industry: null,
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
          current_phase: "ENGAGEMENT",
          next_phase: "PREPARATION",
          previous_phase: null,
        }),
      ),
    );

    renderPage("/ma/transactions/txn-setup?setup=company-info");

    await waitFor(() => {
      expect(screen.getByText("회사 정보")).toBeInTheDocument();
    });
  });
});
