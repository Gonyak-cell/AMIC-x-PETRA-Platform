import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
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

import ModelsTab from "../ModelsTab";

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
          <ModelsTab
            txnId={props.txnId ?? "txn-1"}
            canWrite={props.canWrite ?? true}
          />
        </AuthContext.Provider>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("ModelsTab", () => {
  beforeEach(() => {
    server.resetHandlers();
  });

  it("첨부 업로드 대신 VDR 입력 소스 목록을 표시한다", async () => {
    server.use(
      http.get("*/api/ma/transactions/:txnId/financial-models", () =>
        HttpResponse.json([]),
      ),
      http.get(
        "*/api/ma/transactions/:txnId/financial-models/source-routing-preview",
        () =>
          HttpResponse.json({
            version: "1.1",
            summary: {
              total_documents: 2,
              included_for_financial_model: 1,
              excluded_from_financial_model: 1,
              manual_review_documents: 1,
              overridden_documents: 0,
              by_primary_workstream: {
                FDD: 1,
                VALUATION: 1,
              },
              target_workstreams: ["FDD", "VALUATION"],
            },
            documents: [
              {
                document_id: "doc-1",
                original_name: "historical_financials.xlsx",
                folder_category: "FINANCIAL",
                ddrl_sections: ["CAPITAL"],
                primary_workstream: "FDD",
                workstream_tags: ["FDD"],
                confidence: 0.94,
                requires_manual_review: false,
                reasons: [],
                include_for_financial_model: true,
              },
              {
                document_id: "doc-2",
                original_name: "industry_teaser.pdf",
                folder_category: "COMMERCIAL",
                ddrl_sections: [],
                primary_workstream: "COMMON",
                workstream_tags: ["COMMON"],
                confidence: 0.58,
                requires_manual_review: true,
                reasons: [],
                include_for_financial_model: false,
              },
            ],
          }),
      ),
    );

    renderTab();

    await waitFor(() => {
      expect(screen.getByText("VDR 입력 소스")).toBeInTheDocument();
    });

    expect(
      await screen.findByText("historical_financials.xlsx"),
    ).toBeInTheDocument();
    expect(await screen.findByText("industry_teaser.pdf")).toBeInTheDocument();
    expect(await screen.findByText("모델 입력 포함")).toBeInTheDocument();
    expect(screen.queryByText("첨부 파일")).not.toBeInTheDocument();
  });
});
