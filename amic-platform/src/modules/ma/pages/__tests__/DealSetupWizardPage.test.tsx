import { fireEvent } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import {
  renderWithProviders,
  screen,
  userEvent,
  waitFor,
} from "@/test/test-utils";
import { mockUser } from "@/test/mocks/data";
import DealSetupWizardPage from "../DealSetupWizardPage";

const { mutateMock, navigateMock } = vi.hoisted(() => ({
  mutateMock: vi.fn(),
  navigateMock: vi.fn(),
}));

vi.mock("@/modules/ma/hooks/useTransactions", () => ({
  useCreateTransaction: () => ({
    mutate: mutateMock,
    isPending: false,
  }),
}));

vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual<typeof import("react-router-dom")>(
    "react-router-dom",
  );
  return {
    ...actual,
    useNavigate: () => navigateMock,
  };
});

describe("DealSetupWizardPage", () => {
  beforeEach(() => {
    mutateMock.mockReset();
    navigateMock.mockReset();
  });

  it("keeps project typing responsive and submits a normalized payload", async () => {
    const user = userEvent.setup();
    const { container } = renderWithProviders(<DealSetupWizardPage />);

    const projectInput = screen.getByPlaceholderText(/Edward/i);
    const emailInput = screen.getByPlaceholderText("advisor@company.com");

    await waitFor(() => {
      expect(emailInput).toHaveValue(mockUser.email);
    });

    fireEvent.compositionStart(projectInput);
    fireEvent.change(projectInput, { target: { value: "한" } });
    expect(projectInput).toHaveValue("한");
    fireEvent.compositionEnd(projectInput);

    await user.clear(projectInput);
    await user.type(projectInput, "tempus-01");
    expect(projectInput).toHaveValue("Tempus-01");

    const textboxes = screen.getAllByRole("textbox");
    await user.type(textboxes[1], "Target Co");
    await user.type(textboxes[2], "Client Co");

    const submitButton = container.querySelector(
      'form#create-txn button[type="submit"]',
    );
    expect(submitButton).not.toBeNull();

    await user.click(submitButton!);

    expect(mutateMock).toHaveBeenCalledWith(
      expect.objectContaining({
        name: "Project Tempus-01",
        target_company_name: "Target Co",
        client_name: "Client Co",
        lead_advisor_email: mockUser.email,
      }),
      expect.any(Object),
    );
  });

  it("submits Korean company and client names without mangling", async () => {
    const user = userEvent.setup();
    const { container } = renderWithProviders(<DealSetupWizardPage />);

    const projectInput = screen.getByPlaceholderText(/Edward/i);
    const emailInput = screen.getByPlaceholderText("advisor@company.com");

    await waitFor(() => {
      expect(emailInput).toHaveValue(mockUser.email);
    });

    await user.type(projectInput, "next");

    const textboxes = screen.getAllByRole("textbox");
    await user.type(textboxes[1], "NX게임즈");
    await user.type(textboxes[2], "최일곤");

    const submitButton = container.querySelector(
      'form#create-txn button[type="submit"]',
    );
    expect(submitButton).not.toBeNull();

    await user.click(submitButton!);

    expect(mutateMock).toHaveBeenCalledWith(
      expect.objectContaining({
        name: "Project Next",
        target_company_name: "NX게임즈",
        client_name: "최일곤",
        lead_advisor_email: mockUser.email,
      }),
      expect.any(Object),
    );
  });

  it("blocks garbled company and client names before submit", async () => {
    const user = userEvent.setup();
    const { container } = renderWithProviders(<DealSetupWizardPage />);

    const projectInput = screen.getByPlaceholderText(/Edward/i);
    const emailInput = screen.getByPlaceholderText("advisor@company.com");

    await waitFor(() => {
      expect(emailInput).toHaveValue(mockUser.email);
    });

    await user.type(projectInput, "next");

    const textboxes = screen.getAllByRole("textbox");
    await user.type(textboxes[1], "NX3???");
    await user.type(textboxes[2], "???");

    const submitButton = container.querySelector(
      'form#create-txn button[type="submit"]',
    );
    expect(submitButton).not.toBeNull();

    expect(
      screen.getAllByText(
        "한글 입력이 깨진 것으로 보입니다. 입력기 상태를 확인한 뒤 다시 입력해 주세요.",
      ),
    ).toHaveLength(2);
    expect(submitButton).toBeDisabled();

    await user.click(submitButton!);

    expect(mutateMock).not.toHaveBeenCalled();
  });

  it("navigates to the guided company-info setup after create success", async () => {
    const user = userEvent.setup();
    mutateMock.mockImplementation((_body, options) => {
      options?.onSuccess?.({ id: "txn-guided" });
    });

    const { container } = renderWithProviders(<DealSetupWizardPage />);

    const projectInput = screen.getByPlaceholderText(/Edward/i);
    const emailInput = screen.getByPlaceholderText("advisor@company.com");

    await waitFor(() => {
      expect(emailInput).toHaveValue(mockUser.email);
    });

    await user.type(projectInput, "guided");

    const textboxes = screen.getAllByRole("textbox");
    await user.type(textboxes[1], "Target Co");
    await user.type(textboxes[2], "Client Co");

    const submitButton = container.querySelector(
      'form#create-txn button[type="submit"]',
    );
    expect(submitButton).not.toBeNull();

    await user.click(submitButton!);

    await waitFor(() => {
      expect(navigateMock).toHaveBeenCalledWith(
        "/ma/transactions/txn-guided?setup=company-info",
      );
    });
  });
});
