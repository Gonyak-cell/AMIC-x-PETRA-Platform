import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";

import EngagementTab from "../EngagementTab";

vi.mock("@/modules/ma/hooks/useTransactions", () => ({
  useEngagements: () => ({ data: [] }),
  useCreateEngagement: () => ({ mutate: vi.fn(), isPending: false }),
  useWorkingGroup: () => ({ data: [] }),
  useAddMember: () => ({ mutate: vi.fn(), isPending: false }),
}));

describe("EngagementTab", () => {
  it("keeps only one persistent create action per section in the empty state", () => {
    render(<EngagementTab txnId="txn-1" canWrite />);

    expect(screen.getAllByText("수임계약 추가")).toHaveLength(1);
    expect(screen.getAllByText("멤버 추가")).toHaveLength(1);
    expect(screen.getByRole("heading", { name: "워킹 그룹" })).toBeInTheDocument();
    expect(screen.queryByText("Working Group")).not.toBeInTheDocument();
  });
});
