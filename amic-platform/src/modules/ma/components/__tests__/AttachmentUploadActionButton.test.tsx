import { beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";

import AttachmentUploadActionButton from "../AttachmentUploadActionButton";

const mutateAsync = vi.fn();

vi.mock("@/modules/ma/hooks/useAttachments", () => ({
  useUploadAttachment: () => ({
    mutateAsync,
    isPending: false,
  }),
}));

describe("AttachmentUploadActionButton", () => {
  beforeEach(() => {
    mutateAsync.mockReset();
    mutateAsync.mockResolvedValue({
      id: "attachment-1",
      transaction_id: "txn-1",
      entity_type: "CONTRACT",
      entity_id: null,
      file_name: "spa.pdf",
      file_size_bytes: 1024,
      mime_type: "application/pdf",
      description: null,
      uploaded_by_email: null,
      created_at: "2026-03-22T00:00:00Z",
      updated_at: "2026-03-22T00:00:00Z",
    });
  });

  it("opens the file picker from the action button", () => {
    const clickSpy = vi
      .spyOn(HTMLInputElement.prototype, "click")
      .mockImplementation(() => {});

    render(
      <AttachmentUploadActionButton
        txnId="txn-1"
        entityType="CONTRACT"
        label="파일 업로드"
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: "파일 업로드" }));

    expect(clickSpy).toHaveBeenCalled();
    clickSpy.mockRestore();
  });

  it("uploads the selected files through the shared attachment mutation", async () => {
    const { container } = render(
      <AttachmentUploadActionButton
        txnId="txn-1"
        entityType="CONTRACT"
        label="파일 업로드"
      />,
    );

    const input = container.querySelector("input[type='file']");
    expect(input).not.toBeNull();

    const file = new File(["contract"], "spa.pdf", {
      type: "application/pdf",
    });

    fireEvent.change(input as HTMLInputElement, {
      target: { files: [file] },
    });

    expect(mutateAsync).toHaveBeenCalledWith({
      file,
      entityType: "CONTRACT",
      entityId: undefined,
    });
  });
});
