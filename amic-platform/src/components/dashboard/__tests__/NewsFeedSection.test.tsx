import { renderWithProviders, screen, waitFor } from "@/test/test-utils";
import { fireEvent } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { server } from "@/test/mocks/server";
import { mockNewsFeedItems } from "@/test/mocks/ma-handlers";
import NewsFeedSection from "../NewsFeedSection";

describe("NewsFeedSection", () => {
  it("renders news items from API", async () => {
    renderWithProviders(<NewsFeedSection />);

    await waitFor(() => {
      expect(screen.getByText("삼성전자 M&A 딜 진행 소식")).toBeInTheDocument();
    });

    expect(screen.getByText("사모펀드 GP 평판 리포트")).toBeInTheDocument();
    // 소스 이름은 필터 사이드바 + 뉴스 아이템에 모두 있으므로 getAllByText
    expect(screen.getAllByText("딜사이트").length).toBeGreaterThanOrEqual(2);
    expect(screen.getAllByText("인베스트조선").length).toBeGreaterThanOrEqual(
      2,
    );
  });

  it("shows apiError warning banner when response includes error field", async () => {
    server.use(
      http.get("*/api/ma/news-feed/latest", () =>
        HttpResponse.json({
          items: mockNewsFeedItems,
          total: mockNewsFeedItems.length,
          cached: true,
          error: "KIIS 연결 장애 — 캐시된 데이터 표시 중",
        }),
      ),
    );

    renderWithProviders(<NewsFeedSection />);

    await waitFor(() => {
      expect(
        screen.getByText("KIIS 연결 장애 — 캐시된 데이터 표시 중"),
      ).toBeInTheDocument();
    });

    // 데이터는 여전히 표시됨 (부분 성공)
    expect(screen.getByText("삼성전자 M&A 딜 진행 소식")).toBeInTheDocument();
  });

  it("shows error state with retry button on hard failure", async () => {
    server.use(
      http.get("*/api/ma/news-feed/latest", () => HttpResponse.error()),
    );

    renderWithProviders(<NewsFeedSection />);

    await waitFor(() => {
      expect(
        screen.getByText("뉴스를 불러오지 못했습니다"),
      ).toBeInTheDocument();
    });

    expect(screen.getByText("다시 시도")).toBeInTheDocument();
  });

  it("shows empty state when no items", async () => {
    server.use(
      http.get("*/api/ma/news-feed/latest", () =>
        HttpResponse.json({
          items: [],
          total: 0,
          cached: false,
          error: null,
        }),
      ),
    );

    renderWithProviders(<NewsFeedSection />);

    await waitFor(() => {
      expect(screen.getByText("표시할 뉴스가 없습니다")).toBeInTheDocument();
    });
  });

  it("sends correct query params for source filter", async () => {
    let capturedUrl: string | null = null;
    server.use(
      http.get("*/api/ma/news-feed/latest", ({ request }) => {
        capturedUrl = request.url;
        return HttpResponse.json({
          items: [],
          total: 0,
          cached: false,
          error: null,
        });
      }),
    );

    renderWithProviders(<NewsFeedSection />);

    // 초기 로드 대기
    await waitFor(() => {
      expect(capturedUrl).not.toBeNull();
    });

    // "딜사이트" 소스 필터 클릭
    const dealSiteBtn = screen.getByRole("button", { name: /딜사이트/ });
    fireEvent.click(dealSiteBtn);

    await waitFor(() => {
      expect(capturedUrl).toContain("source=dealsite");
    });
  });
});
