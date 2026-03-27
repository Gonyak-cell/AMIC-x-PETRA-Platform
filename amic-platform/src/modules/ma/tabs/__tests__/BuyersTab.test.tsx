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
  tier: null,
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

  it("hides shortlisted buyers from the long-list table", async () => {
    const user = userEvent.setup();
    const longListBuyer = {
      ...mockBuyer,
      id: "buyer-long",
      company_name: "Long List Buyer",
    };
    const shortListBuyer = {
      ...mockBuyer,
      id: "buyer-short",
      company_name: "Short List Buyer",
      tier: "TIER_1" as const,
      status: "NDA_SIGNED" as const,
      is_short_listed: true,
    };

    server.use(
      http.get("*/api/ma/transactions/:txnId/buyers", () => {
        return HttpResponse.json({
          items: [longListBuyer, shortListBuyer],
          total: 2,
        });
      }),
    );

    renderTab();

    await user.click(await screen.findByRole("tab", { name: /Long List/i }));
    expect(await screen.findByText(longListBuyer.company_name)).toBeInTheDocument();
    expect(screen.queryByText(shortListBuyer.company_name)).not.toBeInTheDocument();
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

  it("auto-advances into the NDA step once every buyer has a tier decision", async () => {
    const tieredBuyer = {
      ...mockBuyer,
      tier: "TIER_1",
    };

    server.use(
      http.get("*/api/ma/transactions/:txnId/buyers", () => {
        return HttpResponse.json({ items: [tieredBuyer], total: 1 });
      }),
    );

    renderTab();

    await waitFor(() => {
      expect(screen.getByRole("tab", { name: /NDA/i })).toHaveAttribute(
        "aria-selected",
        "true",
      );
    });

    expect(screen.getByText("Tier 1")).toBeInTheDocument();
  });

  it("opens the NDA panel with an upload CTA when no NDA exists yet", async () => {
    const user = userEvent.setup();
    const tieredBuyer = {
      ...mockBuyer,
      tier: "TIER_1",
    };

    server.use(
      http.get("*/api/ma/transactions/:txnId/buyers", () => {
        return HttpResponse.json({ items: [tieredBuyer], total: 1 });
      }),
      http.get("*/api/ma/transactions/:txnId/ndas", () => {
        return HttpResponse.json([]);
      }),
    );

    renderTab();

    await waitFor(() => {
      expect(screen.getByRole("tab", { name: /NDA/i })).toHaveAttribute(
        "aria-selected",
        "true",
      );
    });

    await user.click(screen.getByRole("button", { name: tieredBuyer.company_name }));

    expect(
      await screen.findByText("업로드된 NDA가 없습니다"),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "NDA 업로드" }),
    ).toBeInTheDocument();
  });

  it("signs the current NDA from the panel and advances to Short List", async () => {
    const user = userEvent.setup();
    let tieredBuyer = {
      ...mockBuyer,
      tier: "TIER_1",
    };
    let ndas = [
      {
        id: "nda-1",
        transaction_id: "txn-1",
        party_type: "BUYER",
        buyer_candidate_id: tieredBuyer.id,
        nda_type: "MUTUAL",
        status: "DRAFT",
        sent_at: null,
        signed_at: null,
        expires_at: null,
        document_url: null,
        counterparty_name: tieredBuyer.company_name,
        jurisdiction: null,
        confidentiality_period_months: null,
        notes: null,
        created_at: "2026-03-01T00:00:00Z",
        updated_at: "2026-03-01T00:00:00Z",
      },
    ];

    server.use(
      http.get("*/api/ma/transactions/:txnId/buyers", () => {
        return HttpResponse.json({ items: [tieredBuyer], total: 1 });
      }),
      http.get("*/api/ma/transactions/:txnId/ndas", () => {
        return HttpResponse.json(ndas);
      }),
      http.get("*/api/ma/transactions/:txnId/ndas/:ndaId/markups", () => {
        return HttpResponse.json({
          items: [
            {
              id: "markup-1",
              nda_id: "nda-1",
              version_label: "v1",
              version_number: 1,
              version_date: "2026-03-01",
              source_party: null,
              markup_type: null,
              file_name: "nda-v1.pdf",
              file_size_bytes: 1024,
              changes_summary: "초안 검토본",
              key_changes: null,
              redline_issues_count: null,
              base_version_id: null,
              created_by_email: "advisor@test.com",
              created_at: "2026-03-01T00:00:00Z",
              updated_at: "2026-03-01T00:00:00Z",
              has_file: true,
              has_redline: false,
            },
          ],
          total: 1,
          limit: 50,
          offset: 0,
        });
      }),
      http.patch("*/api/ma/transactions/:txnId/ndas/:ndaId", async ({ request }) => {
        const body = (await request.json()) as Record<string, unknown>;
        ndas = ndas.map((nda) => ({
          ...nda,
          status: (body.status as string | undefined) ?? nda.status,
          signed_at: (body.signed_at as string | undefined) ?? nda.signed_at,
          updated_at: "2026-03-10T00:00:00Z",
        }));
        tieredBuyer = {
          ...tieredBuyer,
          status: "NDA_SIGNED",
          is_short_listed: true,
          updated_at: "2026-03-10T00:00:00Z",
        };
        return HttpResponse.json(ndas[0]);
      }),
    );

    renderTab();

    await waitFor(() => {
      expect(screen.getByRole("tab", { name: /NDA/i })).toHaveAttribute(
        "aria-selected",
        "true",
      );
    });

    await user.click(screen.getByRole("button", { name: tieredBuyer.company_name }));
    await user.click(await screen.findByRole("button", { name: "날인" }));

    await waitFor(() => {
      expect(screen.getByRole("tab", { name: /Short List/i })).toHaveAttribute(
        "aria-selected",
        "true",
      );
    });

    const grid = await screen.findByTestId("marketing-grid");
    expect(within(grid).getByTestId("grid-cell-NDA_SIGNED")).toHaveTextContent(
      /\d{2}-\d{2}/,
    );
  });

  it("allows returning to Short List even when the NDA step is locked", async () => {
    const user = userEvent.setup();
    const shortlistedBuyer = {
      ...mockBuyer,
      id: "buyer-return-shortlist",
      company_name: "Return Short List Buyer",
      tier: "TIER_1" as const,
      status: "NDA_SIGNED" as const,
      is_short_listed: true,
      created_at: "2026-01-01T00:00:00Z",
      updated_at: "2026-03-10T00:00:00Z",
    };

    server.use(
      http.get("*/api/ma/transactions/:txnId/buyers", () => {
        return HttpResponse.json({
          items: [shortlistedBuyer],
          total: 1,
        });
      }),
      http.get("*/api/ma/transactions/:txnId/ndas", () => {
        return HttpResponse.json([]);
      }),
      http.get("*/api/ma/transactions/:txnId/short-list/overview", () => {
        return HttpResponse.json([]);
      }),
    );

    renderTab();

    const shortListTab = await screen.findByRole("tab", { name: /Short List/i });

    await waitFor(() => {
      expect(shortListTab).toHaveAttribute("aria-selected", "true");
    });

    await user.click(screen.getByRole("tab", { name: /Long List/i }));

    await waitFor(() => {
      expect(screen.getByRole("tab", { name: /Long List/i })).toHaveAttribute(
        "aria-selected",
        "true",
      );
    });

    await user.click(shortListTab);

    await waitFor(() => {
      expect(screen.getByRole("tab", { name: /Short List/i })).toHaveAttribute(
        "aria-selected",
        "true",
      );
    });
  });

  it("keeps the NDA count aligned with short list buyers and backfills shortlist stages", async () => {
    const shortlistedBuyer = {
      ...mockBuyer,
      id: "buyer-short",
      company_name: "Short List Buyer",
      tier: "TIER_1" as const,
      status: "NDA_SIGNED" as const,
      is_short_listed: true,
      created_at: "2026-01-01T00:00:00Z",
      updated_at: "2026-03-10T00:00:00Z",
    };

    server.use(
      http.get("*/api/ma/transactions/:txnId/buyers", () => {
        return HttpResponse.json({
          items: [shortlistedBuyer],
          total: 1,
        });
      }),
      http.get("*/api/ma/transactions/:txnId/ndas", () => {
        return HttpResponse.json([]);
      }),
      http.get("*/api/ma/transactions/:txnId/short-list/overview", () => {
        return HttpResponse.json([]);
      }),
    );

    renderTab();

    const ndaTab = await screen.findByRole("tab", { name: /NDA/i });
    const shortListTab = screen.getByRole("tab", { name: /Short List/i });

    await waitFor(() => {
      expect(shortListTab).toHaveAttribute("aria-selected", "true");
    });

    expect(ndaTab.textContent?.match(/\d+/)?.[0]).toBe("1");
    expect(shortListTab.textContent?.match(/\d+/)?.[0]).toBe("1");

    const grid = await screen.findByTestId("marketing-grid");
    expect(within(grid).getByTestId("grid-cell-IDENTIFIED")).toHaveTextContent(
      "01-01",
    );
    expect(within(grid).getByTestId("grid-cell-NDA_SIGNED")).toHaveTextContent(
      "03-10",
    );
  });

  it("treats tiered buyers with signed NDAs as short list even when the flag is stale", async () => {
    const syncedBuyer = {
      ...mockBuyer,
      id: "buyer-synced",
      company_name: "Synced Buyer",
      tier: "TIER_1" as const,
      status: "CONTACTED" as const,
      is_short_listed: false,
      created_at: "2026-01-01T00:00:00Z",
      updated_at: "2026-03-10T00:00:00Z",
    };

    server.use(
      http.get("*/api/ma/transactions/:txnId/buyers", () => {
        return HttpResponse.json({
          items: [syncedBuyer],
          total: 1,
        });
      }),
      http.get("*/api/ma/transactions/:txnId/ndas", () => {
        return HttpResponse.json([
          {
            id: "nda-signed",
            transaction_id: "txn-1",
            party_type: "BUYER",
            buyer_candidate_id: syncedBuyer.id,
            nda_type: "MUTUAL",
            status: "SIGNED",
            sent_at: null,
            signed_at: "2026-03-10",
            expires_at: null,
            document_url: null,
            notes: null,
            counterparty_name: syncedBuyer.company_name,
            created_at: "2026-03-10T00:00:00Z",
            updated_at: "2026-03-10T00:00:00Z",
          },
        ]);
      }),
      http.get("*/api/ma/transactions/:txnId/short-list/overview", () => {
        return HttpResponse.json([]);
      }),
    );

    renderTab();

    const ndaTab = await screen.findByRole("tab", { name: /NDA/i });
    const shortListTab = screen.getByRole("tab", { name: /Short List/i });

    await waitFor(() => {
      expect(shortListTab).toHaveAttribute("aria-selected", "true");
    });

    expect(ndaTab.textContent?.match(/\d+/)?.[0]).toBe("1");
    expect(shortListTab.textContent?.match(/\d+/)?.[0]).toBe("1");
    expect(screen.queryByText("Long List 후보 없음")).not.toBeInTheDocument();
  });

  it("keeps shortlist stages visible when a newer draft NDA exists after a signed NDA", async () => {
    const buyerWithMultipleNdas = {
      ...mockBuyer,
      id: "buyer-multi-nda",
      company_name: "Multi NDA Buyer",
      tier: "TIER_1" as const,
      status: "CONTACTED" as const,
      is_short_listed: false,
      created_at: "2026-01-01T00:00:00Z",
      updated_at: "2026-03-20T00:00:00Z",
    };

    server.use(
      http.get("*/api/ma/transactions/:txnId/buyers", () => {
        return HttpResponse.json({
          items: [buyerWithMultipleNdas],
          total: 1,
        });
      }),
      http.get("*/api/ma/transactions/:txnId/ndas", () => {
        return HttpResponse.json([
          {
            id: "nda-signed-older",
            transaction_id: "txn-1",
            party_type: "BUYER",
            buyer_candidate_id: buyerWithMultipleNdas.id,
            nda_type: "MUTUAL",
            status: "SIGNED",
            sent_at: null,
            signed_at: "2026-03-10",
            expires_at: null,
            document_url: null,
            notes: null,
            counterparty_name: buyerWithMultipleNdas.company_name,
            created_at: "2026-03-10T00:00:00Z",
            updated_at: "2026-03-10T00:00:00Z",
          },
          {
            id: "nda-draft-newer",
            transaction_id: "txn-1",
            party_type: "BUYER",
            buyer_candidate_id: buyerWithMultipleNdas.id,
            nda_type: "MUTUAL",
            status: "DRAFT",
            sent_at: null,
            signed_at: null,
            expires_at: null,
            document_url: null,
            notes: null,
            counterparty_name: buyerWithMultipleNdas.company_name,
            created_at: "2026-03-20T00:00:00Z",
            updated_at: "2026-03-20T00:00:00Z",
          },
        ]);
      }),
      http.get("*/api/ma/transactions/:txnId/short-list/overview", () => {
        return HttpResponse.json([]);
      }),
    );

    renderTab();

    const ndaTab = await screen.findByRole("tab", { name: /NDA/i });
    const shortListTab = screen.getByRole("tab", { name: /Short List/i });

    await waitFor(() => {
      expect(shortListTab).toHaveAttribute("aria-selected", "true");
    });

    expect(ndaTab.textContent?.match(/\d+/)?.[0]).toBe("1");
    expect(shortListTab.textContent?.match(/\d+/)?.[0]).toBe("1");

    const grid = await screen.findByTestId("marketing-grid");
    expect(within(grid).getByTestId("grid-cell-IDENTIFIED")).toHaveTextContent(
      "01-01",
    );
    expect(within(grid).getByTestId("grid-cell-NDA_SIGNED")).toHaveTextContent(
      "03-10",
    );
  });

  it("shows teaser delivery status and version inside the long-list NDA / Teaser column", async () => {
    const teaserBuyer = {
      ...mockBuyer,
      id: "buyer-teaser",
      company_name: "Teaser Buyer",
      status: "CONTACTED" as const,
      is_short_listed: false,
    };

    server.use(
      http.get("*/api/ma/transactions/:txnId/buyers", () => {
        return HttpResponse.json({ items: [teaserBuyer], total: 1 });
      }),
      http.get("*/api/ma/transactions/:txnId/marketing-materials", () => {
        return HttpResponse.json([
          {
            id: "tm-1",
            transaction_id: "txn-1",
            doc_type: "TM",
            title: "Teaser v1",
            project_code: "TM-001",
            status: "READY",
            error_message: null,
            source_mode: "UPLOADED",
            attachment_id: "att-1",
            parameters: null,
            file_path: null,
            file_name: "teaser-v1.pdf",
            file_size_bytes: 1024,
            quality_score: null,
            quality_status: null,
            quality_issues: null,
            slide_count: null,
            pipeline_metrics: null,
            distribution_eligible: true,
            distributed_to: [teaserBuyer.company_name],
            distributed_at: "2026-03-20T00:00:00Z",
            created_by_email: "advisor@test.com",
            created_at: "2026-03-01T00:00:00Z",
            updated_at: "2026-03-20T00:00:00Z",
          },
        ]);
      }),
    );

    renderTab();

    expect(await screen.findByText(teaserBuyer.company_name)).toBeInTheDocument();
    expect(screen.getByText("NDA / Teaser")).toBeInTheDocument();
    expect(screen.getByText("Teaser v1")).toBeInTheDocument();
    expect(screen.getByText(/2026-03-20/)).toBeInTheDocument();
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
      await within(headerSlot as HTMLElement).findByRole(
        "button",
        { name: "Excel" },
        { timeout: 10000 },
      ),
    ).toBeInTheDocument();
  }, 10000);

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
