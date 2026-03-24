import { beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { QueryClientProvider } from "@tanstack/react-query";
import { http, HttpResponse } from "msw";
import { toast } from "sonner";

import {
  AuthContext,
  type AuthContextValue,
} from "@/components/auth/AuthContext";
import { mockUser } from "@/test/mocks/data";
import { mockTransaction } from "@/test/mocks/ma-handlers";
import { server } from "@/test/mocks/server";
import { createTestQueryClient } from "@/test/test-utils";

import BuyersTab from "../BuyersTab";

const defaultAuth: AuthContextValue = {
  user: mockUser,
  isAuthenticated: true,
  isLoading: false,
  setAuthState: vi.fn(),
};

const toastErrorSpy = vi
  .spyOn(toast, "error")
  .mockImplementation(() => "toast-error");
const toastInfoSpy = vi
  .spyOn(toast, "info")
  .mockImplementation(() => "toast-info");
const toastSuccessSpy = vi
  .spyOn(toast, "success")
  .mockImplementation(() => "toast-success");

const mockBuyer = {
  id: "buyer-1",
  transaction_id: "txn-1",
  company_name: "Test Buyer",
  contact_name: "Hong",
  contact_email: "hong@test.com",
  contact_phone: null,
  buyer_type: "STRATEGIC",
  status: "CONTACTED",
  tier: "TIER_1",
  corp_code: null,
  deal_role: "SOLE_BUYER",
  is_short_listed: false,
  ioi_value: null,
  ioi_date: null,
  loi_value: null,
  loi_date: null,
  final_offer_value: null,
  rejection_reason: null,
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
    </QueryClientProvider>,
  );
}

describe("BuyersTab", () => {
  beforeEach(() => {
    server.resetHandlers();
    toastErrorSpy.mockClear();
    toastInfoSpy.mockClear();
    toastSuccessSpy.mockClear();
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
      expect(screen.getAllByText(/Long List/i).length).toBeGreaterThanOrEqual(
        1,
      );
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
      expect(screen.getByText(mockBuyer.company_name)).toBeInTheDocument();
    });
  });

  it("renders a company logo when the buyer has a logo URL", async () => {
    const logoBuyer = {
      ...mockBuyer,
      id: "buyer-logo",
      company_name: "Logo Buyer",
      extra_data: {
        logo_url: "https://example.com/logo.png",
      },
    };

    server.use(
      http.get("*/api/ma/transactions/:txnId/buyers", () => {
        return HttpResponse.json({ items: [logoBuyer], total: 1 });
      }),
    );

    renderTab();

    expect(await screen.findByAltText("Logo Buyer logo")).toBeInTheDocument();
  });

  it("opens the long-list detail panel for financial sponsor buyers without showing an SI trigger", async () => {
    const user = userEvent.setup();
    const financialBuyer = {
      ...mockBuyer,
      id: "buyer-fi",
      company_name: "Heimdall Private Equity",
      buyer_type: "FINANCIAL_SPONSOR" as const,
    };

    server.use(
      http.get("*/api/ma/transactions/:txnId/buyers", () => {
        return HttpResponse.json({ items: [financialBuyer], total: 1 });
      }),
    );

    renderTab();

    await waitFor(() => {
      expect(screen.getByText(financialBuyer.company_name)).toBeInTheDocument();
    });

    expect(screen.queryByRole("button", { name: "SI 상세" })).not.toBeInTheDocument();

    await user.click(
      screen.getByRole("button", { name: financialBuyer.company_name }),
    );

    expect(
      await screen.findByRole("button", { name: "롱리스트 정보 수정" }),
    ).toBeInTheDocument();
  });

  it(
    "saves edited long-list buyer information from the summary panel",
    async () => {
    const user = userEvent.setup();
    let requestBody: Record<string, unknown> | null = null;
    const editableBuyer = {
      ...mockBuyer,
      extra_data: {
        si_company_id: "si-company-1",
      },
    };

    server.use(
      http.get("*/api/ma/transactions/:txnId/buyers", () => {
        return HttpResponse.json({ items: [editableBuyer], total: 1 });
      }),
      http.patch("*/api/ma/transactions/:txnId/buyers/:buyerId", async ({ request }) => {
        requestBody = (await request.json()) as Record<string, unknown>;
        return HttpResponse.json({
          ...editableBuyer,
          ...requestBody,
          contact_name: requestBody.contact_name,
          contact_email: requestBody.contact_email,
          contact_phone: requestBody.contact_phone,
          notes: requestBody.notes,
          buyer_type: requestBody.buyer_type,
          tier: requestBody.tier,
          deal_role: requestBody.deal_role,
        });
      }),
    );

    renderTab();

    await waitFor(() => {
      expect(
        screen.getByRole("button", { name: editableBuyer.company_name }),
      ).toBeInTheDocument();
    });

    await user.click(
      screen.getByRole("button", { name: editableBuyer.company_name }),
    );
    await user.click(
      await screen.findByRole("button", { name: "롱리스트 정보 수정" }),
    );

    const companyNameInput = screen.getByLabelText("회사명");
    fireEvent.change(companyNameInput, {
      target: { value: "Updated Buyer" },
    });
    fireEvent.change(screen.getByLabelText("담당자"), {
      target: { value: "Lee" },
    });
    fireEvent.change(screen.getByLabelText("유형"), {
      target: { value: "FINANCIAL_SPONSOR" },
    });
    fireEvent.change(screen.getByLabelText("로고 URL"), {
      target: { value: "https://example.com/logos/updated-buyer.png" },
    });
    fireEvent.change(screen.getByLabelText("비고"), {
      target: { value: "Updated from long list" },
    });
    await user.click(screen.getByRole("button", { name: "저장" }));

    await waitFor(() => {
      expect(requestBody).toMatchObject({
        company_name: "Updated Buyer",
        contact_name: "Lee",
        buyer_type: "FINANCIAL_SPONSOR",
        notes: "Updated from long list",
        extra_data: {
          si_company_id: "si-company-1",
          logo_url: "https://example.com/logos/updated-buyer.png",
        },
      });
    });
    },
    10000,
  );

  it("shows the funnel steps in Long List, NDA, Short List order", async () => {
    renderTab();

    await waitFor(() => {
      expect(screen.getAllByText(/Long List/i).length).toBeGreaterThanOrEqual(
        1,
      );
    });

    expect(screen.getAllByText(/Short List/i).length).toBeGreaterThanOrEqual(1);

    const tabTexts = within(screen.getByRole("tablist"))
      .getAllByRole("tab")
      .map((tab) => tab.textContent ?? "");

    const longListIndex = tabTexts.findIndex((text) => text.includes("Long List"));
    const ndaIndex = tabTexts.findIndex((text) => text.includes("NDA"));
    const shortListIndex = tabTexts.findIndex((text) => text.includes("Short List"));

    expect(longListIndex).toBeGreaterThanOrEqual(0);
    expect(ndaIndex).toBeGreaterThanOrEqual(0);
    expect(shortListIndex).toBeGreaterThanOrEqual(0);
    expect(longListIndex).toBeLessThan(ndaIndex);
    expect(ndaIndex).toBeLessThan(shortListIndex);
  });

  it("hides FI and SI automation buttons for read-only users", async () => {
    renderTab({ canWrite: false });

    await waitFor(() => {
      expect(screen.getAllByText(/Long List/i).length).toBeGreaterThanOrEqual(
        1,
      );
    });

    expect(
      screen.queryByRole("button", { name: /FI/i }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: /SI/i }),
    ).not.toBeInTheDocument();
  });

  it("shows FI, SI, and plus actions first, then reveals manual add actions", async () => {
    const user = userEvent.setup();

    renderTab();

    await waitFor(() => {
      expect(screen.getAllByText(/Long List/i).length).toBeGreaterThanOrEqual(
        1,
      );
    });

    expect(screen.getByRole("button", { name: "FI 자동 추천" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "SI 자동 매핑" })).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "매수자 추가" }),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "FI 추가" }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "SI 추가" }),
    ).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "매수자 추가" }));

    expect(screen.getByRole("button", { name: "FI 추가" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "SI 추가" })).toBeInTheDocument();
  });

  it("renders the Excel action into the workspace header slot on long list", async () => {
    renderTab({ headerActionPortalId: "workspace-tab-header-actions" });

    await waitFor(() => {
      expect(screen.getAllByText(/Long List/i).length).toBeGreaterThanOrEqual(
        1,
      );
    });

    const headerSlot = document.getElementById("workspace-tab-header-actions");
    expect(headerSlot).not.toBeNull();
    expect(
      within(headerSlot as HTMLElement).getByRole("button", { name: "Excel" }),
    ).toBeInTheDocument();
  });

  it("blocks FI recommendations until the estimated deal value is set", async () => {
    const user = userEvent.setup();
    const fiRecommendationHandler = vi.fn();

    server.use(
      http.get("*/api/ma/transactions/:txnId", () =>
        HttpResponse.json({
          ...mockTransaction,
          estimated_deal_value: null,
        }),
      ),
      http.get("*/api/ma/transactions/:txnId/fi-recommendations", () => {
        fiRecommendationHandler();
        return HttpResponse.json([]);
      }),
    );

    renderTab();

    await waitFor(() => {
      expect(screen.getAllByText(/Long List/i).length).toBeGreaterThanOrEqual(
        1,
      );
    });

    await user.click(screen.getByRole("button", { name: "FI 자동 추천" }));

    const firstToastMessage = toastErrorSpy.mock.calls[0]?.[0];
    expect(firstToastMessage).toContain("FI 자동 추천");
    expect(firstToastMessage).toContain("예상 거래금액");
    expect(fiRecommendationHandler).not.toHaveBeenCalled();
  });

  it("shows the API detail inside the FI modal when the recommendation query fails", async () => {
    const user = userEvent.setup();
    const errorDetail =
      "거래금액(estimated_deal_value)이 설정되지 않았습니다. 거래 설정에서 예상 거래금액을 입력해 주세요.";

    server.use(
      http.get("*/api/ma/transactions/:txnId/fi-recommendations", () =>
        HttpResponse.json({ detail: errorDetail }, { status: 422 }),
      ),
    );

    renderTab();

    await waitFor(() => {
      expect(screen.getAllByText(/Long List/i).length).toBeGreaterThanOrEqual(
        1,
      );
    });

    await user.click(screen.getByRole("button", { name: "FI 자동 추천" }));

    expect(await screen.findByText(errorDetail)).toBeInTheDocument();
  });

  it("submits the SI manual add modal with strategic buyer type", async () => {
    const user = userEvent.setup();
    let requestBody: Record<string, unknown> | null = null;

    server.use(
      http.post("*/api/ma/transactions/:txnId/buyers", async ({ request }) => {
        requestBody = (await request.json()) as Record<string, unknown>;
        return HttpResponse.json({
          ...mockBuyer,
          id: "buyer-2",
          company_name: requestBody.company_name,
          buyer_type: requestBody.buyer_type,
        });
      }),
    );

    renderTab();

    await waitFor(() => {
      expect(screen.getAllByText(/Long List/i).length).toBeGreaterThanOrEqual(
        1,
      );
    });

    await user.click(screen.getByRole("button", { name: "매수자 추가" }));
    await user.click(screen.getByRole("button", { name: "SI 추가" }));

    expect(await screen.findByText("전략적 투자자 (SI)")).toBeInTheDocument();

    await user.type(screen.getByLabelText("회사명"), "Strategic Partner");
    await user.selectOptions(screen.getByLabelText("Tier"), "TIER_2");
    await user.click(screen.getByRole("button", { name: "추가" }));

    await waitFor(() => {
      expect(requestBody).toMatchObject({
        company_name: "Strategic Partner",
        buyer_type: "STRATEGIC",
        tier: "TIER_2",
      });
    });
  });
});
