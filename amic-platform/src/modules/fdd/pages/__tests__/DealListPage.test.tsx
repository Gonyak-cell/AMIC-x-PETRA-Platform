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
    expect(screen.getByText("새 딜 생성")).toBeInTheDocument();
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
    expect(screen.getByText("전체 딜")).toBeInTheDocument();
    expect(screen.getByText("진행 중")).toBeInTheDocument();
    expect(screen.getByText("초안")).toBeInTheDocument();
    expect(screen.getByText("보관")).toBeInTheDocument();
  });

  it("opens create modal when clicking new deal button", async () => {
    const user = userEvent.setup();
    renderWithProviders(<DealListPage />);

    await user.click(screen.getByText("새 딜 생성"));

    await waitFor(() => {
      expect(screen.getByLabelText(/딜 이름/i)).toBeInTheDocument();
    });
  });

  it("shows empty state when no deals", async () => {
    server.use(
      http.get("/api/fdd/deals", () => {
        return HttpResponse.json([]);
      }),
    );

    renderWithProviders(<DealListPage />);

    await waitFor(() => {
      expect(screen.getByText("아직 딜이 없습니다")).toBeInTheDocument();
    });

    expect(
      screen.getByText(
        "새 딜을 생성하여 FDD 분석을 시작하세요.",
      ),
    ).toBeInTheDocument();
  });
});
