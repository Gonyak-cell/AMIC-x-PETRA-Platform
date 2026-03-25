import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";

import ClientNdaSection from "../ClientNdaSection";

const mockUseNdas = vi.fn();
const mockUseTransaction = vi.fn();

vi.mock("@/modules/ma/hooks/useNdas", () => ({
  useNdas: () => mockUseNdas(),
  useCreateNda: () => ({ mutate: vi.fn(), isPending: false }),
  useUpdateNda: () => ({ mutate: vi.fn(), isPending: false }),
  useDeleteNda: () => ({ mutate: vi.fn(), isPending: false }),
}));

vi.mock("@/modules/ma/hooks/useTransactions", () => ({
  useTransaction: () => mockUseTransaction(),
}));

vi.mock("@/modules/ma/hooks/useAttachmentExtractionFlow", () => ({
  useAttachmentExtractionFlow: () => ({
    activeReview: null,
    closeReview: vi.fn(),
    startExtractionFromUpload: vi.fn(),
  }),
}));

vi.mock("@/modules/ma/components/FileUploadZone", () => ({
  default: () => <div>client-nda-upload-zone</div>,
}));

vi.mock("@/modules/ma/components/extraction/ExtractionReviewModal", () => ({
  default: () => null,
}));

describe("ClientNdaSection", () => {
  beforeEach(() => {
    mockUseNdas.mockReturnValue({ data: [] });
    mockUseTransaction.mockReturnValue({
      data: { client_name: "Acme Client", target_company_name: "Acme Target" },
    });
  });

  it("uses only the upload empty state when there are no client NDAs or files", () => {
    render(<ClientNdaSection txnId="txn-1" canWrite />);

    expect(screen.queryByText("클라이언트 NDA 없음")).not.toBeInTheDocument();
    expect(screen.getByText("client-nda-upload-zone")).toBeInTheDocument();
  });
});
