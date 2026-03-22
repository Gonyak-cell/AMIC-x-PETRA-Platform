import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";

import NdasTab from "../NdasTab";

vi.mock("@/modules/ma/hooks/useNdas", () => ({
  useNdas: () => ({ data: [] }),
  useNdaSummary: () => ({ data: undefined }),
  useCreateNda: () => ({ mutate: vi.fn(), isPending: false }),
  useUpdateNda: () => ({ mutate: vi.fn(), isPending: false }),
  useDeleteNda: () => ({ mutate: vi.fn(), isPending: false }),
}));

vi.mock("@/modules/ma/hooks/useTransactions", () => ({
  useBuyers: () => ({ data: [] }),
}));

vi.mock("@/modules/ma/hooks/useAttachments", () => ({
  useAttachments: () => ({ data: { items: [] } }),
  useUploadAttachment: () => ({ mutate: vi.fn(), isPending: false }),
  useDeleteAttachment: () => ({ mutate: vi.fn(), isPending: false }),
  getAttachmentDownloadUrl: () => "#",
}));

vi.mock("@/modules/ma/components/NdaVersionPanel", () => ({
  default: () => null,
}));

describe("NdasTab", () => {
  it("shows a direct NDA upload area instead of a generic attachment section", () => {
    render(<NdasTab txnId="txn-1" canWrite />);

    expect(screen.queryByText("첨부 파일")).not.toBeInTheDocument();
    expect(screen.queryByText("NDA 없음")).not.toBeInTheDocument();
    expect(screen.getByText("NDA 업로드")).toBeInTheDocument();
    expect(
      screen.getByText("매수 후보와의 NDA 파일을 바로 업로드하세요."),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "파일 업로드" }),
    ).toBeInTheDocument();
  });
});
