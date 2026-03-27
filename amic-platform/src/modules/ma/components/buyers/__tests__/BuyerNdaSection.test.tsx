import { beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";

import { maApi } from "@/api/maClient";
import BuyerNdaSection from "../BuyerNdaSection";

const mockUseNdas = vi.fn();
const uploadMutateAsync = vi.fn();
const startExtractionFromUpload = vi.fn();
const createNdaMutateAsync = vi.fn();
const invalidateQueries = vi.fn();

vi.mock("@tanstack/react-query", () => ({
  useQueryClient: () => ({
    invalidateQueries,
  }),
}));

vi.mock("@/modules/ma/hooks/useNdas", () => ({
  useNdas: () => mockUseNdas(),
  useCreateNda: () => ({
    mutate: vi.fn(),
    mutateAsync: createNdaMutateAsync,
    isPending: false,
  }),
  useUpdateNda: () => ({ mutate: vi.fn(), isPending: false }),
  useDeleteNda: () => ({ mutate: vi.fn(), isPending: false }),
}));

vi.mock("@/modules/ma/hooks/useAttachments", () => ({
  useAttachments: () => ({ data: { items: [] } }),
  useUploadAttachment: () => ({
    mutateAsync: uploadMutateAsync,
    isPending: false,
  }),
  useDeleteAttachment: () => ({ mutate: vi.fn(), isPending: false }),
  getAttachmentDownloadUrl: () => "#",
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

vi.mock("../BuyerTeaserSection", () => ({
  default: () => <div>buyer-teaser-section</div>,
}));

const buyer = {
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
} as const;

describe("BuyerNdaSection", () => {
  beforeEach(() => {
    mockUseNdas.mockReturnValue({ data: [] });
    uploadMutateAsync.mockReset();
    startExtractionFromUpload.mockReset();
    createNdaMutateAsync.mockReset();
    invalidateQueries.mockReset();

    vi.spyOn(maApi, "post").mockReset();

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
    createNdaMutateAsync.mockResolvedValue({
      id: "nda-1",
      transaction_id: "txn-1",
      party_type: "BUYER",
      buyer_candidate_id: "buyer-1",
      counterparty_name: "ATU파트너스",
      nda_type: "MUTUAL",
      status: "DRAFT",
      sent_at: null,
      signed_at: null,
      expires_at: null,
      notes: null,
      created_at: "2026-03-25T00:00:00Z",
      updated_at: "2026-03-25T00:00:00Z",
    });
    vi.spyOn(maApi, "post").mockResolvedValue({
      data: {
        id: "markup-1",
      },
    });
  });

  it("creates an NDA record and first version after a dropped upload", async () => {
    render(<BuyerNdaSection txnId="txn-1" canWrite buyer={buyer} />);

    const dropZone = screen.getByRole("button", { name: /NDA 없음/ });
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
      expect(createNdaMutateAsync).toHaveBeenCalledWith({
        party_type: "BUYER",
        buyer_candidate_id: "buyer-1",
        counterparty_name: "ATU파트너스",
        nda_type: "MUTUAL",
      });
    });

    await waitFor(() => {
      expect(maApi.post).toHaveBeenCalledWith(
        "/transactions/txn-1/ndas/nda-1/markups",
        expect.any(FormData),
        {
          headers: { "Content-Type": "multipart/form-data" },
        },
      );
    });

    await waitFor(() => {
      expect(invalidateQueries).toHaveBeenCalledWith({
        queryKey: ["ma", "transactions", "txn-1", "ndas", "nda-1", "markups"],
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

  it("reuses the existing NDA and only adds a new version", async () => {
    mockUseNdas.mockReturnValue({
      data: [
        {
          id: "nda-existing",
          transaction_id: "txn-1",
          party_type: "BUYER",
          buyer_candidate_id: "buyer-1",
          counterparty_name: "ATU파트너스",
          nda_type: "MUTUAL",
          status: "SENT",
          sent_at: "2026-03-20",
          signed_at: null,
          expires_at: null,
          notes: null,
          created_at: "2026-03-20T00:00:00Z",
          updated_at: "2026-03-20T00:00:00Z",
        },
      ],
    });

    render(<BuyerNdaSection txnId="txn-1" canWrite buyer={buyer} />);

    const input = document.querySelector('input[type="file"]') as HTMLInputElement;
    const file = new File(["pdf-content"], "buyer-nda.pdf", {
      type: "application/pdf",
    });

    fireEvent.change(input, { target: { files: [file] } });

    await waitFor(() => {
      expect(createNdaMutateAsync).not.toHaveBeenCalled();
    });

    await waitFor(() => {
      expect(maApi.post).toHaveBeenCalledWith(
        "/transactions/txn-1/ndas/nda-existing/markups",
        expect.any(FormData),
        {
          headers: { "Content-Type": "multipart/form-data" },
        },
      );
    });
  });
});
