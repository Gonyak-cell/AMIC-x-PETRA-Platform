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

const mockExternalUpload = {
  id: "att-1",
  transaction_id: "txn-1",
  entity_type: "MARKETING_MATERIAL",
  entity_id: "IM",
  file_name: "external-im.pdf",
  file_size_bytes: 524288,
  mime_type: "application/pdf",
  description: null,
  uploaded_by_email: "test@amic.kr",
  created_at: "2026-02-01T00:00:00Z",
  updated_at: "2026-02-01T00:00:00Z",
};

describe("MarketingMaterialsTab", () => {
  beforeEach(() => {
    server.resetHandlers();
  });

  it("renders the VDR source preview instead of a generic upload zone", async () => {
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

    expect(await screen.findByText("company_overview.pdf")).toBeInTheDocument();
    expect(await screen.findByText("tax_notice.pdf")).toBeInTheDocument();
    expect(
      screen.queryByText("\uCCA8\uBD80 \uD30C\uC77C"),
    ).not.toBeInTheDocument();
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
    expect(screen.getByText("100.0 KB")).toBeInTheDocument();
  });

  it("shows one action button per TM/DM/IM document type when write access is enabled", async () => {
    renderTab({ canWrite: true });

    await waitFor(() => {
    expect(screen.getByText("+ Teaser (TM)")).toBeInTheDocument();
    });

    expect(screen.getByText("+ Discussion (DM)")).toBeInTheDocument();
    expect(screen.getByText("+ Information (IM)")).toBeInTheDocument();
    expect(screen.queryByText(/^마케팅 자료$/)).not.toBeInTheDocument();
    expect(screen.queryByText(`TM ${"\uC5C5\uB85C\uB4DC"}`)).not.toBeInTheDocument();
    expect(screen.queryByText(`DM ${"\uC5C5\uB85C\uB4DC"}`)).not.toBeInTheDocument();
    expect(screen.queryByText(`IM ${"\uC5C5\uB85C\uB4DC"}`)).not.toBeInTheDocument();
  });

  it("opens a choice modal for each document type and can trigger generation", async () => {
    const createRequestSpy = vi.fn();

    server.use(
      http.post("*/api/ma/transactions/:txnId/marketing-materials", async ({ request }) => {
        createRequestSpy(await request.json());
        return HttpResponse.json({
          ...mockMaterial,
          id: "mat-generated",
          doc_type: "TM",
          title: "Generated teaser",
        });
      }),
    );

    renderTab({ canWrite: true });

    await waitFor(() => {
      expect(screen.getByText("+ Teaser (TM)")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText("+ Teaser (TM)"));

    expect(await screen.findByText("Teaser (TM) 선택")).toBeInTheDocument();
    expect(screen.getByText("TM 생성")).toBeInTheDocument();
    expect(screen.getByText("TM 업로드")).toBeInTheDocument();

    fireEvent.click(screen.getByText("TM 생성"));

    await waitFor(() => {
      expect(createRequestSpy).toHaveBeenCalledWith(
        expect.objectContaining({ doc_type: "TM" }),
      );
    });

    await waitFor(() => {
      expect(screen.queryByText("Teaser (TM) 선택")).not.toBeInTheDocument();
    });
  });

  it("hides marketing material action buttons when write access is disabled", async () => {
    renderTab({ canWrite: false });

    await waitFor(() => {
      expect(
        screen.getByText("\uB9C8\uCF00\uD305 \uC790\uB8CC \uC5C6\uC74C"),
      ).toBeInTheDocument();
    });

    expect(screen.queryByText("+ Teaser (TM)")).not.toBeInTheDocument();
    expect(screen.queryByText("+ Discussion (DM)")).not.toBeInTheDocument();
    expect(screen.queryByText("+ Information (IM)")).not.toBeInTheDocument();
  });

  it("uses the DM upload card itself as the drop area without extra helper text", async () => {
    const dmUploadTitle = `DM ${"\uC5C5\uB85C\uB4DC"}`;
    const dmUploadDescription =
      "\uC678\uBD80\uC5D0\uC11C \uC791\uC131\uD55C DM \uD30C\uC77C\uC744 \uBC14\uB85C \uB4F1\uB85D\uD569\uB2C8\uB2E4.";

    renderTab({ canWrite: true });

    await waitFor(() => {
      expect(screen.getByText("+ Discussion (DM)")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText("+ Discussion (DM)"));

    expect(await screen.findByText(dmUploadTitle)).toBeInTheDocument();
    expect(screen.getByText(dmUploadDescription)).toBeInTheDocument();
    expect(screen.queryByText("Upload Files")).not.toBeInTheDocument();
    expect(
      screen.queryByText("Drop TM/DM/IM PDF files here to OCR and prefill metadata."),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByText(
        "PDF uploads open a review modal after OCR. Non-PDF uploads remain as attachments only.",
      ),
    ).not.toBeInTheDocument();

    const description = screen.getByText(dmUploadDescription);
    expect(description.closest("[data-file-dropzone='true']")).not.toBeNull();
  });

  it("uses the TM upload card itself as the drop area without extra helper text", async () => {
    const tmUploadTitle = `TM ${"\uC5C5\uB85C\uB4DC"}`;
    const tmUploadDescription =
      "\uC678\uBD80\uC5D0\uC11C \uC791\uC131\uD55C TM \uD30C\uC77C\uC744 \uBC14\uB85C \uB4F1\uB85D\uD569\uB2C8\uB2E4.";

    renderTab({ canWrite: true });

    await waitFor(() => {
      expect(screen.getByText("+ Teaser (TM)")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText("+ Teaser (TM)"));

    expect(await screen.findByText(tmUploadTitle)).toBeInTheDocument();
    expect(screen.getByText(tmUploadDescription)).toBeInTheDocument();
    expect(screen.queryByText("Upload Files")).not.toBeInTheDocument();
    expect(
      screen.queryByText("Drop TM/DM/IM PDF files here to OCR and prefill metadata."),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByText(
        "PDF uploads open a review modal after OCR. Non-PDF uploads remain as attachments only.",
      ),
    ).not.toBeInTheDocument();

    const description = screen.getByText(tmUploadDescription);
    expect(description.closest("[data-file-dropzone='true']")).not.toBeNull();
  });

  it("renders externally uploaded materials in a separate section", async () => {
    server.use(
      http.get("*/api/ma/transactions/:txnId/marketing-materials", () =>
        HttpResponse.json([]),
      ),
      http.get("*/api/ma/transactions/:txnId/attachments", () =>
        HttpResponse.json({ items: [mockExternalUpload], total: 1 }),
      ),
    );

    renderTab();

    await waitFor(() => {
      expect(screen.getByText("external-im.pdf")).toBeInTheDocument();
    });

    expect(
      screen.getByText("\uC678\uBD80 \uC5C5\uB85C\uB4DC \uC790\uB8CC"),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/Information Memo .*본|Information Memo 업로드본/),
    ).toBeInTheDocument();
    expect(screen.getByText("512.0 KB")).toBeInTheDocument();
  });

  it("shows the download button for READY materials", async () => {
    server.use(
      http.get("*/api/ma/transactions/:txnId/marketing-materials", () =>
        HttpResponse.json([mockMaterial]),
      ),
    );

    renderTab();

    await waitFor(() => {
      expect(
        screen.getAllByText("\uB2E4\uC6B4\uB85C\uB4DC")[0],
      ).toBeInTheDocument();
    });
  });
});
