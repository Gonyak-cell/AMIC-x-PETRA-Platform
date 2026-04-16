import { beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
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

import VdrTab from "../VdrTab";

const navigateSpy = vi.fn();
const reviewModalSpy = vi.fn();

vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual<typeof import("react-router-dom")>(
    "react-router-dom",
  );
  return {
    ...actual,
    useNavigate: () => navigateSpy,
  };
});

vi.mock("@/modules/ma/components/extraction/ExtractionReviewModal", () => ({
  default: (props: {
    extraction: { id: string } | null;
    open: boolean;
    onConfirmed?: () => void;
  }) => {
    if (!props.open || !props.extraction) {
      return null;
    }

    reviewModalSpy(props);

    return (
      <div data-testid="guided-review-modal">
        <button type="button" onClick={() => props.onConfirmed?.()}>
          complete-guided-review
        </button>
      </div>
    );
  },
}));

vi.mock("@/modules/ma/components/vdr/DirectUploadZone", () => ({
  default: (props: {
    onUploadComplete: (result: {
      results: Array<{
        document: { id: string };
      }>;
      pending_review_count: number;
      total_uploaded: number;
      failed_files: unknown[];
    }) => void;
  }) => (
    <button
      type="button"
      onClick={() =>
        props.onUploadComplete({
          results: [
            {
              document: {
                id: "doc-biz-1",
              },
            },
          ],
          pending_review_count: 0,
          total_uploaded: 1,
          failed_files: [],
        })
      }
    >
      trigger-guided-upload
    </button>
  ),
}));

const defaultAuth: AuthContextValue = {
  user: mockUser,
  isAuthenticated: true,
  isLoading: false,
  setAuthState: vi.fn(),
};

function renderTab() {
  const queryClient = createTestQueryClient();
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter
        initialEntries={[
          {
            pathname: "/ma/transactions/txn-1/vdr",
            search: "?upload=1&docHint=BIZ_REG_DOCS",
            state: {
              vdrUploadEntry: {
                returnTo: "/ma/transactions/txn-1?setup=company-info",
                returnLabel: "Company Info",
              },
            },
          },
        ]}
      >
        <AuthContext.Provider value={defaultAuth}>
          <VdrTab txnId="txn-1" />
        </AuthContext.Provider>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("VdrTab guided OCR upload", () => {
  beforeEach(() => {
    navigateSpy.mockReset();
    reviewModalSpy.mockReset();
    server.resetHandlers();
  });

  it("starts extraction automatically and opens the review modal for docHint uploads", async () => {
    let extractionRequestBody: Record<string, unknown> | null = null;

    server.use(
      http.get("*/api/ma/transactions/:txnId/vdr/summary", () =>
        HttpResponse.json({
          total_folders: 2,
          total_documents: 5,
          total_size_bytes: 1024000,
          initialized: true,
        }),
      ),
      http.get("*/api/ma/transactions/:txnId/vdr/folders", () =>
        HttpResponse.json([]),
      ),
      http.get("*/api/ma/transactions/:txnId/extractions", () =>
        HttpResponse.json({ items: [], total: 0 }),
      ),
      http.get("*/api/ma/transactions/:txnId/vdr/routing-queue", () =>
        HttpResponse.json({
          summary: {
            total_documents: 0,
            returned_documents: 0,
            open_documents: 0,
            reviewed_documents: 0,
            auto_routed_documents: 0,
            by_effective_workstream: {},
          },
          items: [],
        }),
      ),
      http.post("*/api/ma/transactions/:txnId/extractions", async ({ request }) => {
        extractionRequestBody = (await request.json()) as Record<string, unknown>;
        return HttpResponse.json(
          {
            id: "ext-biz-1",
            transaction_id: "txn-1",
            vdr_document_id: "doc-biz-1",
            doc_category: "BIZ_REG_DOCS",
            classification_confidence: 0.98,
            status: "PENDING",
            error_message: null,
            extracted_data: null,
            target_model: "transaction",
            target_id: null,
            auto_apply_signed_at: false,
            llm_cost_usd: 0.001,
            reviewed_by_email: null,
            reviewed_at: null,
            created_at: "2026-01-01T00:00:00Z",
            updated_at: "2026-01-01T00:00:00Z",
          },
          { status: 202 },
        );
      }),
      http.get("*/api/ma/transactions/:txnId/extractions/:extractionId", () =>
        HttpResponse.json({
          id: "ext-biz-1",
          transaction_id: "txn-1",
          vdr_document_id: "doc-biz-1",
          doc_category: "BIZ_REG_DOCS",
          classification_confidence: 0.98,
          status: "COMPLETED",
          error_message: null,
          extracted_data: {
            business_registration_number: "123-45-67890",
            business_type: "Software",
            business_item: "Platform development",
          },
          target_model: "transaction",
          target_id: null,
          auto_apply_signed_at: false,
          llm_cost_usd: 0.001,
          reviewed_by_email: null,
          reviewed_at: null,
          created_at: "2026-01-01T00:00:00Z",
          updated_at: "2026-01-01T00:00:02Z",
        }),
      ),
    );

    renderTab();

    const triggerUploadButton = await screen.findByRole("button", {
      name: "trigger-guided-upload",
    });

    fireEvent.click(triggerUploadButton);

    await waitFor(
      () => {
        expect(extractionRequestBody).toMatchObject({
          vdr_document_id: "doc-biz-1",
          doc_category_hint: "BIZ_REG_DOCS",
        });
      },
      { timeout: 5000 },
    );

    await waitFor(
      () => {
        expect(reviewModalSpy).toHaveBeenCalledTimes(1);
      },
      { timeout: 5000 },
    );

    expect(reviewModalSpy.mock.calls[0]?.[0]).toMatchObject({
      open: true,
      extraction: {
        id: "ext-biz-1",
      },
    });

    fireEvent.click(screen.getByRole("button", { name: "complete-guided-review" }));

    await waitFor(() => {
      expect(navigateSpy).toHaveBeenCalledWith(
        "/ma/transactions/txn-1?setup=company-info",
      );
    });
  });
});
