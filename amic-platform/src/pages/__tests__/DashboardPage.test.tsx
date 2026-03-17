import { renderWithProviders, screen, waitFor } from "@/test/test-utils";
import { mockUser } from "@/test/mocks/data";
import DashboardPage from "../DashboardPage";

describe("DashboardPage", () => {
  it("renders welcome message with user name", async () => {
    renderWithProviders(<DashboardPage />, {
      authContext: { user: mockUser },
    });

    expect(
      screen.getByText(
        `Welcome, ${mockUser.display_name} ${mockUser.title} 님`,
      ),
    ).toBeInTheDocument();
  });

  it("does NOT render quick action cards (moved to DesktopHeader)", async () => {
    renderWithProviders(<DashboardPage />);

    // Quick Actions는 DesktopHeader로 이동됨
    expect(screen.queryByText("New Transaction")).not.toBeInTheDocument();
    expect(screen.queryByText("New Document")).not.toBeInTheDocument();
  });

  it("renders module navigation cards", async () => {
    renderWithProviders(<DashboardPage />);

    expect(screen.getByText("M&A Deals")).toBeInTheDocument();
    expect(screen.getByText("Deal Doc Studio")).toBeInTheDocument();
    expect(screen.getByText("KIIS")).toBeInTheDocument();
  });

  it("shows MY PROJECTS section", async () => {
    renderWithProviders(<DashboardPage />);

    expect(screen.getByText("MY PROJECTS")).toBeInTheDocument();
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

  it("renders right rail with calendar widget only", async () => {
    renderWithProviders(<DashboardPage />);

    await waitFor(() => {
      expect(screen.getByText("Calendar")).toBeInTheDocument();
    });
  });

  it("does NOT render removed sections (Module Status, Project Status)", async () => {
    renderWithProviders(<DashboardPage />);

    // Module Status was replaced by MY PROJECTS
    expect(screen.queryByText("Module Status")).not.toBeInTheDocument();
    // Project Status widget was removed from right rail
    expect(screen.queryByText("Project Status")).not.toBeInTheDocument();
  });
});
