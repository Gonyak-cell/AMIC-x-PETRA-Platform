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
  title: "Project teaser",
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

  it("renders the VDR source preview instead of the attachment upload zone", async () => {
    server.use(
      http.get("*/api/ma/transactions/:txnId/marketing-materials", () =>
        HttpResponse.json([]),
      ),
      http.get(
        "*/api/ma/transactions/:txnId/marketing-materials/source-routing-preview",
        () =>
          HttpResponse.json({
            version: "1.1",
            summary: {
              total_documents: 2,
              included_for_marketing_material: 1,
              excluded_from_marketing_material: 1,
              manual_review_documents: 1,
              overridden_documents: 0,
              by_primary_workstream: {
                COMMON: 1,
                LDD: 1,
              },
              target_workstreams: ["COMMON", "VALUATION", "FDD"],
            },
            documents: [
              {
                document_id: "doc-1",
                original_name: "company_overview.pdf",
                folder_category: "COMMERCIAL",
                ddrl_sections: ["CONTRACTS"],
                primary_workstream: "COMMON",
                workstream_tags: ["COMMON", "VALUATION"],
                confidence: 0.91,
                requires_manual_review: false,
                reasons: [],
                include_for_marketing_material: true,
              },
              {
                document_id: "doc-2",
                original_name: "tax_notice.pdf",
                folder_category: "TAX",
                ddrl_sections: ["TAX"],
                primary_workstream: "LDD",
                workstream_tags: ["LDD"],
                confidence: 0.76,
                requires_manual_review: true,
                reasons: [],
                include_for_marketing_material: false,
              },
            ],
          }),
      ),
    );

    renderTab();

    await waitFor(() => {
      expect(screen.getByText("VDR 입력 파일")).toBeInTheDocument();
    });

    expect(await screen.findByText("company_overview.pdf")).toBeInTheDocument();
    expect(await screen.findByText("tax_notice.pdf")).toBeInTheDocument();
    expect(await screen.findByText("마케팅 자료 입력 포함")).toBeInTheDocument();
    expect(screen.queryByText("첨부 파일")).not.toBeInTheDocument();
  });

  it("renders marketing materials in the table", async () => {
    server.use(
      http.get("*/api/ma/transactions/:txnId/marketing-materials", () =>
        HttpResponse.json([mockMaterial]),
      ),
    );

    renderTab();

    await waitFor(() => {
      expect(screen.getByText("Project teaser")).toBeInTheDocument();
    });

    expect(screen.getByText("TM")).toBeInTheDocument();
    expect(screen.getByText("100 KB")).toBeInTheDocument();
  });

  it("shows creation buttons when write access is enabled", async () => {
    renderTab({ canWrite: true });

    await waitFor(() => {
      expect(screen.getByText("+ Teaser (TM)")).toBeInTheDocument();
    });

    expect(screen.getByText("+ Discussion (DM)")).toBeInTheDocument();
    expect(screen.getByText("+ Information (IM)")).toBeInTheDocument();
  });

  it("hides creation buttons when write access is disabled", async () => {
    renderTab({ canWrite: false });

    await waitFor(() => {
      expect(screen.getByText("VDR 입력 파일")).toBeInTheDocument();
    });

    expect(screen.queryByText("+ Teaser (TM)")).not.toBeInTheDocument();
    expect(screen.queryByText("+ Discussion (DM)")).not.toBeInTheDocument();
    expect(screen.queryByText("+ Information (IM)")).not.toBeInTheDocument();
  });

  it("shows the download button for READY materials", async () => {
    server.use(
      http.get("*/api/ma/transactions/:txnId/marketing-materials", () =>
        HttpResponse.json([mockMaterial]),
      ),
    );

    renderTab();

    await waitFor(() => {
      expect(screen.getByText("다운로드")).toBeInTheDocument();
    });
  });
});
