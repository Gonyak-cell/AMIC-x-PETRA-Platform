import { renderWithProviders, screen, waitFor } from "@/test/test-utils";
import { fireEvent } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { server } from "@/test/mocks/server";
import { mockUser } from "@/test/mocks/data";
import MyProjectsSection from "../MyProjectsSection";

const EMAIL = mockUser.email; // jwsuh@amic.kr
const mockClientUser = {
  ...mockUser,
  email: "client.demo@amic.kr",
  display_name: "Client Demo",
  role: "CLIENT" as const,
};

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

/** 서버 assigned_to_me=true 응답 시뮬레이션 — 담당 거래만 포함 */
const mockItems = [
  makeTxn("t1", "Alpha", "ACTIVE", "MARKETING", EMAIL, null, now),
  makeTxn("t2", "Beta", "COMPLETED", "CLOSING", EMAIL, null, now),
  makeTxn("t3", "Gamma", "ACTIVE", "BIDDING", "other@amic.kr", EMAIL, ago1h),
  makeTxn("t4", "Delta", "ON_HOLD", "PREPARATION", EMAIL, EMAIL, ago2h),
  makeTxn("t5", "Epsilon", "TERMINATED", "CLOSING", EMAIL, null, now),
];
const clientItems = [
  makeTxn(
    "client-1",
    "Project Next",
    "ACTIVE",
    "MARKETING",
    "lead@amic.kr",
    null,
    now,
  ),
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

    expect(screen.queryByText("Beta")).not.toBeInTheDocument();
    expect(screen.queryByText("Epsilon")).not.toBeInTheDocument();
  });

  it("shows backend-assigned client projects without assigned_to_me", async () => {
    server.use(
      http.get("*/api/ma/transactions", ({ request }) => {
        const url = new URL(request.url);

        expect(url.searchParams.get("assigned_to_me")).toBeNull();
        expect(url.searchParams.get("limit")).toBe("100");

        return HttpResponse.json({
          items: clientItems,
          total: clientItems.length,
          limit: 100,
          offset: 0,
        });
      }),
    );

    renderWithProviders(<MyProjectsSection />, {
      authContext: { user: mockClientUser },
    });

    await waitFor(() => {
      expect(screen.getByText("Project Next")).toBeInTheDocument();
    });

    expect(screen.getByText("Client")).toBeInTheDocument();
  });

  it("navigates between projects with peek carousel", async () => {
    useMockTransactions();
    renderWithProviders(<MyProjectsSection />, {
      authContext: { user: mockUser },
    });

    await waitFor(() => {
      expect(screen.getByText("Alpha")).toBeInTheDocument();
    });

    // Counter shows 1 / 3
    expect(screen.getByText("1 / 3")).toBeInTheDocument();

    // All cards are rendered (peek style — prev/next visible as edges)
    expect(screen.getByText("Gamma")).toBeInTheDocument();
    expect(screen.getByText("Delta")).toBeInTheDocument();

    // Prev button disabled on first item
    expect(screen.getByLabelText("Previous project")).toBeDisabled();

    // Click next → Gamma
    fireEvent.click(screen.getByLabelText("Next project"));
    expect(screen.getByText("2 / 3")).toBeInTheDocument();

    // Now prev is enabled
    expect(screen.getByLabelText("Previous project")).not.toBeDisabled();

    // Click next → Delta (last)
    fireEvent.click(screen.getByLabelText("Next project"));
    expect(screen.getByText("3 / 3")).toBeInTheDocument();

    // Next button disabled on last item
    expect(screen.getByLabelText("Next project")).toBeDisabled();

    // Click prev → back to Gamma
    fireEvent.click(screen.getByLabelText("Previous project"));
    expect(screen.getByText("2 / 3")).toBeInTheDocument();
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

  it("hides nav buttons when only one project", async () => {
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
