import { beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";

import BuyerNdaSection from "../BuyerNdaSection";

const mockUseNdas = vi.fn();
const uploadMutateAsync = vi.fn();
const startExtractionFromUpload = vi.fn();

vi.mock("@/modules/ma/hooks/useNdas", () => ({
  useNdas: () => mockUseNdas(),
  useCreateNda: () => ({ mutate: vi.fn(), isPending: false }),
  useUpdateNda: () => ({ mutate: vi.fn(), isPending: false }),
  useDeleteNda: () => ({ mutate: vi.fn(), isPending: false }),
}));

vi.mock("@/modules/ma/hooks/useAttachments", () => ({
  useUploadAttachment: () => ({
    mutateAsync: uploadMutateAsync,
    isPending: false,
  }),
}));

vi.mock("@/modules/ma/hooks/useAttachmentExtractionFlow", () => ({
  useAttachmentExtractionFlow: () => ({
    activeReview: null,
    closeReview: vi.fn(),
    startExtractionFromUpload,
  }),
}));

vi.mock("@/modules/ma/components/NdaVersionPanel", () => ({
  default: () => null,
}));

vi.mock("@/modules/ma/components/extraction/ExtractionReviewModal", () => ({
  default: () => null,
}));

describe("BuyerNdaSection", () => {
  beforeEach(() => {
    mockUseNdas.mockReturnValue({ data: [] });
    uploadMutateAsync.mockReset();
    startExtractionFromUpload.mockReset();
    uploadMutateAsync.mockResolvedValue({
      id: "att-1",
      transaction_id: "txn-1",
      entity_type: "NDA",
      entity_id: null,
      file_name: "buyer-nda.pdf",
      file_size_bytes: 128,
      mime_type: "application/pdf",
      description: null,
      uploaded_by_email: "test@example.com",
      created_at: "2026-03-25T00:00:00Z",
      updated_at: "2026-03-25T00:00:00Z",
      vdr_sync: null,
    });
  });

  it("uploads a dropped file from the empty-state dropzone", async () => {
    render(
      <BuyerNdaSection
        txnId="txn-1"
        canWrite
        buyer={{
          id: "buyer-1",
          transaction_id: "txn-1",
          company_name: "ATU파트너스",
          contact_name: null,
          contact_email: null,
          contact_phone: null,
          buyer_type: "FINANCIAL_SPONSOR",
          status: "IDENTIFIED",
          tier: null,
          deal_role: null,
          is_short_listed: false,
          corp_code: null,
          ioi_value: null,
          ioi_date: null,
          loi_value: null,
          loi_date: null,
          final_offer_value: null,
          rejection_reason: null,
          notes: null,
          extra_data: null,
          created_at: "2026-03-25T00:00:00Z",
          updated_at: "2026-03-25T00:00:00Z",
        }}
      />,
    );

    const dropZone = screen.getByRole("button", {
      name: "ATU파트너스 NDA 드래그 앤 드롭 업로드",
    });
    const file = new File(["pdf-content"], "buyer-nda.pdf", {
      type: "application/pdf",
    });
    const dataTransfer = {
      files: [file],
      types: ["Files"],
      dropEffect: "none",
    };

    fireEvent.dragEnter(dropZone, { dataTransfer });
    fireEvent.dragOver(dropZone, { dataTransfer });
    fireEvent.drop(dropZone, { dataTransfer });

    await waitFor(() => {
      expect(uploadMutateAsync).toHaveBeenCalledWith({
        file,
        entityType: "NDA",
        entityId: undefined,
      });
    });

    await waitFor(() => {
      expect(startExtractionFromUpload).toHaveBeenCalledWith({
        attachment: expect.objectContaining({
          id: "att-1",
          file_name: "buyer-nda.pdf",
        }),
        file,
        docCategoryHint: "NDA",
        reviewContext: {
          source: "buyer-nda",
          buyerCandidateId: "buyer-1",
        },
      });
    });
  });
});
