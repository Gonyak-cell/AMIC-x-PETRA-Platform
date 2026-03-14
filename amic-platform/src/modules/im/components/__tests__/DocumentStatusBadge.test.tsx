import { render, screen } from "@testing-library/react";
import { DocumentStatusBadge } from "../DocumentStatusBadge";

describe("DocumentStatusBadge", () => {
  describe("QUALITY_CONDITIONAL 상태", () => {
    it("QUALITY_CONDITIONAL → '품질 조건부' 텍스트를 렌더링한다", () => {
      render(<DocumentStatusBadge status="QUALITY_CONDITIONAL" />);
      expect(screen.getByText("품질 조건부")).toBeInTheDocument();
    });

    it("QUALITY_CONDITIONAL → warning variant CSS 클래스를 적용한다", () => {
      render(<DocumentStatusBadge status="QUALITY_CONDITIONAL" />);
      const badge = screen.getByText("품질 조건부");
      // warning variant: bg-amber-50 text-caution
      expect(badge).toHaveClass("bg-amber-50");
    });
  });

  describe("QUALITY_FAILED 상태", () => {
    it("QUALITY_FAILED → '품질 미통과' 텍스트를 렌더링한다", () => {
      render(<DocumentStatusBadge status="QUALITY_FAILED" />);
      expect(screen.getByText("품질 미통과")).toBeInTheDocument();
    });

    it("QUALITY_FAILED → error variant CSS 클래스를 적용한다", () => {
      render(<DocumentStatusBadge status="QUALITY_FAILED" />);
      const badge = screen.getByText("품질 미통과");
      // error variant: bg-red-50 text-negative
      expect(badge).toHaveClass("bg-red-50");
    });
  });

  describe("COMPLETED 상태", () => {
    it("COMPLETED → 'Completed' 텍스트를 렌더링한다", () => {
      render(<DocumentStatusBadge status="COMPLETED" />);
      expect(screen.getByText("Completed")).toBeInTheDocument();
    });

    it("COMPLETED → success variant CSS 클래스를 적용한다", () => {
      render(<DocumentStatusBadge status="COMPLETED" />);
      const badge = screen.getByText("Completed");
      // success variant: bg-accent-light text-positive
      expect(badge).toHaveClass("text-positive");
    });
  });

  describe("qualityStatus prop", () => {
    it("qualityStatus='CONDITIONAL' 전달 시 두 번째 Badge를 렌더링한다", () => {
      render(
        <DocumentStatusBadge
          status="QUALITY_CONDITIONAL"
          qualityStatus="CONDITIONAL"
        />,
      );
      // 첫 번째 Badge: 문서 상태
      expect(screen.getByText("품질 조건부")).toBeInTheDocument();
      // 두 번째 Badge: quality status
      expect(screen.getByText("조건부")).toBeInTheDocument();
    });

    it("qualityStatus='CONDITIONAL' → 두 번째 Badge에 warning variant를 적용한다", () => {
      render(
        <DocumentStatusBadge
          status="QUALITY_CONDITIONAL"
          qualityStatus="CONDITIONAL"
        />,
      );
      const qualityBadge = screen.getByText("조건부");
      expect(qualityBadge).toHaveClass("bg-amber-50");
    });

    it("qualityStatus=null → Badge 1개만 렌더링한다", () => {
      render(<DocumentStatusBadge status="COMPLETED" qualityStatus={null} />);
      expect(screen.getByText("Completed")).toBeInTheDocument();
      // 두 번째 Badge(품질 라벨)가 없음을 확인
      expect(screen.queryByText("통과")).not.toBeInTheDocument();
      expect(screen.queryByText("조건부")).not.toBeInTheDocument();
      expect(screen.queryByText("미통과")).not.toBeInTheDocument();
    });

    it("qualityStatus 미전달 → Badge 1개만 렌더링한다", () => {
      render(<DocumentStatusBadge status="COMPLETED" />);
      expect(screen.getByText("Completed")).toBeInTheDocument();
      expect(screen.queryByText("통과")).not.toBeInTheDocument();
    });

    it("qualityStatus='PASS' → '통과' 텍스트와 success variant를 렌더링한다", () => {
      render(<DocumentStatusBadge status="COMPLETED" qualityStatus="PASS" />);
      const qualityBadge = screen.getByText("통과");
      expect(qualityBadge).toBeInTheDocument();
      expect(qualityBadge).toHaveClass("text-positive");
    });

    it("qualityStatus='FAIL' → '미통과' 텍스트와 error variant를 렌더링한다", () => {
      render(
        <DocumentStatusBadge status="QUALITY_FAILED" qualityStatus="FAIL" />,
      );
      expect(screen.getByText("미통과")).toBeInTheDocument();
      const qualityBadge = screen.getByText("미통과");
      expect(qualityBadge).toHaveClass("bg-red-50");
    });
  });
});
