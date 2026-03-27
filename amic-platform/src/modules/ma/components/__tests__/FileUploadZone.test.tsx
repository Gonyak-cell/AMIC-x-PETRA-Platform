import { beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";

import FileUploadZone from "../FileUploadZone";

const uploadMutateAsync = vi.fn();
const deleteMutate = vi.fn();

vi.mock("@/modules/ma/hooks/useAttachments", () => ({
  useAttachments: () => ({ data: { items: [] } }),
  useUploadAttachment: () => ({
    mutateAsync: uploadMutateAsync,
    isPending: false,
  }),
  useDeleteAttachment: () => ({
    mutate: deleteMutate,
    isPending: false,
  }),
  getAttachmentDownloadUrl: () => "#",
}));

describe("FileUploadZone", () => {
  beforeEach(() => {
    uploadMutateAsync.mockReset();
    deleteMutate.mockReset();
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

  it("uploads a dropped file from the empty dashed state and sets dropEffect", async () => {
    const onUploaded = vi.fn();

    render(
      <FileUploadZone
        txnId="txn-1"
        entityType="NDA"
        embedded
        emptyVariant="dashed"
        emptyTitle="NDA 없음"
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
      expect(uploadMutateAsync).toHaveBeenCalledWith({
        file,
        entityType: "NDA",
        entityId: undefined,
      });
    });

    await waitFor(() => {
      expect(onUploaded).toHaveBeenCalledWith(
        expect.objectContaining({
          id: "att-1",
          file_name: "buyer-nda.pdf",
        }),
        file,
      );
    });
  });
});
