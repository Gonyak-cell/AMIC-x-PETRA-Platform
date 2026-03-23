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

vi.mock("@/modules/ma/components/FileUploadZone", () => ({
  default: (props: {
    entityType: string;
    embedded?: boolean;
    embeddedLabel?: string;
  }) => (
    <div
      data-testid="ndas-upload-zone"
      data-embedded={String(Boolean(props.embedded))}
      data-embedded-label={props.embeddedLabel ?? ""}
      data-entity-type={props.entityType}
    >
      ndas-upload-zone
    </div>
  ),
}));

vi.mock("@/modules/ma/components/NdaVersionPanel", () => ({
  default: () => <div>nda-version-panel</div>,
}));

describe("NdasTab", () => {
  it("uses the embedded NDA upload zone instead of a generic attachment section", () => {
    render(<NdasTab txnId="txn-1" canWrite />);

    const uploadZone = screen.getByTestId("ndas-upload-zone");

    expect(uploadZone).toHaveAttribute("data-entity-type", "NDA");
    expect(uploadZone).toHaveAttribute("data-embedded", "true");
    expect(uploadZone.getAttribute("data-embedded-label")).toMatch(/\S/);
    expect(screen.queryByText("nda-version-panel")).not.toBeInTheDocument();
  });
});
