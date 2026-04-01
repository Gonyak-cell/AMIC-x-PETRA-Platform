import { beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";

import FileUploadZone from "@/modules/ma/components/FileUploadZone";
import { SlidePanel } from "../SlidePanel";

const uploadMutateAsync = vi.fn();
const deleteMutate = vi.fn();
const retryMutate = vi.fn();

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
  useRetryAttachmentProcessing: () => ({
    mutate: retryMutate,
    isPending: false,
  }),
  getAttachmentDownloadUrl: () => "#",
}));

describe("SlidePanel", () => {
  beforeEach(() => {
    uploadMutateAsync.mockReset();
    deleteMutate.mockReset();
    retryMutate.mockReset();
    uploadMutateAsync.mockResolvedValue({
      id: "att-1",
      transaction_id: "txn-1",
      entity_type: "NDA",
      entity_id: null,
      file_name: "nda.pdf",
      file_size_bytes: 128,
      mime_type: "application/pdf",
      description: null,
      uploaded_by_email: "test@example.com",
      created_at: "2026-03-27T00:00:00Z",
      updated_at: "2026-03-27T00:00:00Z",
      processing_status: "PENDING",
      processing_error: null,
      vdr_sync: null,
    });
  });

  it("allows file drags within the panel overlay", () => {
    const { container } = render(
      <SlidePanel open onClose={vi.fn()} title="Buyer Detail">
        <div>content</div>
      </SlidePanel>,
    );

    const dialog = container.querySelector("dialog");
    expect(dialog).not.toBeNull();

    const file = new File(["pdf"], "tm.pdf", { type: "application/pdf" });
    const dataTransfer = {
      files: [file],
      types: ["Files"],
      dropEffect: "none",
    };

    expect(
      fireEvent.dragOver(dialog as HTMLElement, {
        dataTransfer,
      }),
    ).toBe(false);
    expect(dataTransfer.dropEffect).toBe("copy");

    expect(
      fireEvent.dragOver(document.body, {
        dataTransfer,
      }),
    ).toBe(false);

    expect(
      fireEvent.dragOver(window, {
        dataTransfer,
      }),
    ).toBe(false);
  });

  it("lets nested upload zones receive dropped files", async () => {
    render(
      <SlidePanel open onClose={vi.fn()} title="Buyer Detail">
        <FileUploadZone
          txnId="txn-1"
          entityType="NDA"
          embedded
          emptyVariant="dashed"
          emptyTitle="NDA 없음"
        />
      </SlidePanel>,
    );

    const dropZone = screen.getByRole("button", { name: /NDA 없음/ });
    const file = new File(["pdf"], "nda.pdf", { type: "application/pdf" });
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
  });
});
