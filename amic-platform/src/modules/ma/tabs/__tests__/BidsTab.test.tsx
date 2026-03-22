import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";

import BidsTab from "../BidsTab";

vi.mock("@/modules/ma/hooks/useBids", () => ({
  useBids: () => ({ data: [] }),
  useBidComparison: () => ({ data: [] }),
  useCreateBid: () => ({ mutate: vi.fn(), isPending: false }),
  useUpdateBid: () => ({ mutate: vi.fn(), isPending: false }),
  useDeleteBid: () => ({ mutate: vi.fn(), isPending: false }),
  useImportBidFromAttachment: () => ({
    mutateAsync: vi.fn(),
    isPending: false,
  }),
}));

vi.mock("@/modules/ma/hooks/useTransactions", () => ({
  useBuyers: () => ({ data: [] }),
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

describe("BidsTab", () => {
  it("shows a direct bid upload area with auto-fill assist controls", () => {
    render(<BidsTab txnId="txn-1" canWrite />);

    expect(screen.queryByText("첨부 파일")).not.toBeInTheDocument();
    expect(screen.queryByText("입찰 없음")).not.toBeInTheDocument();
    expect(screen.getByText("입찰 업로드")).toBeInTheDocument();
    expect(screen.getByText("입찰 자료를 바로 업로드하세요.")).toBeInTheDocument();
    expect(screen.getByLabelText("매수후보 우선 지정")).toBeInTheDocument();
    expect(screen.getByLabelText("입찰 유형 우선 지정")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "파일 업로드" })).toBeInTheDocument();
  });
});
