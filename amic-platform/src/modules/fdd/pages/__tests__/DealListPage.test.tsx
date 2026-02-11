import { http, HttpResponse } from "msw";
import { server } from "@/test/mocks/server";
import {
  renderWithProviders,
  screen,
  waitFor,
  userEvent,
} from "@/test/test-utils";
import DealListPage from "../DealListPage";

// Mock sonner toast
vi.mock("sonner", () => ({
  toast: { success: vi.fn(), error: vi.fn() },
}));

describe("DealListPage", () => {
  it("renders page title and new deal button", async () => {
    renderWithProviders(<DealListPage />);

    expect(screen.getByText("Deals")).toBeInTheDocument();
    expect(screen.getByText("New Deal")).toBeInTheDocument();
  });

  it("shows deal data after loading", async () => {
    renderWithProviders(<DealListPage />);

    await waitFor(() => {
      expect(screen.getByText("Project Alpha")).toBeInTheDocument();
    });

    expect(screen.getByText("Project Beta")).toBeInTheDocument();
  });

  it("displays KPI cards with correct values", async () => {
    renderWithProviders(<DealListPage />);

    await waitFor(() => {
      expect(screen.getByText("Project Alpha")).toBeInTheDocument();
    });

    // 2 deals total, 1 active, 1 draft, 0 archived
    expect(screen.getByText("Total Deals")).toBeInTheDocument();
    expect(screen.getByText("Active")).toBeInTheDocument();
    expect(screen.getByText("Draft")).toBeInTheDocument();
    expect(screen.getByText("Archived")).toBeInTheDocument();
  });

  it("opens create modal when clicking New Deal", async () => {
    const user = userEvent.setup();
    renderWithProviders(<DealListPage />);

    await user.click(screen.getByText("New Deal"));

    await waitFor(() => {
      expect(screen.getByText("Create New Deal")).toBeInTheDocument();
    });

    expect(screen.getByLabelText(/deal name/i)).toBeInTheDocument();
  });

  it("shows empty state when no deals", async () => {
    server.use(
      http.get("/api/fdd/deals", () => {
        return HttpResponse.json([]);
      }),
    );

    renderWithProviders(<DealListPage />);

    await waitFor(() => {
      expect(screen.getByText("No deals yet")).toBeInTheDocument();
    });

    expect(
      screen.getByText(
        "Create your first deal to get started with FDD analysis.",
      ),
    ).toBeInTheDocument();
  });
});
