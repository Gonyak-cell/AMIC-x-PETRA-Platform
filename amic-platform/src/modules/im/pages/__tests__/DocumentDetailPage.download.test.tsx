/**
 * DocumentDetailPage 다운로드 섹션 UX 테스트
 *
 * doc.status가 COMPLETED / QUALITY_CONDITIONAL / QUALITY_FAILED 일 때
 * Download 카드, 경고 텍스트, PPTX 버튼의 렌더링 동작을 검증한다.
 *
 * 검증 대상: DocumentDetailPage.tsx L288-345
 */

import { render, screen } from "@testing-library/react";
import { vi } from "vitest";
import type { Document } from "@/modules/im/types/document";

// ── 모듈 모킹 ─────────────────────────────────────────────────────────────────

vi.mock("react-router-dom", async (importOriginal) => {
  const mod = await importOriginal<typeof import("react-router-dom")>();
  return {
    ...mod,
    useParams: vi.fn(() => ({ documentId: "test-doc-1" })),
    useNavigate: vi.fn(() => vi.fn()),
  };
});

vi.mock("@/modules/im/hooks/useDocuments", () => ({
  useDocument: vi.fn(),
  useCreateDocument: vi.fn(() => ({ mutateAsync: vi.fn() })),
  useUploadFinancials: vi.fn(() => ({
    mutateAsync: vi.fn(),
    isPending: false,
  })),
  useDownloadDocument: vi.fn(() => ({ mutateAsync: vi.fn() })),
}));

vi.mock("@/modules/im/hooks/useIMRalphLoop", () => ({
  useIMRalphSessions: vi.fn(() => ({ data: [] })),
}));

vi.mock("@/modules/im/hooks/useDiagrams", () => ({
  useDiagrams: vi.fn(() => ({ data: [], isLoading: false })),
}));

vi.mock("@/assets/images/heroes/forestgp-vc.jpg", () => ({
  default: "hero.jpg",
}));

// sonner toast는 실제 DOM 렌더링 없이 no-op으로 처리
vi.mock("sonner", () => ({
  toast: { success: vi.fn(), error: vi.fn() },
}));

// excalidraw를 사용하는 DiagramsCard는 jsdom에서 로드 불가 → stub으로 대체
vi.mock("@/modules/im/components/DiagramsCard", () => ({
  DiagramsCard: () => null,
}));

// ── 타입 임포트 (모킹 이후) ──────────────────────────────────────────────────

import { MemoryRouter } from "react-router-dom";
import { useDocument } from "@/modules/im/hooks/useDocuments";
import DocumentDetailPage from "../DocumentDetailPage";

// ── Document 팩토리 ───────────────────────────────────────────────────────────

function makeDoc(overrides: Partial<Document> = {}): Document {
  return {
    id: "test-doc-1",
    owner_id: "user-1",
    corp_code: "00126380",
    company_name: "Test Company",
    project_name: "Test Project",
    data_source: "DART",
    im_style: "TITAN",
    sections: ["cover", "deal_overview"],
    industry: null,
    status: "COMPLETED",
    progress_pct: 100,
    celery_task_id: null,
    pptx_path: "/output/test.pptx",
    pdf_path: null,
    file_size_bytes: 1024000,
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
    completed_at: "2026-01-01T01:00:00Z",
    stage_details: null,
    quality_score: null,
    quality_status: null,
    quality_issues: null,
    slide_count: 10,
    generation_profile: null,
    supported_formats: ["pptx"],
    ...overrides,
  };
}

// ── 헬퍼 ─────────────────────────────────────────────────────────────────────

function renderWithDoc(doc: Document) {
  vi.mocked(useDocument).mockReturnValue({
    data: doc,
    isLoading: false,
  } as ReturnType<typeof useDocument>);
  return render(
    <MemoryRouter>
      <DocumentDetailPage />
    </MemoryRouter>,
  );
}

// ── 테스트 ───────────────────────────────────────────────────────────────────

describe("DocumentDetailPage — 다운로드 섹션 UX", () => {
  it("QUALITY_CONDITIONAL → '품질 조건부 통과 문서입니다' 경고 텍스트를 표시한다", () => {
    renderWithDoc(makeDoc({ status: "QUALITY_CONDITIONAL" }));
    expect(
      screen.getByText(
        "품질 조건부 통과 문서입니다. 일부 항목을 확인해 주세요.",
      ),
    ).toBeInTheDocument();
  });

  it("QUALITY_CONDITIONAL → Download 카드를 표시한다", () => {
    renderWithDoc(makeDoc({ status: "QUALITY_CONDITIONAL" }));
    // Card title="Download" 로 렌더링되는 텍스트
    expect(screen.getByText("Download")).toBeInTheDocument();
  });

  it("QUALITY_CONDITIONAL → PPTX 다운로드 버튼을 표시한다", () => {
    renderWithDoc(
      makeDoc({
        status: "QUALITY_CONDITIONAL",
        pptx_path: "/output/test.pptx",
      }),
    );
    expect(screen.getByRole("button", { name: /PPTX/i })).toBeInTheDocument();
  });

  it("QUALITY_FAILED → '품질 검증 미통과 문서입니다' 경고 텍스트를 표시한다", () => {
    renderWithDoc(makeDoc({ status: "QUALITY_FAILED" }));
    expect(
      screen.getByText("품질 검증 미통과 문서입니다. 다운로드는 가능합니다."),
    ).toBeInTheDocument();
  });

  it("QUALITY_FAILED → QUALITY_CONDITIONAL 경고 텍스트는 표시하지 않는다", () => {
    renderWithDoc(makeDoc({ status: "QUALITY_FAILED" }));
    expect(
      screen.queryByText(/품질 조건부 통과 문서입니다/),
    ).not.toBeInTheDocument();
  });

  it("COMPLETED → 경고 텍스트 없이 Download 카드만 표시한다", () => {
    renderWithDoc(makeDoc({ status: "COMPLETED" }));
    // Download 카드는 존재한다
    expect(screen.getByText("Download")).toBeInTheDocument();
    // QUALITY_CONDITIONAL 경고 없음
    expect(
      screen.queryByText(/품질 조건부 통과 문서입니다/),
    ).not.toBeInTheDocument();
    // QUALITY_FAILED 경고 없음
    expect(
      screen.queryByText(/품질 검증 미통과 문서입니다/),
    ).not.toBeInTheDocument();
  });

  it("ANALYZING (진행 중) → Download 카드의 경고 텍스트와 PPTX 버튼을 표시하지 않는다", () => {
    renderWithDoc(
      makeDoc({
        status: "ANALYZING",
        progress_pct: 50,
        pptx_path: null,
        completed_at: null,
      }),
    );
    // 다운로드 섹션에만 나타나는 경고 텍스트가 없어야 한다
    expect(
      screen.queryByText(/품질 조건부 통과 문서입니다/),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByText(/품질 검증 미통과 문서입니다/),
    ).not.toBeInTheDocument();
    // PPTX 버튼이 없어야 한다
    expect(
      screen.queryByRole("button", { name: /PPTX/i }),
    ).not.toBeInTheDocument();
  });
});
