import { beforeEach, describe, expect, it, vi } from "vitest";

import type { DocumentExtraction } from "@/modules/ma/types/document_extraction";
import { renderWithProviders, screen } from "@/test/test-utils";

import ExtractionReviewModal from "../ExtractionReviewModal";

const mutateMock = vi.fn();
const emptyBuyers: [] = [];
const emptyNdas: [] = [];
const emptyEngagements: [] = [];
const transactionData = {
  client_name: "Client Co",
};

vi.mock("@/modules/ma/hooks/useDocumentExtraction", () => ({
  useConfirmExtraction: () => ({
    mutate: mutateMock,
    isPending: false,
  }),
  useExtraction: () => ({
    data: undefined,
  }),
}));

vi.mock("@/modules/ma/hooks/useTransactions", () => ({
  useBuyers: () => ({ data: emptyBuyers }),
  useEngagements: () => ({ data: emptyEngagements }),
  useTransaction: () => ({
    data: transactionData,
  }),
}));

vi.mock("@/modules/ma/hooks/useNdas", () => ({
  useNdas: () => ({ data: emptyNdas }),
}));

const baseExtraction: DocumentExtraction = {
  id: "ext-1",
  transaction_id: "txn-1",
  vdr_document_id: "doc-1",
  doc_category: "REGISTRY_DOCS",
  classification_confidence: 1,
  status: "COMPLETED",
  error_message: null,
  extracted_data: {},
  target_model: null,
  target_id: null,
  llm_cost_usd: 0,
  reviewed_by_email: null,
  reviewed_at: null,
  created_at: "2026-03-23T00:00:00Z",
  updated_at: "2026-03-23T00:00:00Z",
};

function renderModal(overrides: Partial<DocumentExtraction> = {}) {
  return renderWithProviders(
    <ExtractionReviewModal
      txnId="txn-1"
      extraction={{ ...baseExtraction, ...overrides }}
      open
      onClose={vi.fn()}
    />,
  );
}

describe("ExtractionReviewModal", () => {
  beforeEach(() => {
    mutateMock.mockReset();
  });

  it("shows an empty-result state instead of review pending when extracted data is blank", () => {
    renderModal({
      extracted_data: {},
    });

    expect(screen.getByText("추출값 없음")).toBeInTheDocument();
    expect(
      screen.getByText(/AI가 문서에서 채울 값을 찾지 못했습니다/),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "확정" }),
    ).not.toBeInTheDocument();
  });

  it("keeps the review flow available when extracted data exists", () => {
    renderModal({
      extracted_data: {
        company_name: "테스트 주식회사",
      },
    });

    expect(screen.getByText("검토 대기")).toBeInTheDocument();
    expect(screen.getByDisplayValue("테스트 주식회사")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "확정" })).toBeInTheDocument();
  });
});
