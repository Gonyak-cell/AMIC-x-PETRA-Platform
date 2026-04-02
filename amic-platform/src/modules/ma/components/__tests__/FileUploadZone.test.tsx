import { beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";

import FileUploadZone from "../FileUploadZone";

const mockUseAttachments = vi.fn();
const uploadMutateAsync = vi.fn();
const deleteMutate = vi.fn();
const retryMutate = vi.fn();

vi.mock("@/modules/ma/hooks/useAttachments", () => ({
  useAttachments: (...args: unknown[]) => mockUseAttachments(...args),
  useUploadAttachment: () => ({
    mutateAsync: uploadMutateAsync,
    isPending: false,
  }),
  useDeleteAttachment: () => ({
    mutate: deleteMutate,
    isPending: false,
  }),
  useRetryAttachmentProcessing: () => ({
    mutate: retryMutate,
    isPending: false,
  }),
  getAttachmentDownloadUrl: () => "#",
}));

describe("FileUploadZone", () => {
  beforeEach(() => {
    mockUseAttachments.mockReset();
    uploadMutateAsync.mockReset();
    deleteMutate.mockReset();
    retryMutate.mockReset();
    mockUseAttachments.mockReturnValue({
      data: { items: [] },
      isError: false,
    });
    uploadMutateAsync.mockImplementation(
      async ({
        entityId,
      }: {
        entityId?: string;
      }) => ({
        id: "att-1",
        transaction_id: "txn-1",
        entity_type: "NDA",
        entity_id: entityId ?? null,
        file_name: "buyer-nda.pdf",
        file_size_bytes: 128,
        mime_type: "application/pdf",
        processing_status: "PENDING",
        processing_error: null,
        description: null,
        uploaded_by_email: "test@example.com",
        created_at: "2026-03-25T00:00:00Z",
        updated_at: "2026-03-25T00:00:00Z",
        vdr_sync: null,
      }),
      );
  });

  it("shows an inline list error while keeping the upload zone available", () => {
    mockUseAttachments.mockReturnValue({
      data: { items: [] },
      isError: true,
    });

    render(
      <FileUploadZone
        txnId="txn-1"
        entityType="MARKETING_MATERIAL"
        entityId="TM"
        embedded
        emptyVariant="dashed"
        emptyTitle="등록된 Teaser 없음"
        suppressListErrorToast
        listErrorMessage="기존 Teaser 첨부 목록을 불러오지 못했습니다. 업로드는 계속 가능합니다."
      />,
    );

    expect(
      screen.getByText(
        "기존 Teaser 첨부 목록을 불러오지 못했습니다. 업로드는 계속 가능합니다.",
      ),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /등록된 Teaser 없음/ }),
    ).toBeInTheDocument();
    expect(mockUseAttachments).toHaveBeenCalledWith(
      "txn-1",
      "MARKETING_MATERIAL",
      "TM",
      expect.objectContaining({
        refetchWhileProcessing: true,
        suppressGlobalErrorToast: true,
      }),
    );
  });

  it("skips attachment list loading in upload-only mode", () => {
    mockUseAttachments.mockReturnValue({
      data: { items: [] },
      isError: true,
    });

    render(
      <FileUploadZone
        txnId="txn-1"
        entityType="MARKETING_MATERIAL"
        embedded
        uploadOnly
        emptyVariant="dashed"
        emptyTitle="등록된 Teaser 없음"
        listErrorMessage="기존 Teaser 첨부 목록을 불러오지 못했습니다. 업로드는 계속 가능합니다."
      />,
    );

    expect(
      screen.queryByText(
        "기존 Teaser 첨부 목록을 불러오지 못했습니다. 업로드는 계속 가능합니다.",
      ),
    ).not.toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /등록된 Teaser 없음/ }),
    ).toBeInTheDocument();
    expect(mockUseAttachments).toHaveBeenCalledWith(
      "txn-1",
      "MARKETING_MATERIAL",
      undefined,
      expect.objectContaining({
        enabled: false,
        refetchWhileProcessing: false,
      }),
    );
  });

  it("uploads a dropped file from the empty dashed state and sets dropEffect", async () => {
    const onUploaded = vi.fn();
    const resolveEntityId = vi.fn().mockResolvedValue("nda-1");

    render(
      <FileUploadZone
        txnId="txn-1"
        entityType="NDA"
        embedded
        emptyVariant="dashed"
        emptyTitle="NDA 없음"
        resolveEntityId={resolveEntityId}
        onUploaded={onUploaded}
      />,
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

    expect(dataTransfer.dropEffect).toBe("copy");

    fireEvent.drop(dropZone, { dataTransfer });

    await waitFor(() => {
      expect(resolveEntityId).toHaveBeenCalled();
    });

    await waitFor(() => {
      expect(uploadMutateAsync).toHaveBeenCalledWith({
        file,
        entityType: "NDA",
        entityId: "nda-1",
      });
    });

    await waitFor(() => {
      expect(onUploaded).toHaveBeenCalledWith(
        expect.objectContaining({
          id: "att-1",
          entity_id: "nda-1",
          file_name: "buyer-nda.pdf",
        }),
        file,
      );
    });
  });
});
