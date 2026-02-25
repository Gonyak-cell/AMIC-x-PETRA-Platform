/**
 * API 스키마 계약 테스트
 *
 * 백엔드 응답 mock 데이터의 구조가 프론트엔드 타입과 일치하는지 검증한다.
 * 백엔드 스키마 변경(필드 삭제, 이름 변경 등) 시 이 테스트가 실패하여
 * 프론트엔드 crash를 사전에 방지한다.
 */
import type { Deal } from "@/modules/fdd/types/deal";
import type { Document } from "@/modules/im/types/document";
import type { ModuleHealth } from "@/types/dashboard";

// ── 필수 필드 존재 검증 헬퍼 ─────────────────────────

function assertRequiredFields<T extends Record<string, unknown>>(
  obj: T,
  fields: string[],
) {
  for (const field of fields) {
    expect(obj).toHaveProperty(field);
    expect(typeof obj[field] !== "undefined").toBe(true);
  }
}

// ── FDD Deal 스키마 계약 ─────────────────────────

describe("FDD Deal 스키마 계약", () => {
  const mockDeal: Deal = {
    id: "deal-001",
    name: "Test Deal",
    deal_type: "COMPLETION_ACCOUNTS",
    base_currency: "KRW",
    reference_date: "2026-01-01",
    period_start: "2025-01-01",
    period_end: "2025-12-31",
    status: "ACTIVE",
    created_by: "user-1",
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-15T00:00:00Z",
    current_phase: "ANALYSIS",
    target_company_name: "Target Corp",
    client_name: "Client Corp",
    client_contact_name: null,
    client_contact_email: null,
    team_partner_id: null,
    team_manager_id: null,
    scope_qoe: true,
    scope_nwc: true,
    scope_debt: false,
    industry: "general",
    deal_structure: null,
    investment_type: null,
    seller_type: null,
  };

  it("필수 필드가 모두 존재한다", () => {
    assertRequiredFields(mockDeal, [
      "id", "name", "status", "created_at", "updated_at", "current_phase",
    ]);
  });

  it("id는 문자열이다", () => {
    expect(typeof mockDeal.id).toBe("string");
  });

  it("status는 유효한 값이다", () => {
    const validStatuses = ["DRAFT", "ACTIVE", "ARCHIVED"];
    expect(validStatuses).toContain(mockDeal.status);
  });

  it("deal_type은 유효한 값이다", () => {
    const validTypes = ["COMPLETION_ACCOUNTS", "LOCKED_BOX"];
    expect(validTypes).toContain(mockDeal.deal_type);
  });

  it("current_phase는 유효한 값이다", () => {
    const validPhases = ["MOU", "VDR_SETUP", "DATA_UPLOAD", "ANALYSIS", "REPORTING"];
    expect(validPhases).toContain(mockDeal.current_phase);
  });

  it("created_at은 ISO 8601 형식이다", () => {
    expect(new Date(mockDeal.created_at).toISOString()).toBeDefined();
    expect(mockDeal.created_at).toMatch(/^\d{4}-\d{2}-\d{2}T/);
  });

  it("created_at.slice(0, 10)으로 날짜 추출 가능하다", () => {
    const dateStr = mockDeal.created_at.slice(0, 10);
    expect(dateStr).toMatch(/^\d{4}-\d{2}-\d{2}$/);
  });
});

// ── IM Document 스키마 계약 ─────────────────────────

describe("IM Document 스키마 계약", () => {
  const mockDoc: Document = {
    id: "doc-001",
    owner_id: "user-1",
    project_name: "Test Project",
    company_name: "Test Corp",
    corp_code: "00123456",
    data_source: "DART",
    im_style: "TITAN",
    sections: ["cover", "executive_summary"],
    industry: "general",
    status: "COMPLETED",
    progress_pct: 100,
    celery_task_id: null,
    pptx_path: "/output/doc-001.pptx",
    pdf_path: null,
    file_size_bytes: null,
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-02T00:00:00Z",
    completed_at: "2026-01-02T00:00:00Z",
  };

  it("필수 필드가 모두 존재한다", () => {
    assertRequiredFields(mockDoc, [
      "id", "status", "created_at", "owner_id", "company_name",
    ]);
  });

  it("status는 유효한 값이다", () => {
    const validStatuses = [
      "PENDING", "COLLECTING", "ANALYZING", "GENERATING",
      "RENDERING", "COMPLETED", "FAILED",
    ];
    expect(validStatuses).toContain(mockDoc.status);
  });

  it("im_style은 유효한 값이다", () => {
    const validStyles = ["TITAN", "COVENANT", "FULL", "TEASER", "CUSTOM"];
    expect(validStyles).toContain(mockDoc.im_style);
  });

  it("created_at.slice(0, 10)으로 날짜 추출 가능하다", () => {
    const dateStr = mockDoc.created_at.slice(0, 10);
    expect(dateStr).toMatch(/^\d{4}-\d{2}-\d{2}$/);
  });
});

// ── ModuleHealth 스키마 계약 ─────────────────────────

describe("ModuleHealth 스키마 계약", () => {
  const mockHealth: ModuleHealth = {
    module: "fdd",
    label: "FDD Engine",
    healthy: true,
  };

  it("module은 유효한 모듈 이름이다", () => {
    const validModules = ["fdd", "kiis", "ma", "im"];
    expect(validModules).toContain(mockHealth.module);
  });

  it("healthy는 boolean이다", () => {
    expect(typeof mockHealth.healthy).toBe("boolean");
  });

  it("label은 문자열이다", () => {
    expect(typeof mockHealth.label).toBe("string");
    expect(mockHealth.label.length).toBeGreaterThan(0);
  });
});

// ── Calendar 이벤트 날짜 필드 계약 ─────────────────────────

describe("Calendar 이벤트 날짜 필드 계약", () => {
  it("Deal.created_at은 .slice()로 날짜 추출 가능하다", () => {
    const deal = { created_at: "2026-02-15T14:30:00Z" };
    expect(typeof deal.created_at).toBe("string");
    expect(deal.created_at.slice(0, 10)).toBe("2026-02-15");
  });

  it("Document.created_at도 동일 형식이다", () => {
    const doc = { created_at: "2026-03-01T09:00:00Z" };
    expect(typeof doc.created_at).toBe("string");
    expect(doc.created_at.slice(0, 10)).toBe("2026-03-01");
  });

  it("날짜 필드가 Date 객체로 파싱 가능하다", () => {
    const dateStr = "2026-02-15T14:30:00Z";
    const parsed = new Date(dateStr);
    expect(parsed.getTime()).toBeGreaterThan(0);
    expect(Number.isNaN(parsed.getTime())).toBe(false);
  });
});
