import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import EngagementTab from "../EngagementTab";

const mockUseWorkingGroup = vi.fn();
const mockUseAuth = vi.fn();
const addMemberMutate = vi.fn();
const updateMemberMutate = vi.fn();

vi.mock("@/modules/ma/hooks/useTransactions", () => ({
  useEngagements: () => ({ data: [] }),
  useCreateEngagement: () => ({ mutate: vi.fn(), isPending: false }),
  useWorkingGroup: () => mockUseWorkingGroup(),
  useAddMember: () => ({ mutate: addMemberMutate, isPending: false }),
  useUpdateMember: () => ({ mutate: updateMemberMutate, isPending: false }),
}));

vi.mock("@/hooks/useAuth", () => ({
  useAuth: () => mockUseAuth(),
}));

vi.mock("@/modules/ma/hooks/useAttachmentExtractionFlow", () => ({
  useAttachmentExtractionFlow: () => ({
    activeReview: null,
    closeReview: vi.fn(),
    startExtractionFromUpload: vi.fn(),
  }),
}));

vi.mock("@/modules/ma/components/FileUploadZone", () => ({
  default: () => <div>engagement-upload-zone</div>,
}));

vi.mock("@/modules/ma/components/extraction/ExtractionReviewModal", () => ({
  default: () => null,
}));

vi.mock("@/modules/ma/components/engagement/ClientNdaSection", () => ({
  default: () => <div>client-nda-section</div>,
}));

describe("EngagementTab", () => {
  beforeEach(() => {
    mockUseWorkingGroup.mockReturnValue({ data: [] });
    mockUseAuth.mockReturnValue({
      user: {
        id: "user-1",
        email: "manager@amic.kr",
        display_name: "김매니저",
        title: "Manager",
        role: "MANAGER",
        is_active: true,
        created_at: "2026-03-23T00:00:00Z",
      },
    });
    addMemberMutate.mockReset();
    updateMemberMutate.mockReset();
  });

  it("keeps only one persistent create action per section in the empty state", () => {
    render(<EngagementTab txnId="txn-1" canWrite />);

    expect(screen.getAllByText("계약 추가")).toHaveLength(1);
    expect(screen.getAllByText("멤버 추가")).toHaveLength(1);
    expect(
      screen.getByRole("heading", { name: "Working Group List" }),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("heading", { name: "워킹 그룹" }),
    ).not.toBeInTheDocument();
  });

  it("uses only the upload empty state when there are no engagement rows or files", () => {
    render(<EngagementTab txnId="txn-1" canWrite />);

    expect(screen.queryByText("계약 정보 없음")).not.toBeInTheDocument();
    expect(screen.getByText("engagement-upload-zone")).toBeInTheDocument();
  });

  it("hides working group add action for non-manager roles", () => {
    mockUseAuth.mockReturnValue({
      user: {
        id: "user-2",
        email: "analyst@amic.kr",
        display_name: "이분석",
        title: "Analyst",
        role: "ANALYST",
        is_active: true,
        created_at: "2026-03-23T00:00:00Z",
      },
    });

    render(<EngagementTab txnId="txn-1" canWrite />);

    expect(screen.getByText("계약 추가")).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "멤버 추가" }),
    ).not.toBeInTheDocument();
  });

  it("shows an edit action for a member's own row", () => {
    mockUseAuth.mockReturnValue({
      user: {
        id: "user-3",
        email: "wsjo@amic.kr",
        display_name: "조우상",
        title: "Analyst",
        role: "ANALYST",
        is_active: true,
        created_at: "2026-03-23T00:00:00Z",
      },
    });
    mockUseWorkingGroup.mockReturnValue({
      data: [
        {
          id: "member-1",
          transaction_id: "txn-1",
          name: "조우상",
          email: "other@amic.kr",
          organization: "페트라브릿지파트너스",
          role: "LEAD_ADVISOR",
          phone: "02-1234-5678",
          is_active: true,
          created_at: "2026-03-23T00:00:00Z",
          updated_at: "2026-03-23T00:00:00Z",
        },
        {
          id: "member-2",
          transaction_id: "txn-1",
          name: "김양태",
          email: "ytkim@amic.kr",
          organization: "페트라브릿지파트너스",
          role: "LEAD_ADVISOR",
          phone: "02-2345-6789",
          is_active: true,
          created_at: "2026-03-23T00:00:00Z",
          updated_at: "2026-03-23T00:00:00Z",
        },
      ],
    });

    render(<EngagementTab txnId="txn-1" canWrite />);

    expect(
      screen.getByRole("button", { name: "조우상 수정" }),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "김양태 수정" }),
    ).not.toBeInTheDocument();
  });

  it("submits a self-edit with contact fields only", async () => {
    const user = userEvent.setup();
    mockUseAuth.mockReturnValue({
      user: {
        id: "user-3",
        email: "wsjo@amic.kr",
        display_name: "조우상",
        title: "Analyst",
        role: "ANALYST",
        is_active: true,
        created_at: "2026-03-23T00:00:00Z",
      },
    });
    mockUseWorkingGroup.mockReturnValue({
      data: [
        {
          id: "member-1",
          transaction_id: "txn-1",
          name: "조우상",
          email: "other@amic.kr",
          organization: "페트라브릿지파트너스",
          role: "LEAD_ADVISOR",
          phone: "02-1234-5678",
          is_active: true,
          created_at: "2026-03-23T00:00:00Z",
          updated_at: "2026-03-23T00:00:00Z",
        },
      ],
    });

    render(<EngagementTab txnId="txn-1" canWrite />);

    await user.click(screen.getByRole("button", { name: "조우상 수정" }));

    expect(screen.queryByLabelText("이름")).not.toBeInTheDocument();
    expect(screen.queryByLabelText("역할")).not.toBeInTheDocument();

    await user.clear(screen.getByLabelText("소속"));
    await user.type(screen.getByLabelText("소속"), "AMIC");
    await user.clear(screen.getByLabelText("전화"));
    await user.type(screen.getByLabelText("전화"), "010-9999-0000");
    await user.click(screen.getByRole("button", { name: "저장" }));

    expect(updateMemberMutate).toHaveBeenCalledWith(
      {
        memberId: "member-1",
        body: {
          organization: "AMIC",
          phone: "010-9999-0000",
        },
      },
      expect.any(Object),
    );
  });
  it("renders the client nda section in engagement phase", () => {
    render(<EngagementTab txnId="txn-1" canWrite />);

    expect(screen.getByText("client-nda-section")).toBeInTheDocument();
  });
});
