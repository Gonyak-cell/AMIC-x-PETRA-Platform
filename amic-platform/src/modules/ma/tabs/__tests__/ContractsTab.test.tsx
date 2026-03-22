import { describe, expect, it, vi, beforeEach } from "vitest";
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

vi.mock("@/modules/ma/components/negotiation/ContractNegotiationWorkspace", () => ({
  ContractNegotiationWorkspace: () => <div>계약 협상 워크스페이스</div>,
}));

vi.mock("@/modules/docs/components/LegalDocumentsTab", () => ({
  default: () => null,
}));

describe("ContractsTab", () => {
  beforeEach(() => {
    mockContracts = [];
    mockContractSummary = undefined;
  });

  it("shows a single contract entry section when no contracts exist", () => {
    render(<ContractsTab txnId="txn-1" canWrite />);

    expect(screen.queryByText("계약 협상 워크스페이스")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "법률 문서" })).not.toBeInTheDocument();
    expect(screen.getByText("계약서 관리")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "파일 업로드" })).toBeInTheDocument();
    expect(screen.queryByText("계약서 업로드")).not.toBeInTheDocument();
    expect(
      screen.getByText("SPA, SHA 등 계약서를 바로 업로드하세요."),
    ).toBeInTheDocument();
    expect(screen.queryByText("계약서 없음")).not.toBeInTheDocument();
  });

  it("shows the negotiation workspace and legal-doc action once contracts exist", () => {
    mockContracts = [
      {
        id: "contract-1",
        title: "주식매매계약",
        contract_type: "SPA",
        status: "DRAFT",
        counterparty_name: "NX게임즈",
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

    expect(screen.getByText("계약 협상 워크스페이스")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "법률 문서" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "파일 업로드" })).toBeInTheDocument();
    expect(screen.getByText("계약서 파일")).toBeInTheDocument();
    expect(screen.queryByText("계약서 업로드")).not.toBeInTheDocument();
  });
});
