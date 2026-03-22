import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";

import DDChecklistTab from "../DDChecklistTab";

vi.mock("@/modules/ma/hooks/useDDChecklist", () => ({
  useDDChecklist: () => ({ data: [] }),
  useDDChecklistSummary: () => ({ data: undefined }),
  useCreateDDChecklistItem: () => ({ mutate: vi.fn(), isPending: false }),
  useUpdateDDChecklistItem: () => ({ mutate: vi.fn(), isPending: false }),
  useDeleteDDChecklistItem: () => ({ mutate: vi.fn(), isPending: false }),
}));

vi.mock("@/modules/ma/components/DDReportSection", () => ({
  default: () => null,
}));

describe("DDChecklistTab", () => {
  it("shows the checklist workspace without a separate upload zone", () => {
    render(<DDChecklistTab txnId="txn-1" canWrite />);

    expect(screen.getByText("DD 체크리스트")).toBeInTheDocument();
    expect(screen.getByText("체크리스트 없음")).toBeInTheDocument();
    expect(screen.queryByText("DD 업로드")).not.toBeInTheDocument();
    expect(screen.queryByText("파일 업로드")).not.toBeInTheDocument();
  });
});
