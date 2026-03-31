import { beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { toast } from "sonner";

import { maApi } from "@/api/maClient";
import BuyerNdaSection from "../BuyerNdaSection";

const mockUseNdas = vi.fn();
const uploadMutateAsync = vi.fn();
const startExtractionFromUpload = vi.fn();
const createNdaMutateAsync = vi.fn();
const createMarketingMaterialMutateAsync = vi.fn();
const invalidateQueries = vi.fn();
const teaserUploadHandlerState = vi.hoisted(() => ({
  handler: null as
    | ((attachment: Record<string, unknown>, file: File) => Promise<void> | void)
    | null,
}));

vi.mock("sonner", () => ({
  toast: {
    error: vi.fn(),
    success: vi.fn(),
    warning: vi.fn(),
    info: vi.fn(),
  },
}));

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
  canStartExtractionFromUpload: (
    attachment: { mime_type?: string; vdr_sync?: { vdr_document_id?: string } | null },
    file: File,
  ) =>
    Boolean(attachment.vdr_sync?.vdr_document_id) &&
    (attachment.mime_type === "application/pdf" ||
      file.type === "application/pdf" ||
      file.name.toLowerCase().endsWith(".pdf")),
  useAttachmentExtractionFlow: () => ({
    activeReview: null,
    closeReview: vi.fn(),
    startExtractionFromUpload,
  }),
}));

vi.mock("@/modules/ma/hooks/useMarketingMaterials", () => ({
  useCreateMarketingMaterial: () => ({
    mutateAsync: createMarketingMaterialMutateAsync,
    isPending: false,
  }),
}));

vi.mock("@/modules/ma/components/NdaVersionPanel", () => ({
  default: () => null,
}));

vi.mock("@/modules/ma/components/extraction/ExtractionReviewModal", () => ({
  default: () => null,
}));

vi.mock("../BuyerTeaserSection", () => ({
  default: ({
    onUploaded,
  }: {
    onUploaded: (
      attachment: Record<string, unknown>,
      file: File,
    ) => Promise<void> | void;
  }) => {
    teaserUploadHandlerState.handler = onUploaded;
    return <div>buyer-teaser-section</div>;
  },
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
    createMarketingMaterialMutateAsync.mockReset();
    invalidateQueries.mockReset();
    teaserUploadHandlerState.handler = null;
    vi.mocked(toast.error).mockReset();

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
    createMarketingMaterialMutateAsync.mockResolvedValue({
      id: "tm-1",
      transaction_id: "txn-1",
      doc_type: "TM",
      title: "atu-teaser",
      project_code: null,
      status: "READY",
      error_message: null,
      source_mode: "UPLOADED",
      attachment_id: "att-tm-1",
      parameters: null,
      file_path: "/uploads/tm.pdf",
      file_name: "atu-teaser.pdf",
      file_size_bytes: 256,
      quality_score: null,
      quality_status: "SKIPPED",
      quality_issues: null,
      slide_count: null,
      pipeline_metrics: null,
      distribution_eligible: true,
      distributed_to: ["ATU?뚰듃?덉뒪"],
      distributed_at: "2026-03-25T00:00:00Z",
      created_by_email: "test@example.com",
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
      expect(startExtractionFromUpload).toHaveBeenCalledWith(
        {
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
        },
        {
          successToast: "NDA OCR 분석을 시작했습니다.",
          failureToast: "파일은 업로드되었지만 OCR 시작에는 실패했습니다.",
          failureToastVariant: "warning",
        },
      );
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

  it("does not start OCR when NDA version registration fails after upload", async () => {
    vi.spyOn(maApi, "post").mockRejectedValueOnce({
      response: { status: 500 },
    });

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
      expect(uploadMutateAsync).toHaveBeenCalled();
    });

    await waitFor(() => {
      expect(createNdaMutateAsync).toHaveBeenCalled();
    });

    await waitFor(() => {
      expect(startExtractionFromUpload).not.toHaveBeenCalled();
    });

    expect(toast.error).toHaveBeenCalledWith(
      "파일은 업로드되었지만 NDA 버전 등록에는 실패했습니다. (HTTP 500)",
    );
  });

  it("creates and auto-distributes an uploaded teaser for the current buyer", async () => {
    render(<BuyerNdaSection txnId="txn-1" canWrite buyer={buyer} />);

    const file = new File(["pdf-content"], "atu-teaser.pdf", {
      type: "application/pdf",
    });

    await teaserUploadHandlerState.handler?.(
      {
        id: "att-tm-1",
        transaction_id: "txn-1",
        entity_type: "MARKETING_MATERIAL",
        entity_id: "TM",
        file_name: "atu-teaser.pdf",
        file_size_bytes: 256,
        mime_type: "application/pdf",
        description: null,
        uploaded_by_email: "test@example.com",
        created_at: "2026-03-25T00:00:00Z",
        updated_at: "2026-03-25T00:00:00Z",
        vdr_sync: null,
      },
      file,
    );

    expect(createMarketingMaterialMutateAsync).toHaveBeenCalledWith({
      doc_type: "TM",
      title: "atu-teaser",
      attachment_id: "att-tm-1",
      distributed_to: [buyer.company_name],
      distributed_at: expect.any(String),
    });
    expect(startExtractionFromUpload).not.toHaveBeenCalled();
  });

  it("reuses the created teaser material as the OCR review target when VDR sync exists", async () => {
    render(<BuyerNdaSection txnId="txn-1" canWrite buyer={buyer} />);

    const file = new File(["pdf-content"], "atu-teaser.pdf", {
      type: "application/pdf",
    });

    await teaserUploadHandlerState.handler?.(
      {
        id: "att-tm-1",
        transaction_id: "txn-1",
        entity_type: "MARKETING_MATERIAL",
        entity_id: "TM",
        file_name: "atu-teaser.pdf",
        file_size_bytes: 256,
        mime_type: "application/pdf",
        description: null,
        uploaded_by_email: "test@example.com",
        created_at: "2026-03-25T00:00:00Z",
        updated_at: "2026-03-25T00:00:00Z",
        vdr_sync: {
          vdr_document_id: "vdr-1",
        },
      },
      file,
    );

    expect(startExtractionFromUpload).toHaveBeenCalledWith({
      attachment: expect.objectContaining({
        id: "att-tm-1",
        file_name: "atu-teaser.pdf",
      }),
      file,
      docCategoryHint: "TEASER_IM",
      reviewContext: {
        source: "marketing-material",
        marketingDocType: "TM",
        marketingMaterialId: "tm-1",
      },
    });
  });
});
