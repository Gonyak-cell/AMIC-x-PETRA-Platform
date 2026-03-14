/**
 * DocumentListPage QUALITY_CONDITIONAL 로직 회귀 테스트
 *
 * 페이지 전체 렌더링 없이 핵심 필터/KPI 계산 로직만 순수 함수로 검증한다.
 * DocumentListPage.tsx의 filteredItems / kpis 계산 로직을 인라인으로 재현한다.
 */
import type { Document } from "@/modules/im/types/document";
import { IN_PROGRESS_STATUSES } from "@/modules/im/types/document";

// ── 테스트용 Document 팩토리 ─────────────────────────────────────────────────

function makeDoc(
  id: string,
  status: Document["status"],
): Pick<Document, "id" | "status"> {
  return { id, status };
}

// ── DocumentListPage의 filteredItems 로직 (인라인 재현) ────────────────────────

type StatusFilter = "ALL" | "IN_PROGRESS" | Document["status"];

function applyStatusFilter(
  items: Pick<Document, "id" | "status">[],
  statusFilter: StatusFilter,
): Pick<Document, "id" | "status">[] {
  if (statusFilter === "ALL") return items;
  if (statusFilter === "IN_PROGRESS")
    return items.filter((d) => IN_PROGRESS_STATUSES.includes(d.status));
  if (statusFilter === "COMPLETED")
    return items.filter(
      (d) => d.status === "COMPLETED" || d.status === "QUALITY_CONDITIONAL",
    );
  return items.filter((d) => d.status === statusFilter);
}

// ── DocumentListPage의 kpis 계산 로직 (인라인 재현) ──────────────────────────

function calcKpis(items: Pick<Document, "id" | "status">[]) {
  return {
    inProgress: items.filter((d) => IN_PROGRESS_STATUSES.includes(d.status))
      .length,
    completed: items.filter(
      (d) => d.status === "COMPLETED" || d.status === "QUALITY_CONDITIONAL",
    ).length,
    qualityFailed: items.filter((d) => d.status === "QUALITY_FAILED").length,
    failed: items.filter((d) => d.status === "FAILED").length,
  };
}

// ── 공통 픽스처 ──────────────────────────────────────────────────────────────

const fixtures = [
  makeDoc("doc-1", "COMPLETED"),
  makeDoc("doc-2", "QUALITY_CONDITIONAL"),
  makeDoc("doc-3", "QUALITY_CONDITIONAL"),
  makeDoc("doc-4", "QUALITY_FAILED"),
  makeDoc("doc-5", "FAILED"),
  makeDoc("doc-6", "ANALYZING"),
  makeDoc("doc-7", "PENDING"),
];

// ── 테스트 ───────────────────────────────────────────────────────────────────

describe("DocumentListPage — QUALITY_CONDITIONAL 필터 로직", () => {
  describe("'COMPLETED' 필터", () => {
    it("QUALITY_CONDITIONAL 문서를 포함하여 반환한다", () => {
      const result = applyStatusFilter(fixtures, "COMPLETED");
      const ids = result.map((d) => d.id);
      expect(ids).toContain("doc-2");
      expect(ids).toContain("doc-3");
    });

    it("COMPLETED 문서를 포함하여 반환한다", () => {
      const result = applyStatusFilter(fixtures, "COMPLETED");
      expect(result.map((d) => d.id)).toContain("doc-1");
    });

    it("QUALITY_FAILED 문서는 포함하지 않는다", () => {
      const result = applyStatusFilter(fixtures, "COMPLETED");
      expect(result.map((d) => d.id)).not.toContain("doc-4");
    });

    it("FAILED 문서는 포함하지 않는다", () => {
      const result = applyStatusFilter(fixtures, "COMPLETED");
      expect(result.map((d) => d.id)).not.toContain("doc-5");
    });

    it("진행 중 문서는 포함하지 않는다", () => {
      const result = applyStatusFilter(fixtures, "COMPLETED");
      const inProgressIds = ["doc-6", "doc-7"];
      inProgressIds.forEach((id) => {
        expect(result.map((d) => d.id)).not.toContain(id);
      });
    });

    it("COMPLETED 1 + QUALITY_CONDITIONAL 2 = 총 3개를 반환한다", () => {
      const result = applyStatusFilter(fixtures, "COMPLETED");
      expect(result).toHaveLength(3);
    });
  });

  describe("'ALL' 필터", () => {
    it("모든 문서를 반환한다", () => {
      const result = applyStatusFilter(fixtures, "ALL");
      expect(result).toHaveLength(fixtures.length);
    });
  });

  describe("'IN_PROGRESS' 필터", () => {
    it("QUALITY_CONDITIONAL을 포함하지 않는다", () => {
      const result = applyStatusFilter(fixtures, "IN_PROGRESS");
      expect(result.map((d) => d.id)).not.toContain("doc-2");
    });

    it("진행 중 상태(ANALYZING, PENDING)만 반환한다", () => {
      const result = applyStatusFilter(fixtures, "IN_PROGRESS");
      expect(result.map((d) => d.id)).toContain("doc-6"); // ANALYZING
      expect(result.map((d) => d.id)).toContain("doc-7"); // PENDING
    });
  });
});

describe("DocumentListPage — QUALITY_CONDITIONAL KPI 계산", () => {
  it("completed KPI에 QUALITY_CONDITIONAL을 합산한다", () => {
    const kpis = calcKpis(fixtures);
    // doc-1(COMPLETED) + doc-2(QUALITY_CONDITIONAL) + doc-3(QUALITY_CONDITIONAL) = 3
    expect(kpis.completed).toBe(3);
  });

  it("completed KPI: QUALITY_CONDITIONAL만 있을 때도 정상 집계한다", () => {
    const onlyConditional = [
      makeDoc("a", "QUALITY_CONDITIONAL"),
      makeDoc("b", "QUALITY_CONDITIONAL"),
    ];
    expect(calcKpis(onlyConditional).completed).toBe(2);
  });

  it("qualityFailed KPI는 QUALITY_FAILED만 집계한다", () => {
    const kpis = calcKpis(fixtures);
    // doc-4(QUALITY_FAILED) = 1
    expect(kpis.qualityFailed).toBe(1);
  });

  it("QUALITY_CONDITIONAL은 qualityFailed KPI에 포함되지 않는다", () => {
    const items = [
      makeDoc("a", "QUALITY_CONDITIONAL"),
      makeDoc("b", "QUALITY_FAILED"),
    ];
    const kpis = calcKpis(items);
    expect(kpis.qualityFailed).toBe(1);
    expect(kpis.completed).toBe(1);
  });

  it("failed KPI는 FAILED만 집계한다", () => {
    const kpis = calcKpis(fixtures);
    // doc-5(FAILED) = 1
    expect(kpis.failed).toBe(1);
  });

  it("inProgress KPI는 IN_PROGRESS_STATUSES만 집계한다", () => {
    const kpis = calcKpis(fixtures);
    // doc-6(ANALYZING) + doc-7(PENDING) = 2
    expect(kpis.inProgress).toBe(2);
  });

  it("빈 배열 입력 시 모든 KPI가 0이다", () => {
    const kpis = calcKpis([]);
    expect(kpis.completed).toBe(0);
    expect(kpis.qualityFailed).toBe(0);
    expect(kpis.failed).toBe(0);
    expect(kpis.inProgress).toBe(0);
  });
});
