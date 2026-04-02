import { beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { toast } from "sonner";

import { maApi } from "@/api/maClient";
import BuyerNdaSection from "../BuyerNdaSection";

const mockUseNdas = vi.fn();
const mockUseAttachments = vi.fn();
const uploadMutateAsync = vi.fn();
const createNdaMutateAsync = vi.fn();
const uploadMarketingMaterialMutateAsync = vi.fn();
const startExtractionFromUpload = vi.fn();
const invalidateQueries = vi.fn();
const teaserUploadHandlerState = vi.hoisted(() => ({
  handler: null as
    | ((material: Record<string, unknown>, file: File) => Promise<void> | void)
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
  useAttachments: () => mockUseAttachments(),
  useUploadAttachment: () => ({
    mutateAsync: uploadMutateAsync,
    isPending: false,
  }),
  useDeleteAttachment: () => ({ mutate: vi.fn(), isPending: false }),
  useRetryAttachmentProcessing: () => ({ mutate: vi.fn(), isPending: false }),
  getAttachmentDownloadUrl: () => "#",
}));

vi.mock("@/modules/ma/hooks/useAttachmentExtractionFlow", () => ({
  canStartExtractionFromUpload: (
    attachment: {
      mime_type?: string;
      processing_status?: string;
      vdr_sync?: { vdr_document_id?: string } | null;
    },
    file: File,
  ) =>
    attachment.processing_status === "SYNCED" &&
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
  useUploadMarketingMaterial: () => ({
    mutateAsync: uploadMarketingMaterialMutateAsync,
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
    onUploadedMaterial,
  }: {
    onUploadedMaterial: (
      material: Record<string, unknown>,
      file: File,
    ) => Promise<void> | void;
  }) => {
    teaserUploadHandlerState.handler = onUploadedMaterial;
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

function makeAttachment(overrides?: Record<string, unknown>) {
  return {
    id: "att-1",
    transaction_id: "txn-1",
    entity_type: "NDA",
    entity_id: "nda-1",
    file_name: "buyer-nda.pdf",
    file_size_bytes: 128,
    mime_type: "application/pdf",
    processing_status: "SYNCED",
    processing_error: null,
    description: null,
    uploaded_by_email: "test@example.com",
    created_at: "2026-03-25T00:00:00Z",
    updated_at: "2026-03-25T00:00:00Z",
    vdr_sync: {
      vdr_document_id: "vdr-1",
      folder_name: "NDA",
      category: "NDA",
      classification_status: "READY",
    },
    ...overrides,
  };
}

describe("BuyerNdaSection", () => {
  beforeEach(() => {
    mockUseNdas.mockReturnValue({ data: [] });
    mockUseAttachments.mockReturnValue({ data: { items: [] } });
    uploadMutateAsync.mockReset();
    createNdaMutateAsync.mockReset();
    uploadMarketingMaterialMutateAsync.mockReset();
    startExtractionFromUpload.mockReset();
    invalidateQueries.mockReset();
    teaserUploadHandlerState.handler = null;
    vi.mocked(toast.error).mockReset();
    vi.mocked(toast.warning).mockReset();
    vi.mocked(toast.info).mockReset();

    uploadMutateAsync.mockImplementation(
      async ({
        entityType,
        entityId,
        file,
      }: {
        entityType: string;
        entityId?: string;
        file: File;
      }) =>
        makeAttachment({
          entity_type: entityType,
          entity_id: entityId ?? null,
          file_name: file.name,
        }),
    );

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

    uploadMarketingMaterialMutateAsync.mockResolvedValue({
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
      distributed_to: ["ATU파트너스"],
      distributed_at: "2026-03-25T00:00:00Z",
      created_by_email: "test@example.com",
      created_at: "2026-03-25T00:00:00Z",
      updated_at: "2026-03-25T00:00:00Z",
    });

    vi.spyOn(maApi, "post").mockReset();
    vi.spyOn(maApi, "post").mockResolvedValue({
      data: {
        id: "markup-1",
      },
    });
    vi.spyOn(maApi, "get").mockReset();
    vi.spyOn(maApi, "get").mockResolvedValue({
      data: { items: [], total: 0 },
    } as never);
  });

  it("creates an NDA record, uploads against nda.id, and creates the first version", async () => {
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
      expect(createNdaMutateAsync).toHaveBeenCalledWith({
        party_type: "BUYER",
        buyer_candidate_id: "buyer-1",
        counterparty_name: "ATU파트너스",
        nda_type: "MUTUAL",
      });
    });

    await waitFor(() => {
      expect(uploadMutateAsync).toHaveBeenCalledWith({
        file,
        entityType: "NDA",
        entityId: "nda-1",
      });
    });

    await waitFor(() => {
      expect(maApi.post).toHaveBeenCalledWith(
        "/transactions/txn-1/ndas/nda-1/markups",
        expect.any(FormData),
      );
    });

    const formData = vi.mocked(maApi.post).mock.calls[0]?.[1] as FormData;
    expect(formData.get("attachment_id")).toBe("att-1");
    expect(formData.get("version_label")).toBe("buyer-nda");
    expect(formData.get("version_date")).toBeTruthy();

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
            entity_id: "nda-1",
            file_name: "buyer-nda.pdf",
          }),
          file,
          docCategoryHint: "NDA",
          targetModel: "nda",
          targetId: "nda-1",
          autoApplySignedAt: true,
          reviewContext: {
            source: "buyer-nda",
            buyerCandidateId: "buyer-1",
          },
        },
        {
          successToast: "NDA OCR 분석을 시작했습니다.",
          failureToast: "파일은 업로드됐지만 OCR 시작에는 실패했습니다.",
          failureToastVariant: "warning",
        },
      );
    });
  });

  it("reuses the existing NDA instead of creating a second one", async () => {
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
      expect(uploadMutateAsync).toHaveBeenCalledWith({
        file,
        entityType: "NDA",
        entityId: "nda-existing",
      });
    });

    await waitFor(() => {
      expect(maApi.post).toHaveBeenCalledWith(
        "/transactions/txn-1/ndas/nda-existing/markups",
        expect.any(FormData),
      );
    });
  });

  it("keeps the upload successful but stops before OCR when markup creation fails", async () => {
    vi.mocked(maApi.post).mockRejectedValueOnce({
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
      expect(startExtractionFromUpload).not.toHaveBeenCalled();
    });

    expect(toast.error).toHaveBeenCalledWith(
      expect.stringContaining("NDA 버전 생성에는 실패했습니다."),
    );
  });

  it("checks the created teaser material attachment status without starting OCR yet", async () => {
    render(<BuyerNdaSection txnId="txn-1" canWrite buyer={buyer} />);

    const file = new File(["pdf-content"], "atu-teaser.pdf", {
      type: "application/pdf",
    });

    await teaserUploadHandlerState.handler?.(
      {
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
      },
      file,
    );

    expect(maApi.get).toHaveBeenCalledWith("/transactions/txn-1/attachments", {
      params: {
        entity_type: "MARKETING_MATERIAL",
        entity_id: "tm-1",
      },
    });
    expect(startExtractionFromUpload).not.toHaveBeenCalled();
  });

  it("reuses the created teaser material as the OCR review target when VDR sync exists", async () => {
    vi.spyOn(maApi, "get").mockResolvedValue({
      data: {
        items: [
          {
            id: "att-tm-1",
            transaction_id: "txn-1",
            entity_type: "MARKETING_MATERIAL",
            entity_id: "tm-1",
            file_name: "atu-teaser.pdf",
            file_size_bytes: 256,
            mime_type: "application/pdf",
            processing_status: "SYNCED",
            processing_error: null,
            description: null,
            uploaded_by_email: "test@example.com",
            created_at: "2026-03-25T00:00:00Z",
            updated_at: "2026-03-25T00:00:00Z",
            vdr_sync: {
              vdr_document_id: "vdr-1",
              folder_name: "TM",
              category: "TM",
              classification_status: "READY",
            },
          },
        ],
        total: 1,
      },
    } as never);
    render(<BuyerNdaSection txnId="txn-1" canWrite buyer={buyer} />);

    const file = new File(["pdf-content"], "atu-teaser.pdf", {
      type: "application/pdf",
    });

    await teaserUploadHandlerState.handler?.(
      {
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
      },
      file,
    );

    expect(startExtractionFromUpload).toHaveBeenCalledWith({
      attachment: expect.objectContaining({
        id: "att-tm-1",
        entity_id: "tm-1",
        file_name: "atu-teaser.pdf",
      }),
      file,
      docCategoryHint: "TEASER_IM",
      targetModel: "marketing_material",
      targetId: "tm-1",
      reviewContext: {
        source: "marketing-material",
        marketingDocType: "TM",
        marketingMaterialId: "tm-1",
      },
    });
  });

  it("starts OCR later when the uploaded NDA attachment finishes syncing", async () => {
    let currentAttachmentItems: ReturnType<typeof makeAttachment>[] = [];
    let currentNdas: Array<Record<string, unknown>> = [];
    mockUseNdas.mockImplementation(() => ({ data: currentNdas }));
    uploadMutateAsync.mockResolvedValueOnce(
      makeAttachment({
        processing_status: "PENDING",
        vdr_sync: null,
      }),
    );
    mockUseAttachments.mockImplementation(() => ({
      data: { items: currentAttachmentItems },
    }));

    const { rerender } = render(
      <BuyerNdaSection txnId="txn-1" canWrite buyer={buyer} />,
    );

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
      expect(startExtractionFromUpload).not.toHaveBeenCalled();
    });

    currentAttachmentItems = [
      makeAttachment({
        processing_status: "SYNCED",
        entity_id: "nda-1",
        vdr_sync: {
          vdr_document_id: "vdr-1",
          folder_name: "NDA",
          category: "NDA",
          classification_status: "READY",
        },
      }),
    ];
    currentNdas = [
      {
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
      },
    ];
    rerender(<BuyerNdaSection txnId="txn-1" canWrite buyer={buyer} />);

    await waitFor(() => {
      expect(startExtractionFromUpload).toHaveBeenCalledWith(
        {
          attachment: expect.objectContaining({
            id: "att-1",
            processing_status: "SYNCED",
          }),
          file,
          docCategoryHint: "NDA",
          targetModel: "nda",
          targetId: "nda-1",
          autoApplySignedAt: true,
          reviewContext: {
            source: "buyer-nda",
            buyerCandidateId: "buyer-1",
          },
        },
        {
          successToast: "NDA OCR 분석을 시작했습니다.",
          failureToast: "파일은 업로드됐지만 OCR 시작에는 실패했습니다.",
          failureToastVariant: "warning",
        },
      );
    });
  });
});
