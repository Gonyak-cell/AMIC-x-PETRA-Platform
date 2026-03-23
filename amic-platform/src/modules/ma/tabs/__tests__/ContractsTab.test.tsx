import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";

import ContractsTab from "../ContractsTab";

let mockContracts: unknown[] = [];
let mockContractSummary: unknown = undefined;

vi.mock("@/modules/ma/hooks/useContracts", () => ({
  useContracts: () => ({ data: mockContracts }),
  useContractSummary: () => ({ data: mockContractSummary }),
  useCreateContract: () => ({ mutate: vi.fn(), isPending: false }),
  useUpdateContract: () => ({ mutate: vi.fn(), isPending: false }),
  useDeleteContract: () => ({ mutate: vi.fn(), isPending: false }),
  useAnalyzeContract: () => ({ mutate: vi.fn(), isPending: false }),
}));

vi.mock("@/modules/ma/hooks/useAttachments", () => ({
  useAttachments: () => ({ data: { items: [] } }),
  useUploadAttachment: () => ({
    mutate: vi.fn(),
    mutateAsync: vi.fn(),
    isPending: false,
  }),
  useDeleteAttachment: () => ({ mutate: vi.fn(), isPending: false }),
  getAttachmentDownloadUrl: () => "#",
}));

vi.mock("@/modules/ma/components/AttachmentUploadActionButton", () => ({
  default: () => <button type="button">attachment-upload</button>,
}));

vi.mock("@/modules/ma/components/FileUploadZone", () => ({
  default: (props: {
    entityType: string;
    embedded?: boolean;
    embeddedLabel?: string;
    showUploadAction?: boolean;
  }) => (
    <div
      data-testid="contracts-upload-zone"
      data-embedded={String(Boolean(props.embedded))}
      data-embedded-label={props.embeddedLabel ?? ""}
      data-entity-type={props.entityType}
      data-show-upload-action={String(props.showUploadAction ?? true)}
    >
      contracts-upload-zone
    </div>
  ),
}));

vi.mock("@/modules/ma/components/negotiation/ContractNegotiationWorkspace", () => ({
  ContractNegotiationWorkspace: () => <div>contract-workspace</div>,
}));

vi.mock("@/modules/docs/components/LegalDocumentsTab", () => ({
  default: () => null,
}));

describe("ContractsTab", () => {
  beforeEach(() => {
    mockContracts = [];
    mockContractSummary = undefined;
  });

  it("keeps the upload zone embedded when no contracts exist", () => {
    render(<ContractsTab txnId="txn-1" canWrite />);

    const uploadZone = screen.getByTestId("contracts-upload-zone");

    expect(screen.queryByText("contract-workspace")).not.toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "attachment-upload" }),
    ).toBeInTheDocument();
    expect(uploadZone).toHaveAttribute("data-entity-type", "CONTRACT");
    expect(uploadZone).toHaveAttribute("data-embedded", "true");
    expect(uploadZone).toHaveAttribute("data-embedded-label", "");
    expect(uploadZone).toHaveAttribute("data-show-upload-action", "false");
  });

  it("shows the negotiation workspace once contracts exist", () => {
    mockContracts = [
      {
        id: "contract-1",
        title: "Stock Purchase Agreement",
        contract_type: "SPA",
        status: "DRAFT",
        counterparty_name: "NX Games",
        current_version: 1,
        seller_signature: "PENDING",
        buyer_signature: "PENDING",
        effective_date: null,
      },
    ];
    mockContractSummary = {
      total: 1,
      pending_signatures: 1,
      fully_executed: 0,
      by_type: { SPA: 1 },
    };

    render(<ContractsTab txnId="txn-1" canWrite />);

    const uploadZone = screen.getByTestId("contracts-upload-zone");

    expect(screen.getByText("contract-workspace")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "attachment-upload" }),
    ).toBeInTheDocument();
    expect(uploadZone).toHaveAttribute("data-entity-type", "CONTRACT");
    expect(uploadZone).toHaveAttribute("data-show-upload-action", "false");
    expect(uploadZone.getAttribute("data-embedded-label")).toMatch(/\S/);
  });
});
