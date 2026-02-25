import {
  renderWithProviders,
  screen,
  waitFor,
} from "@/test/test-utils";
import { mockUser } from "@/test/mocks/data";
import DashboardPage from "../DashboardPage";

describe("DashboardPage", () => {
  it("renders welcome message with user name", async () => {
    renderWithProviders(<DashboardPage />, {
      authContext: { user: mockUser },
    });

    expect(
      screen.getByText(`Welcome, ${mockUser.display_name} ${mockUser.title} 님`),
    ).toBeInTheDocument();
  });

  it("renders quick action cards", async () => {
    renderWithProviders(<DashboardPage />);

    expect(screen.getByText("New Transaction")).toBeInTheDocument();
    expect(screen.getByText("New Document")).toBeInTheDocument();
    expect(screen.getByText("Search Company")).toBeInTheDocument();
  });

  it("renders module navigation cards", async () => {
    renderWithProviders(<DashboardPage />);

    expect(screen.getByText("M&A Deals")).toBeInTheDocument();
    expect(screen.getByText("Deal Doc Studio")).toBeInTheDocument();
    expect(screen.getByText("KIIS")).toBeInTheDocument();
  });

  it("shows KPI labels after loading", async () => {
    renderWithProviders(<DashboardPage />);

    await waitFor(() => {
      expect(screen.getByText("Active M&A Deals")).toBeInTheDocument();
    });

    expect(screen.getByText("Watchlist Alerts")).toBeInTheDocument();
  });

  it("shows Module Status section", async () => {
    renderWithProviders(<DashboardPage />);

    expect(screen.getByText("Module Status")).toBeInTheDocument();
  });

  it("shows Modules section header", async () => {
    renderWithProviders(<DashboardPage />);

    expect(screen.getByText("Modules")).toBeInTheDocument();
  });

  it("falls back to 'User' when display_name is missing", () => {
    renderWithProviders(<DashboardPage />, {
      authContext: { user: null },
    });

    expect(screen.getByText("Welcome, User 님")).toBeInTheDocument();
  });
});
