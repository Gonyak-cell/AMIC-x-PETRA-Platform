import { renderWithProviders, screen } from "@/test/test-utils";
import TeamPage from "../TeamPage";

describe("TeamPage", () => {
  it("renders all team member cards", () => {
    renderWithProviders(<TeamPage />);

    expect(screen.getByText("Our Team")).toBeInTheDocument();
    expect(screen.getByText("Team Members")).toBeInTheDocument();
    expect(screen.getByText("김양태")).toBeInTheDocument();
    expect(screen.getByText("임영훈")).toBeInTheDocument();
    expect(screen.getByText("박병준")).toBeInTheDocument();
    expect(screen.getByText("조우상")).toBeInTheDocument();
    expect(screen.getByText("서지원")).toBeInTheDocument();
  });
});
