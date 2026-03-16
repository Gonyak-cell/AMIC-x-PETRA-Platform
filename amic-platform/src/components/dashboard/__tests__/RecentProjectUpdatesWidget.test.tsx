import { renderWithProviders, screen, waitFor } from "@/test/test-utils";
import { http, HttpResponse } from "msw";
import { server } from "@/test/mocks/server";
import RecentProjectUpdatesWidget from "../RecentProjectUpdatesWidget";

const now = new Date().toISOString();

function makeTxn(
  id: string,
  name: string,
  status: string,
  phase: string,
  updatedAt: string,
) {
  return {
    id,
    name,
    code_name: name,
    target_company_name: name,
    status,
    phase,
    deal_type: "SELL_SIDE",
    created_at: "2026-01-01T00:00:00Z",
    updated_at: updatedAt,
  };
}

const mockItems = [
  makeTxn("t1", "Alpha", "ACTIVE", "MARKETING", now),
  makeTxn("t2", "Beta", "COMPLETED", "CLOSING", now),
  makeTxn(
    "t3",
    "Gamma",
    "ON_HOLD",
    "BIDDING",
    new Date(Date.now() - 3600000).toISOString(),
  ),
  makeTxn(
    "t4",
    "Delta",
    "ACTIVE",
    "PREPARATION",
    new Date(Date.now() - 7200000).toISOString(),
  ),
  makeTxn("t5", "Epsilon", "TERMINATED", "CLOSING", now),
  makeTxn(
    "t6",
    "Zeta",
    "ACTIVE",
    "ENGAGEMENT",
    new Date(Date.now() - 86400000).toISOString(),
  ),
  makeTxn(
    "t7",
    "Eta",
    "DRAFT",
    "ENGAGEMENT",
    new Date(Date.now() - 172800000).toISOString(),
  ),
  makeTxn(
    "t8",
    "Theta",
    "ACTIVE",
    "NEGOTIATION",
    new Date(Date.now() - 259200000).toISOString(),
  ),
];

function useMockTransactions() {
  server.use(
    http.get("*/api/ma/transactions", () =>
      HttpResponse.json({
        items: mockItems,
        total: mockItems.length,
        limit: 20,
        offset: 0,
      }),
    ),
  );
}

describe("RecentProjectUpdatesWidget", () => {
  it("renders at most 5 items, excluding COMPLETED and TERMINATED", async () => {
    useMockTransactions();
    renderWithProviders(<RecentProjectUpdatesWidget />);

    await waitFor(() => {
      expect(screen.getByText("Alpha")).toBeInTheDocument();
    });

    // COMPLETED (Beta) and TERMINATED (Epsilon) should be excluded
    expect(screen.queryByText("Beta")).not.toBeInTheDocument();
    expect(screen.queryByText("Epsilon")).not.toBeInTheDocument();

    // Visible: Alpha, Gamma, Delta, Zeta, Eta (5 items) — Theta is 6th, excluded by slice
    expect(screen.getByText("Gamma")).toBeInTheDocument();
    expect(screen.getByText("Delta")).toBeInTheDocument();
    expect(screen.getByText("Zeta")).toBeInTheDocument();
    expect(screen.getByText("Eta")).toBeInTheDocument();
    expect(screen.queryByText("Theta")).not.toBeInTheDocument();
  });

  it("shows phase label and status badge", async () => {
    useMockTransactions();
    renderWithProviders(<RecentProjectUpdatesWidget />);

    await waitFor(() => {
      expect(screen.getByText("마케팅 단계")).toBeInTheDocument();
    });
    expect(screen.getAllByText("진행중").length).toBeGreaterThan(0);
  });

  it("shows empty state when no visible transactions", async () => {
    server.use(
      http.get("*/api/ma/transactions", () =>
        HttpResponse.json({ items: [], total: 0, limit: 20, offset: 0 }),
      ),
    );

    renderWithProviders(<RecentProjectUpdatesWidget />);

    await waitFor(() => {
      expect(
        screen.getByText("최근 업데이트된 프로젝트가 없습니다"),
      ).toBeInTheDocument();
    });
  });
});
