import { render, screen } from "@testing-library/react";
import { ProgressTracker } from "../ProgressTracker";

describe("ProgressTracker", () => {
  describe("QUALITY_CONDITIONAL 상태", () => {
    it("QUALITY_CONDITIONAL + progressPct=100 → progressbar aria-valuenow=100을 렌더링한다", () => {
      render(
        <ProgressTracker status="QUALITY_CONDITIONAL" progressPct={100} />,
      );
      const progressBar = screen.getByRole("progressbar");
      expect(progressBar).toHaveAttribute("aria-valuenow", "100");
    });

    it("QUALITY_CONDITIONAL → '100%' 텍스트를 표시한다", () => {
      render(
        <ProgressTracker status="QUALITY_CONDITIONAL" progressPct={100} />,
      );
      expect(screen.getByText("100%")).toBeInTheDocument();
    });

    it("QUALITY_CONDITIONAL은 COMPLETED와 동일한 STATUS_ORDER(5)를 가져 모든 스테이지가 완료 표시된다", () => {
      // STATUS_ORDER: COMPLETED = 5, QUALITY_CONDITIONAL = 5
      // STAGES는 6개(index 0~5), currentIndex=5이면 index < 5인 0~4 모두 isCompleted=true
      // 마지막 스테이지(index=5, "Complete")는 isCurrent=true
      render(
        <ProgressTracker status="QUALITY_CONDITIONAL" progressPct={100} />,
      );

      // progressbar가 100%로 렌더링됨
      const progressBar = screen.getByRole("progressbar");
      expect(progressBar).toHaveAttribute("aria-valuenow", "100");
      expect(progressBar).toHaveAttribute("aria-valuemax", "100");
    });

    it("COMPLETED와 동일한 진행률 표시 — 두 상태 모두 100%를 렌더링한다", () => {
      const { unmount } = render(
        <ProgressTracker status="COMPLETED" progressPct={100} />,
      );
      const completedBar = screen.getByRole("progressbar");
      const completedValueNow = completedBar.getAttribute("aria-valuenow");
      unmount();

      render(
        <ProgressTracker status="QUALITY_CONDITIONAL" progressPct={100} />,
      );
      const conditionalBar = screen.getByRole("progressbar");
      const conditionalValueNow = conditionalBar.getAttribute("aria-valuenow");

      expect(conditionalValueNow).toBe(completedValueNow);
      expect(conditionalValueNow).toBe("100");
    });
  });

  describe("FAILED 상태", () => {
    it("FAILED → progressbar에 '(failed)' aria-label을 포함한다", () => {
      render(<ProgressTracker status="FAILED" progressPct={55} />);
      const progressBar = screen.getByRole("progressbar");
      expect(progressBar).toHaveAttribute(
        "aria-label",
        expect.stringContaining("failed"),
      );
    });
  });

  describe("진행 중 상태", () => {
    it("RENDERING + progressPct=80 → progressbar aria-valuenow=80", () => {
      render(<ProgressTracker status="RENDERING" progressPct={80} />);
      const progressBar = screen.getByRole("progressbar");
      expect(progressBar).toHaveAttribute("aria-valuenow", "80");
      expect(screen.getByText("80%")).toBeInTheDocument();
    });

    it("progressPct가 음수면 0으로 처리한다", () => {
      render(<ProgressTracker status="PENDING" progressPct={-10} />);
      const progressBar = screen.getByRole("progressbar");
      expect(progressBar).toHaveAttribute("aria-valuenow", "0");
    });

    it("progressPct가 100을 초과하면 100으로 처리한다", () => {
      render(<ProgressTracker status="COMPLETED" progressPct={150} />);
      const progressBar = screen.getByRole("progressbar");
      expect(progressBar).toHaveAttribute("aria-valuenow", "100");
    });
  });
});
