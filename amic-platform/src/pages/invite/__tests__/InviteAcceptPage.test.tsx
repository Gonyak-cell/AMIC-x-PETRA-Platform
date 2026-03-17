import { vi, describe, it, expect, beforeEach } from "vitest";
import {
  renderWithProviders,
  screen,
  waitFor,
  userEvent,
} from "@/test/test-utils";

// Mock the hooks module
const mockUseVerifyInvite = vi.fn();
const mockUseAcceptInvite = vi.fn();
vi.mock("@/hooks/useInvite", () => ({
  useVerifyInvite: (...args: unknown[]) => mockUseVerifyInvite(...args),
  useAcceptInvite: () => mockUseAcceptInvite(),
}));

// Mock navigate
const mockNavigate = vi.fn();
vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual("react-router-dom");
  return { ...actual, useNavigate: () => mockNavigate };
});

import InviteAcceptPage from "../InviteAcceptPage";

describe("InviteAcceptPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Default useAcceptInvite return value
    mockUseAcceptInvite.mockReturnValue({
      mutateAsync: vi.fn(),
      isPending: false,
    });
  });

  it("토큰 없음 → Invalid Link 카드 표시", () => {
    mockUseVerifyInvite.mockReturnValue({
      data: undefined,
      isLoading: false,
      isError: false,
    });

    renderWithProviders(<InviteAcceptPage />, {
      initialEntries: ["/invite/accept"],
    });

    expect(screen.getByText("Invalid Link")).toBeInTheDocument();
  });

  it("isVerifying=true → Spinner 및 Verifying 텍스트 표시", () => {
    mockUseVerifyInvite.mockReturnValue({
      data: undefined,
      isLoading: true,
      isError: false,
    });

    renderWithProviders(<InviteAcceptPage />, {
      initialEntries: ["/invite/accept?token=abc"],
    });

    expect(screen.getByText(/Verifying/i)).toBeInTheDocument();
  });

  it("isVerifyError=true → 연결 오류 카드 표시", () => {
    mockUseVerifyInvite.mockReturnValue({
      data: undefined,
      isLoading: false,
      isError: true,
    });

    renderWithProviders(<InviteAcceptPage />, {
      initialEntries: ["/invite/accept?token=abc"],
    });

    expect(screen.getByText("연결 오류")).toBeInTheDocument();
  });

  it("tokenInfo.valid=false, expired=true → Invitation Expired 안내 표시", () => {
    mockUseVerifyInvite.mockReturnValue({
      data: {
        valid: false,
        expired: true,
        already_used: false,
        email: null,
        display_name: null,
      },
      isLoading: false,
      isError: false,
    });

    renderWithProviders(<InviteAcceptPage />, {
      initialEntries: ["/invite/accept?token=abc"],
    });

    expect(screen.getAllByText(/Expired/i).length).toBeGreaterThan(0);
  });

  it("tokenInfo.valid=true → 비밀번호 폼 및 사용자 이름 표시", () => {
    mockUseVerifyInvite.mockReturnValue({
      data: {
        valid: true,
        email: "test@test.com",
        display_name: "테스트",
        expired: false,
        already_used: false,
      },
      isLoading: false,
      isError: false,
    });

    renderWithProviders(<InviteAcceptPage />, {
      initialEntries: ["/invite/accept?token=abc"],
    });

    expect(
      screen.getByPlaceholderText("At least 8 characters"),
    ).toBeInTheDocument();
    expect(screen.getByText("테스트")).toBeInTheDocument();
  });

  it("비밀번호 불일치 → do not match 메시지 표시", async () => {
    mockUseVerifyInvite.mockReturnValue({
      data: {
        valid: true,
        email: "test@test.com",
        display_name: "테스트",
        expired: false,
        already_used: false,
      },
      isLoading: false,
      isError: false,
    });
    mockUseAcceptInvite.mockReturnValue({
      mutateAsync: vi.fn(),
      isPending: false,
    });

    const user = userEvent.setup();

    renderWithProviders(<InviteAcceptPage />, {
      initialEntries: ["/invite/accept?token=abc"],
    });

    await user.type(
      screen.getByPlaceholderText("At least 8 characters"),
      "password1",
    );
    await user.type(
      screen.getByPlaceholderText("Re-enter your password"),
      "password2",
    );
    await user.click(screen.getByRole("button", { name: /Activate Account/i }));

    await waitFor(() => {
      expect(screen.getByText(/do not match/i)).toBeInTheDocument();
    });
  });

  it("accept 성공 → successfully 메시지 표시", async () => {
    mockUseVerifyInvite.mockReturnValue({
      data: {
        valid: true,
        email: "test@test.com",
        display_name: "테스트",
        expired: false,
        already_used: false,
      },
      isLoading: false,
      isError: false,
    });
    mockUseAcceptInvite.mockReturnValue({
      mutateAsync: vi
        .fn()
        .mockResolvedValue({ message: "ok", email: "test@test.com" }),
      isPending: false,
    });

    const user = userEvent.setup();

    renderWithProviders(<InviteAcceptPage />, {
      initialEntries: ["/invite/accept?token=abc"],
    });

    await user.type(
      screen.getByPlaceholderText("At least 8 characters"),
      "password123",
    );
    await user.type(
      screen.getByPlaceholderText("Re-enter your password"),
      "password123",
    );
    await user.click(screen.getByRole("button", { name: /Activate Account/i }));

    await waitFor(() => {
      expect(screen.getByText(/successfully/i)).toBeInTheDocument();
    });
  });
});
