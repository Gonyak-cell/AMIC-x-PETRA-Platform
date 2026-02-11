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
      screen.getByText(`Welcome, ${mockUser.display_name}`),
    ).toBeInTheDocument();
  });

  it("renders quick action cards", async () => {
    renderWithProviders(<DashboardPage />);

    expect(screen.getByText("New Deal")).toBeInTheDocument();
    expect(screen.getByText("New IM")).toBeInTheDocument();
    expect(screen.getByText("Search Company")).toBeInTheDocument();
    expect(screen.getByText("Watchlist")).toBeInTheDocument();
  });

  it("renders module navigation cards", async () => {
    renderWithProviders(<DashboardPage />);

    expect(screen.getByText("Auto FDD")).toBeInTheDocument();
    expect(screen.getByText("KIIS")).toBeInTheDocument();
    expect(screen.getByText("IM Generator")).toBeInTheDocument();
  });

  it("shows KPI values after loading", async () => {
    renderWithProviders(<DashboardPage />);

    await waitFor(() => {
      expect(screen.getByText("Active FDD Deals")).toBeInTheDocument();
    });

    expect(screen.getByText("Watchlist Alerts")).toBeInTheDocument();
    expect(screen.getByText("IM In Progress")).toBeInTheDocument();
    expect(screen.getByText("Draft Deals")).toBeInTheDocument();
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

    expect(screen.getByText("Welcome, User")).toBeInTheDocument();
  });
});
