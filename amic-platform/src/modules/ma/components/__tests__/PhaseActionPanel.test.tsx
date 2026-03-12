import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { http, HttpResponse } from "msw";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { server } from "@/test/mocks/server";
import { mockPhaseStatus } from "@/test/mocks/ma-handlers";
import type { PhaseCompletionStatus } from "@/modules/ma/types/workflow";
import PhaseActionPanel from "../PhaseActionPanel";

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  });
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    );
  };
}

describe("PhaseActionPanel", () => {
  beforeEach(() => {
    server.resetHandlers();
  });

  it("로딩 중 Spinner를 표시한다", () => {
    // phase-status 응답을 지연시켜 로딩 상태 유지
    server.use(
      http.get(
        "*/api/ma/transactions/:txnId/workflow/phase-status",
        () => new Promise(() => {}), // never resolves
      ),
    );

    render(<PhaseActionPanel txnId="txn-1" />, { wrapper: createWrapper() });
    expect(screen.getByRole("status")).toBeInTheDocument();
  });

  it("충족된 조건에 line-through 스타일을 적용한다", async () => {
    render(<PhaseActionPanel txnId="txn-1" />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(
        screen.getByText("Short List 매수자 1명 이상"),
      ).toBeInTheDocument();
    });

    const satisfiedLabel = screen.getByText("Short List 매수자 1명 이상");
    expect(satisfiedLabel.className).toContain("line-through");
  });

  it("미충족 조건에 font-medium 스타일을 적용한다", async () => {
    render(<PhaseActionPanel txnId="txn-1" />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(
        screen.getByText("NDA 체결 또는 자료 배포 1건 이상"),
      ).toBeInTheDocument();
    });

    const unmetLabel = screen.getByText("NDA 체결 또는 자료 배포 1건 이상");
    expect(unmetLabel.className).toContain("font-medium");
    expect(unmetLabel.className).not.toContain("line-through");
  });

  it("requires_acknowledgement 항목에 체크박스를 렌더링한다", async () => {
    render(<PhaseActionPanel txnId="txn-1" />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText("DD 항목 없음 — 확인 필요")).toBeInTheDocument();
    });

    const checkbox = screen.getByRole("checkbox");
    expect(checkbox).toBeInTheDocument();
    expect(checkbox).not.toBeChecked();
  });

  it("체크박스 토글 시 onAcknowledgementsChange를 호출한다", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();

    render(
      <PhaseActionPanel txnId="txn-1" onAcknowledgementsChange={onChange} />,
      { wrapper: createWrapper() },
    );

    await waitFor(() => {
      expect(screen.getByRole("checkbox")).toBeInTheDocument();
    });

    await user.click(screen.getByRole("checkbox"));

    await waitFor(() => {
      expect(onChange).toHaveBeenCalledWith(
        expect.objectContaining({ dd_items_complete: true }),
      );
    });
  });

  it("gate_summary가 있으면 Info 블록을 표시한다", async () => {
    render(<PhaseActionPanel txnId="txn-1" />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(
        screen.getByText(
          "입찰 진입: Short List 매수자 및 NDA/자료 배포 완료 필요",
        ),
      ).toBeInTheDocument();
    });
  });

  it("프로그레스 바에 올바른 퍼센트를 표시한다 (2/3 = 67%)", async () => {
    // mockPhaseStatus: 3 prereqs, 2 satisfied (short_list + dd_items) → 67%
    render(<PhaseActionPanel txnId="txn-1" />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText("67%")).toBeInTheDocument();
    });

    expect(screen.getByText("필수 조건 2/3")).toBeInTheDocument();
  });

  it("prerequisites가 비어 있으면 빈 상태 메시지를 표시한다", async () => {
    const emptyStatus: PhaseCompletionStatus = {
      ...mockPhaseStatus,
      prerequisites: [],
      all_met: true,
      can_advance: true,
      blocking_reasons: [],
    };

    server.use(
      http.get("*/api/ma/transactions/:txnId/workflow/phase-status", () =>
        HttpResponse.json(emptyStatus),
      ),
    );

    render(<PhaseActionPanel txnId="txn-1" />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(
        screen.getByText("다음 단계 전환 조건이 없습니다."),
      ).toBeInTheDocument();
    });
  });

  it("현재 단계 라벨을 표시한다", async () => {
    render(<PhaseActionPanel txnId="txn-1" />, { wrapper: createWrapper() });

    await waitFor(() => {
      // PHASE_CONFIG에서 MARKETING → "마케팅" 라벨
      expect(screen.getByText(/현재 단계:/)).toBeInTheDocument();
    });
  });

  it("모든 조건 충족 시 프로그레스 100%를 표시한다", async () => {
    const allMetStatus: PhaseCompletionStatus = {
      ...mockPhaseStatus,
      prerequisites: [
        {
          field: "a",
          label: "조건 A",
          satisfied: true,
          current_value: "완료",
        },
        {
          field: "b",
          label: "조건 B",
          satisfied: true,
          current_value: "완료",
        },
      ],
      all_met: true,
      can_advance: true,
      blocking_reasons: [],
    };

    server.use(
      http.get("*/api/ma/transactions/:txnId/workflow/phase-status", () =>
        HttpResponse.json(allMetStatus),
      ),
    );

    render(<PhaseActionPanel txnId="txn-1" />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText("100%")).toBeInTheDocument();
    });

    expect(screen.getByText("필수 조건 2/2")).toBeInTheDocument();
  });
});
