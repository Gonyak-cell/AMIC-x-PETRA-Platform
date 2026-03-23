import { renderWithProviders, screen } from "@/test/test-utils";
import { mockUser } from "@/test/mocks/data";
import ProfilePage from "../ProfilePage";

describe("ProfilePage", () => {
  it("shows M&A pipeline email notices for client users", () => {
    renderWithProviders(<ProfilePage />, {
      authContext: {
        user: {
          ...mockUser,
          role: "CLIENT",
          email: "client.demo@amic.kr",
          display_name: "Client Demo",
        },
      },
    });

    expect(screen.getByText("Pipeline Stage Updates")).toBeInTheDocument();
    expect(screen.getByText("VDR & DD Requests")).toBeInTheDocument();
    expect(screen.getByText("Marketing Materials Ready")).toBeInTheDocument();
    expect(screen.getByText("Weekly Deal Digest")).toBeInTheDocument();
    expect(screen.queryByText("Watchlist Alerts")).not.toBeInTheDocument();
    expect(screen.queryByText("IM Completion")).not.toBeInTheDocument();
  });

  it("keeps the existing platform-wide notices for internal users", () => {
    renderWithProviders(<ProfilePage />, {
      authContext: { user: mockUser },
    });

    expect(screen.getByText("Deal Updates")).toBeInTheDocument();
    expect(screen.getByText("Watchlist Alerts")).toBeInTheDocument();
    expect(screen.getByText("IM Completion")).toBeInTheDocument();
    expect(screen.getByText("Weekly Digest")).toBeInTheDocument();
    expect(screen.queryByText("Pipeline Stage Updates")).not.toBeInTheDocument();
    expect(screen.queryByText("VDR & DD Requests")).not.toBeInTheDocument();
  });
});
