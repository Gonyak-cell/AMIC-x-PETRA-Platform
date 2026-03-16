import { renderWithProviders, screen, waitFor } from "@/test/test-utils";
import { fireEvent } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { server } from "@/test/mocks/server";
import { mockUser } from "@/test/mocks/data";
import MyProjectsSection from "../MyProjectsSection";

const EMAIL = mockUser.email; // jwsuh@amic.kr

function makeTxn(
  id: string,
  codeName: string,
  status: string,
  phase: string,
  leadEmail: string,
  captainEmail: string | null,
  updatedAt: string,
) {
  return {
    id,
    name: codeName,
    code_name: codeName,
    target_company_name: `${codeName} Corp`,
    status,
    phase,
    deal_type: "SE",
    side: "SELL",
    lead_advisor_email: leadEmail,
    deal_captain_email: captainEmail,
    target_close_date: "2026-06-30T00:00:00Z",
    created_at: "2026-01-01T00:00:00Z",
    updated_at: updatedAt,
  };
}

const now = new Date().toISOString();
const ago1h = new Date(Date.now() - 3600000).toISOString();
const ago2h = new Date(Date.now() - 7200000).toISOString();
const ago3h = new Date(Date.now() - 10800000).toISOString();

/** 서버 assigned_to_me=true 응답 시뮬레이션 — 담당 거래만 포함 (Zeta 미포함) */
const mockItems = [
  makeTxn("t1", "Alpha", "ACTIVE", "MARKETING", EMAIL, null, now),
  makeTxn("t2", "Beta", "COMPLETED", "CLOSING", EMAIL, null, now),
  makeTxn("t3", "Gamma", "ACTIVE", "BIDDING", "other@amic.kr", EMAIL, ago1h),
  makeTxn("t4", "Delta", "ON_HOLD", "PREPARATION", EMAIL, EMAIL, ago2h),
  makeTxn("t5", "Epsilon", "TERMINATED", "CLOSING", EMAIL, null, now),
];

function useMockTransactions() {
  server.use(
    http.get("*/api/ma/transactions", () =>
      HttpResponse.json({
        items: mockItems,
        total: mockItems.length,
        limit: 50,
        offset: 0,
      }),
    ),
  );
}

describe("MyProjectsSection", () => {
  it("excludes COMPLETED/TERMINATED from server-filtered results", async () => {
    useMockTransactions();
    renderWithProviders(<MyProjectsSection />, {
      authContext: { user: mockUser },
    });

    await waitFor(() => {
      expect(screen.getByText("Alpha")).toBeInTheDocument();
    });

    // Server returns only assigned transactions (assigned_to_me=true)
    // Frontend further excludes COMPLETED (Beta) and TERMINATED (Epsilon)
    expect(screen.queryByText("Beta")).not.toBeInTheDocument();
    expect(screen.queryByText("Epsilon")).not.toBeInTheDocument();
  });

  it("wraps around when navigating past first/last project", async () => {
    useMockTransactions();
    renderWithProviders(<MyProjectsSection />, {
      authContext: { user: mockUser },
    });

    await waitFor(() => {
      expect(screen.getByText("Alpha")).toBeInTheDocument();
    });

    // Counter shows 1 / 3 (Alpha, Gamma, Delta)
    expect(screen.getByText("1 / 3")).toBeInTheDocument();

    // Click prev on first item → wraps to last (Delta)
    fireEvent.click(screen.getByLabelText("Previous project"));
    expect(screen.getByText("3 / 3")).toBeInTheDocument();
    expect(screen.getByText("Delta")).toBeInTheDocument();

    // Click next on last item → wraps to first (Alpha)
    fireEvent.click(screen.getByLabelText("Next project"));
    expect(screen.getByText("1 / 3")).toBeInTheDocument();
    expect(screen.getByText("Alpha")).toBeInTheDocument();

    // Click next → goes to second (Gamma)
    fireEvent.click(screen.getByLabelText("Next project"));
    expect(screen.getByText("2 / 3")).toBeInTheDocument();
    expect(screen.getByText("Gamma")).toBeInTheDocument();
  });

  it("shows empty state when no assigned projects", async () => {
    server.use(
      http.get("*/api/ma/transactions", () =>
        HttpResponse.json({ items: [], total: 0, limit: 50, offset: 0 }),
      ),
    );

    renderWithProviders(<MyProjectsSection />, {
      authContext: { user: mockUser },
    });

    await waitFor(() => {
      expect(
        screen.getByText("현재 담당 중인 프로젝트가 없습니다"),
      ).toBeInTheDocument();
    });
  });

  it("shows empty state when user is null", async () => {
    useMockTransactions();
    renderWithProviders(<MyProjectsSection />, {
      authContext: { user: null },
    });

    await waitFor(() => {
      expect(
        screen.getByText("현재 담당 중인 프로젝트가 없습니다"),
      ).toBeInTheDocument();
    });
  });

  it("shows error state on API failure", async () => {
    server.use(http.get("*/api/ma/transactions", () => HttpResponse.error()));

    renderWithProviders(<MyProjectsSection />, {
      authContext: { user: mockUser },
    });

    await waitFor(() => {
      expect(
        screen.getByText("프로젝트 정보를 불러올 수 없습니다"),
      ).toBeInTheDocument();
    });
  });

  it("disables both nav buttons when only one project", async () => {
    server.use(
      http.get("*/api/ma/transactions", () =>
        HttpResponse.json({
          items: [
            makeTxn("t1", "Solo", "ACTIVE", "MARKETING", EMAIL, null, now),
          ],
          total: 1,
          limit: 50,
          offset: 0,
        }),
      ),
    );

    renderWithProviders(<MyProjectsSection />, {
      authContext: { user: mockUser },
    });

    await waitFor(() => {
      expect(screen.getByText("Solo")).toBeInTheDocument();
    });

    // With 1 item, nav buttons should not render (no "1 / 1")
    expect(screen.queryByText("1 / 1")).not.toBeInTheDocument();
  });

  it("shows correct My Role in summary panel", async () => {
    useMockTransactions();
    renderWithProviders(<MyProjectsSection />, {
      authContext: { user: mockUser },
    });

    // First project (Alpha): lead only
    await waitFor(() => {
      expect(screen.getByText("Lead Advisor")).toBeInTheDocument();
    });

    // Navigate to Gamma (captain only)
    fireEvent.click(screen.getByLabelText("Next project"));
    await waitFor(() => {
      expect(screen.getByText("Deal Captain")).toBeInTheDocument();
    });

    // Navigate to Delta (both lead and captain)
    fireEvent.click(screen.getByLabelText("Next project"));
    await waitFor(() => {
      expect(
        screen.getByText("Lead Advisor / Deal Captain"),
      ).toBeInTheDocument();
    });
  });
});
