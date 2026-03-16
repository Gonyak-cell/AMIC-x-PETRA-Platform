import { renderWithProviders, screen, waitFor } from "@/test/test-utils";
import DashboardCalendarWidget from "../DashboardCalendarWidget";

describe("DashboardCalendarWidget", () => {
  it("renders current month header", async () => {
    renderWithProviders(<DashboardCalendarWidget />);

    const now = new Date();
    const monthLabel = now.toLocaleDateString("ko-KR", {
      year: "numeric",
      month: "long",
    });

    await waitFor(() => {
      expect(screen.getByText(monthLabel)).toBeInTheDocument();
    });
  });

  it("renders Calendar title", async () => {
    renderWithProviders(<DashboardCalendarWidget />);
    // title is always shown (even in loading skeleton)
    expect(screen.getByText("Calendar")).toBeInTheDocument();
  });

  it("renders day labels after loading", async () => {
    renderWithProviders(<DashboardCalendarWidget />);

    await waitFor(() => {
      expect(screen.getByText("일")).toBeInTheDocument();
    });
    expect(screen.getByText("토")).toBeInTheDocument();
  });

  it("renders upcoming section header", async () => {
    renderWithProviders(<DashboardCalendarWidget />);

    await waitFor(() => {
      expect(screen.getByText("다가오는 일정")).toBeInTheDocument();
    });
  });

  it("renders 전체 보기 button after loading", async () => {
    renderWithProviders(<DashboardCalendarWidget />);

    await waitFor(() => {
      expect(screen.getByText("전체 보기")).toBeInTheDocument();
    });
  });
});
