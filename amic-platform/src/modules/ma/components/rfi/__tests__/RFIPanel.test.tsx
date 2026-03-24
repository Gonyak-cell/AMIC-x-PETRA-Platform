import { beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";

import RFIPanel from "../RFIPanel";

const exportMutate = vi.fn();
const importMutate = vi.fn();
const generateMutate = vi.fn();
const uploadMutate = vi.fn();
const deleteMutate = vi.fn();
const attachmentsHook = vi.fn();

vi.mock("@/modules/ma/hooks/useRFI", () => ({
  useExportRFI: () => ({
    mutate: exportMutate,
    isPending: false,
  }),
  useImportRFI: () => ({
    mutate: importMutate,
    isPending: false,
  }),
  useGenerateRFI: () => ({
    mutate: generateMutate,
    isPending: false,
  }),
  useUploadAttachments: () => ({
    mutate: uploadMutate,
    isPending: false,
  }),
  useDeleteAttachment: () => ({
    mutate: deleteMutate,
    isPending: false,
  }),
  useRFIAttachments: () => attachmentsHook(),
}));

vi.mock("../RFIDashboard", () => ({
  default: () => <div>rfi-dashboard</div>,
}));

vi.mock("../RFIItemList", () => ({
  default: () => <div>rfi-item-list</div>,
}));

vi.mock("../RFIItemDetail", () => ({
  default: () => <div>rfi-item-detail</div>,
}));

vi.mock("../RFICreateModal", () => ({
  default: () => null,
}));

describe("RFIPanel", () => {
  beforeEach(() => {
    exportMutate.mockReset();
    importMutate.mockReset();
    generateMutate.mockReset();
    uploadMutate.mockReset();
    deleteMutate.mockReset();
    attachmentsHook.mockReset();
    attachmentsHook.mockReturnValue({ data: [] });
  });

  it("shows the RFI upload action in the toolbar", () => {
    render(<RFIPanel txnId="txn-1" />);

    expect(
      screen.getByRole("button", { name: "RFI 업로드" }),
    ).toBeInTheDocument();
  });

  it("renders uploaded RFI files in a separate section", () => {
    attachmentsHook.mockReturnValue({
      data: [
        {
          id: "att-1",
          thread_id: null,
          item_id: null,
          transaction_id: "txn-1",
          vdr_index: null,
          file_name: "existing-rfi.pdf",
          file_url: "https://example.com/existing-rfi.pdf",
          is_mapped: false,
          created_at: "2026-03-24T00:00:00Z",
        },
      ],
    });

    render(<RFIPanel txnId="txn-1" />);

    expect(screen.getByText("업로드한 RFI 파일 (1건)")).toBeInTheDocument();
    expect(screen.getByText("existing-rfi.pdf")).toBeInTheDocument();
    expect(screen.getByText("미매핑")).toBeInTheDocument();
  });

  it("uploads selected existing RFI files", () => {
    const { container } = render(<RFIPanel txnId="txn-1" />);

    const file = new File(["rfi"], "existing-rfi.pdf", {
      type: "application/pdf",
    });

    const uploadInput = container.querySelector(
      'input[aria-label="RFI 파일 선택"]',
    );
    expect(uploadInput).not.toBeNull();

    fireEvent.change(uploadInput as HTMLInputElement, {
      target: { files: [file] },
    });

    expect(uploadMutate).toHaveBeenCalledWith([file]);
  });
});
