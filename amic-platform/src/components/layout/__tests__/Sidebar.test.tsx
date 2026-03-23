import { renderWithProviders, screen } from "@/test/test-utils";
import { Sidebar } from "../Sidebar";
import { mockUser } from "@/test/mocks/data";

describe("Sidebar", () => {
  it("shows dashboard and account navigation for client users on the help page", () => {
    renderWithProviders(<Sidebar />, {
      initialEntries: ["/help"],
      authContext: {
        user: {
          ...mockUser,
          role: "CLIENT",
          email: "client.demo@amic.kr",
          display_name: "Client Demo",
        },
      },
    });

    expect(screen.getByText("Home")).toBeInTheDocument();
    expect(screen.getByText("Calendar")).toBeInTheDocument();
    expect(screen.getByText("Team")).toBeInTheDocument();
    expect(screen.getByText("Settings")).toBeInTheDocument();
    expect(screen.getByText("M&A Deals")).toBeInTheDocument();
    expect(screen.getByText("Pipeline")).toBeInTheDocument();
    expect(screen.getByText("Help")).toBeInTheDocument();
    expect(screen.queryByText("New Transaction")).not.toBeInTheDocument();
    expect(screen.queryByText("Exports")).not.toBeInTheDocument();
  });
});
