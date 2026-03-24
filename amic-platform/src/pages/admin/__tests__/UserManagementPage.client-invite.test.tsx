import { vi, describe, it, expect, beforeEach } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { AuthContext } from "@/components/auth/AuthContext";
import {
  createTestQueryClient,
  createMockAuthContext,
} from "@/test/test-utils";
import { mockUser } from "@/test/mocks/data";

// ── Mock: useUsers ────────────────────────────────────────────
const mockUsers = vi.fn();
const mockCreateUser = vi.fn();
const mockUpdateUser = vi.fn();
const mockDeleteUser = vi.fn();
vi.mock("@/hooks/useUsers", () => ({
  useUsers: () => mockUsers(),
  useCreateUser: () => mockCreateUser(),
  useUpdateUser: () => mockUpdateUser(),
  useDeleteUser: () => mockDeleteUser(),
}));

// ── Mock: useClientDeals ──────────────────────────────────────
vi.mock("@/hooks/useClientDeals", () => ({
  useClientDeals: () => ({ data: [], isLoading: false }),
  useAdminAssignDeal: () => ({ mutateAsync: vi.fn() }),
  useAdminUnassignDeal: () => ({ mutateAsync: vi.fn() }),
}));

// ── Mock: useTransactions / useMaStats ────────────────────────
const mockTransactions = vi.fn();
const mockMaStats = vi.fn();
vi.mock("@/modules/ma/hooks/useTransactions", () => ({
  useTransactions: () => mockTransactions(),
  useMaStats: () => mockMaStats(),
}));

// ── Mock: useCreateInvite ─────────────────────────────────────
const mockCreateInviteMutateAsync = vi.fn();
vi.mock("@/hooks/useInvite", () => ({
  useCreateInvite: () => ({
    mutateAsync: mockCreateInviteMutateAsync,
    isPending: false,
  }),
}));

// ── Mock: maApi ───────────────────────────────────────────────
vi.mock("@/api/maClient", () => ({
  maApi: {
    post: vi.fn(),
    get: vi.fn(),
    delete: vi.fn(),
  },
}));

// ── window.alert spy ──────────────────────────────────────────
const alertSpy = vi.spyOn(window, "alert").mockImplementation(() => {});

// ── Import AFTER mocks ────────────────────────────────────────
import { maApi } from "@/api/maClient";
import UserManagementPage from "../UserManagementPage";

// ── Render helper ─────────────────────────────────────────────
function renderPage() {
  const queryClient = createTestQueryClient();
  const auth = createMockAuthContext({ user: { ...mockUser, role: "ADMIN" } });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <AuthContext.Provider value={auth}>
          <UserManagementPage />
        </AuthContext.Provider>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

// ── Default transaction list ──────────────────────────────────
const defaultTransactions = {
  items: [
    {
      id: "txn-1",
      name: "거래A",
      code_name: "TX-A",
      phase: "ENGAGEMENT",
      status: "ACTIVE",
      side: "SELL",
      estimated_value: null,
      estimated_value_currency: "KRW",
      lead_advisor_email: "a@b.com",
      created_at: "2026-01-01",
    },
    {
      id: "txn-2",
      name: "거래B",
      code_name: "TX-B",
      phase: "ENGAGEMENT",
      status: "ACTIVE",
      side: "SELL",
      estimated_value: null,
      estimated_value_currency: "KRW",
      lead_advisor_email: "a@b.com",
      created_at: "2026-01-01",
    },
  ],
  total: 2,
};

const defaultInviteResult = {
  user_id: "new-user-id",
  email: "client@test.com",
  display_name: "Client",
  is_new_user: true,
  assigned_deal_count: 1,
  invite_sent: true,
  invite_error: null,
};

// ── Setup ─────────────────────────────────────────────────────
beforeEach(() => {
  vi.clearAllMocks();
  // Re-apply alert mock implementation after clearAllMocks resets it
  alertSpy.mockImplementation(() => {});

  mockUsers.mockReturnValue({ data: [mockUser], isLoading: false });
  mockCreateUser.mockReturnValue({ mutate: vi.fn(), isPending: false });
  mockUpdateUser.mockReturnValue({ mutate: vi.fn(), isPending: false });
  mockDeleteUser.mockReturnValue({ mutate: vi.fn(), isPending: false });
  mockTransactions.mockReturnValue({
    data: defaultTransactions,
    isLoading: false,
  });
  mockMaStats.mockReturnValue({ data: null, isLoading: false });
  mockCreateInviteMutateAsync.mockResolvedValue(defaultInviteResult);
  (maApi.post as ReturnType<typeof vi.fn>).mockResolvedValue({
    data: { id: "dc-1" },
  });
});

// ── Helper: open create modal and switch to CLIENT role ───────
async function openClientCreateModal(user: ReturnType<typeof userEvent.setup>) {
  // Click "Create User" button
  const createBtn = screen.getByRole("button", { name: /create user/i });
  await user.click(createBtn);

  // Wait for modal to appear
  await waitFor(() => {
    expect(screen.getByText("Create New User")).toBeInTheDocument();
  });

  // Change role to CLIENT
  const roleSelect = screen.getByLabelText("Role");
  await user.selectOptions(roleSelect, "CLIENT");

  // Wait for CLIENT-specific fields to appear
  await waitFor(() => {
    expect(screen.getByLabelText(/거래 배정/i)).toBeInTheDocument();
  });
}

// ── Helper: fill email + display_name ────────────────────────
async function fillBasicClientFields(
  email = "client@test.com",
  displayName = "Test Client",
) {
  const emailInput = screen.getByLabelText("Email");
  fireEvent.change(emailInput, { target: { value: email } });

  const nameInput = screen.getByLabelText("Display Name");
  fireEvent.change(nameInput, { target: { value: displayName } });
}

// ── Helper: select and add a transaction ─────────────────────
async function addTransaction(
  user: ReturnType<typeof userEvent.setup>,
  txnId: string,
) {
  const dealSelect = screen.getByLabelText(/거래 배정/i);
  // select by value (txn id) to avoid label text matching issues
  await user.selectOptions(dealSelect, txnId);

  // Click the "추가" button
  const addBtn = screen.getByRole("button", { name: /추가/i });
  await user.click(addBtn);
}

// ── Tests ─────────────────────────────────────────────────────

describe("UserManagementPage — CLIENT 초대 플로우", () => {
  it("Test 1: 거래 0건 선택 시 alert 표시, createInvite 미호출", async () => {
    const user = userEvent.setup();
    renderPage();

    await openClientCreateModal(user);
    await fillBasicClientFields();

    // Submit WITHOUT selecting any transaction
    const submitBtn = screen.getByRole("button", { name: /초대 발송/i });
    await user.click(submitBtn);

    await waitFor(() => {
      expect(alertSpy).toHaveBeenCalledWith(expect.stringContaining("거래"));
    });

    expect(mockCreateInviteMutateAsync).not.toHaveBeenCalled();
  });

  it("Test 2: 거래 배정 성공 + invite 성공 → createInvite 호출됨", async () => {
    const user = userEvent.setup();
    renderPage();

    await openClientCreateModal(user);
    await fillBasicClientFields();

    // Select transaction by txn-1 id and add it
    await addTransaction(user, "txn-1");

    // Wait for the selected transaction chip (has remove button with aria-label)
    await waitFor(() => {
      expect(
        screen.getByRole("button", { name: /거래A 제거/i }),
      ).toBeInTheDocument();
    });

    // Submit
    const submitBtn = screen.getByRole("button", { name: /초대 발송/i });
    await user.click(submitBtn);

    await waitFor(() => {
      expect(maApi.post).toHaveBeenCalledWith(
        "/transactions/txn-1/clients",
        expect.objectContaining({ email: "client@test.com" }),
      );
    });

    await waitFor(() => {
      expect(mockCreateInviteMutateAsync).toHaveBeenCalled();
    });
  });

  it("Test 3: invite 예외 시 거래 배정 롤백 호출", async () => {
    mockCreateInviteMutateAsync.mockRejectedValueOnce(new Error("fail"));
    (maApi.get as ReturnType<typeof vi.fn>).mockResolvedValue({
      data: [{ id: "dc-1", email: "client@test.com" }],
    });

    const user = userEvent.setup();
    renderPage();

    await openClientCreateModal(user);
    await fillBasicClientFields();
    await addTransaction(user, "txn-1");

    await waitFor(() => {
      expect(
        screen.getByRole("button", { name: /거래A 제거/i }),
      ).toBeInTheDocument();
    });

    const submitBtn = screen.getByRole("button", { name: /초대 발송/i });
    await user.click(submitBtn);

    // maApi.get called for rollback (fetch clients list)
    await waitFor(() => {
      expect(maApi.get).toHaveBeenCalledWith("/transactions/txn-1/clients");
    });

    // maApi.delete called for rollback
    await waitFor(() => {
      expect(maApi.delete).toHaveBeenCalledWith(
        "/transactions/txn-1/clients/dc-1",
      );
    });

    // Alert message should contain "롤백"
    await waitFor(() => {
      expect(alertSpy).toHaveBeenCalledWith(expect.stringContaining("롤백"));
    });
  });

  it(
    "Test 4: invite_sent=false + 이미 활성화된 계정 → '활성화' 포함 문구, '재발송' 미포함",
    async () => {
      mockCreateInviteMutateAsync.mockResolvedValueOnce({
        ...defaultInviteResult,
        invite_sent: false,
        invite_error: "이미 활성화된 CLIENT입니다",
      });

      const user = userEvent.setup();
      renderPage();

      await openClientCreateModal(user);
      await fillBasicClientFields();

      // Select txn-1 and click 추가 — same as Test 2/3
      const dealSelect = screen.getByLabelText(/거래 배정/i);
      await user.selectOptions(dealSelect, "txn-1");

      const addBtn = screen.getByRole("button", { name: /추가/i });
      await user.click(addBtn);

      // Wait for the chip/list item showing selected transaction (has X/remove button)
      await waitFor(() => {
        expect(
          screen.getByRole("button", { name: /거래A 제거/i }),
        ).toBeInTheDocument();
      });

      const submitBtn = screen.getByRole("button", { name: /초대 발송/i });
      await user.click(submitBtn);

      await waitFor(() => {
        expect(alertSpy).toHaveBeenCalled();
      });

      // Find the alert call that contains "활성화" among all alert calls
      const allAlertMessages = alertSpy.mock.calls.map((c) => c[0] as string);
      const activationAlert = allAlertMessages.find((m) => m.includes("활성화"));
      expect(activationAlert).toBeDefined();
      expect(activationAlert).not.toContain("재발송");
    },
    10000,
  );
});
