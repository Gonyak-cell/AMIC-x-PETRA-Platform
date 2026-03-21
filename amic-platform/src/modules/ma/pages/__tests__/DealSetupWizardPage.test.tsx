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

const { mutateMock } = vi.hoisted(() => ({
  mutateMock: vi.fn(),
}));

vi.mock("@/modules/ma/hooks/useTransactions", () => ({
  useCreateTransaction: () => ({
    mutate: mutateMock,
    isPending: false,
  }),
}));

describe("DealSetupWizardPage", () => {
  beforeEach(() => {
    mutateMock.mockReset();
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
});
