import { act, renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { toast } from "sonner";

import { maApi } from "@/api/maClient";
import { useAttachmentExtractionFlow } from "../useAttachmentExtractionFlow";

const invalidateQueries = vi.fn();

vi.mock("sonner", () => ({
  toast: {
    error: vi.fn(),
    success: vi.fn(),
    warning: vi.fn(),
    info: vi.fn(),
  },
}));

vi.mock("@tanstack/react-query", () => ({
  useQueryClient: () => ({
    invalidateQueries,
  }),
}));

describe("useAttachmentExtractionFlow", () => {
  beforeEach(() => {
    vi.useRealTimers();
    invalidateQueries.mockReset();
    vi.mocked(toast.error).mockReset();
    vi.mocked(toast.success).mockReset();
    vi.mocked(toast.warning).mockReset();
    vi.mocked(toast.info).mockReset();
    vi.spyOn(maApi, "post").mockReset();
    vi.spyOn(maApi, "get").mockReset();
  });

  it("creates an extraction, invalidates the list, and opens the review", async () => {
    vi.spyOn(maApi, "post").mockResolvedValueOnce({
      data: {
        id: "ext-1",
        transaction_id: "txn-1",
        vdr_document_id: "vdr-1",
        status: "PENDING",
        doc_category_hint: "NDA",
        target_model: null,
        target_id: null,
        auto_apply_signed_at: false,
        extracted_data: null,
        created_at: "2026-03-31T00:00:00Z",
        updated_at: "2026-03-31T00:00:00Z",
      },
    });

    const { result } = renderHook(() => useAttachmentExtractionFlow("txn-1"));

    await act(async () => {
      await result.current.startExtractionFromUpload({
        attachment: {
          id: "att-1",
          transaction_id: "txn-1",
          entity_type: "NDA",
          entity_id: null,
          file_name: "nda.pdf",
          file_size_bytes: 128,
          mime_type: "application/pdf",
          description: null,
          uploaded_by_email: "test@example.com",
          created_at: "2026-03-31T00:00:00Z",
          updated_at: "2026-03-31T00:00:00Z",
          vdr_sync: {
            vdr_document_id: "vdr-1",
            folder_name: "NDA",
            category: null,
            classification_status: "SYNCED",
          },
        },
        file: new File(["pdf"], "nda.pdf", { type: "application/pdf" }),
        docCategoryHint: "NDA",
        reviewContext: { source: "buyer-nda", buyerCandidateId: "buyer-1" },
      });
    });

    await waitFor(() => {
      expect(invalidateQueries).toHaveBeenCalledWith({
        queryKey: ["ma", "transactions", "txn-1", "extractions"],
      });
    });

    expect(toast.success).toHaveBeenCalledWith("AI 분석을 시작했습니다.");
    expect(result.current.activeReview).toEqual({
      extraction: expect.objectContaining({ id: "ext-1" }),
      context: { source: "buyer-nda", buyerCandidateId: "buyer-1" },
    });
  });

  it("polls NDA extraction completion and refreshes NDA date queries", async () => {
    vi.useFakeTimers();
    vi.spyOn(maApi, "post").mockResolvedValueOnce({
      data: {
        id: "ext-nda-1",
        transaction_id: "txn-1",
        vdr_document_id: "vdr-1",
        status: "PENDING",
        doc_category: "NDA",
        target_model: "nda",
        target_id: "nda-1",
        auto_apply_signed_at: true,
        extracted_data: null,
        created_at: "2026-03-31T00:00:00Z",
        updated_at: "2026-03-31T00:00:00Z",
      },
    });
    vi.spyOn(maApi, "get").mockResolvedValueOnce({
      data: {
        id: "ext-nda-1",
        transaction_id: "txn-1",
        vdr_document_id: "vdr-1",
        status: "COMPLETED",
        doc_category: "NDA",
        target_model: "nda",
        target_id: "nda-1",
        auto_apply_signed_at: true,
        extracted_data: { signed_at: "2026-03-31" },
        created_at: "2026-03-31T00:00:00Z",
        updated_at: "2026-03-31T00:00:02Z",
      },
    });

    const { result } = renderHook(() => useAttachmentExtractionFlow("txn-1"));

    await act(async () => {
      await result.current.startExtractionFromUpload({
        attachment: {
          id: "att-1",
          transaction_id: "txn-1",
          entity_type: "NDA",
          entity_id: "nda-1",
          file_name: "nda.pdf",
          file_size_bytes: 128,
          mime_type: "application/pdf",
          description: null,
          uploaded_by_email: "test@example.com",
          created_at: "2026-03-31T00:00:00Z",
          updated_at: "2026-03-31T00:00:00Z",
          processing_status: "SYNCED",
          processing_error: null,
          vdr_sync: {
            vdr_document_id: "vdr-1",
            folder_name: "NDA",
            category: null,
            classification_status: "SYNCED",
          },
        },
        file: new File(["pdf"], "nda.pdf", { type: "application/pdf" }),
        docCategoryHint: "NDA",
        targetModel: "nda",
        targetId: "nda-1",
        autoApplySignedAt: true,
        reviewContext: { source: "buyer-nda", buyerCandidateId: "buyer-1" },
      });
    });

    expect(maApi.post).toHaveBeenCalledWith(
      "/transactions/txn-1/extractions",
      expect.objectContaining({
        vdr_document_id: "vdr-1",
        doc_category_hint: "NDA",
        target_model: "nda",
        target_id: "nda-1",
        auto_apply_signed_at: true,
      }),
    );

    await act(async () => {
      await vi.runOnlyPendingTimersAsync();
      await Promise.resolve();
      await Promise.resolve();
    });

    expect(maApi.get).toHaveBeenCalledWith(
      "/transactions/txn-1/extractions/ext-nda-1",
    );

    expect(invalidateQueries).toHaveBeenCalledWith({
      queryKey: ["ma", "transactions", "txn-1", "ndas"],
    });
    expect(invalidateQueries).toHaveBeenCalledWith({
      queryKey: ["ma", "transactions", "txn-1", "buyers"],
    });
    expect(invalidateQueries).toHaveBeenCalledWith({
      queryKey: ["ma", "transactions", "txn-1", "short-list", "overview"],
    });
    expect(invalidateQueries).toHaveBeenCalledWith({
      queryKey: ["ma", "transactions", "txn-1", "workspace-summary"],
    });
    expect(invalidateQueries).toHaveBeenCalledWith({
      queryKey: ["ma", "transactions", "txn-1", "buyers", "summary"],
    });
  });

  it("shows a warning instead of a raw OCR 500 during NDA follow-up", async () => {
    vi.spyOn(maApi, "post").mockRejectedValueOnce({
      response: { status: 500 },
    });

    const { result } = renderHook(() => useAttachmentExtractionFlow("txn-1"));

    await act(async () => {
      await result.current.startExtractionFromUpload(
        {
          attachment: {
            id: "att-1",
            transaction_id: "txn-1",
            entity_type: "NDA",
            entity_id: null,
            file_name: "nda.pdf",
            file_size_bytes: 128,
            mime_type: "application/pdf",
            description: null,
            uploaded_by_email: "test@example.com",
            created_at: "2026-03-31T00:00:00Z",
            updated_at: "2026-03-31T00:00:00Z",
            vdr_sync: {
              vdr_document_id: "vdr-1",
              folder_name: "NDA",
              category: null,
              classification_status: "SYNCED",
            },
          },
          file: new File(["pdf"], "nda.pdf", { type: "application/pdf" }),
          docCategoryHint: "NDA",
          reviewContext: { source: "buyer-nda", buyerCandidateId: "buyer-1" },
        },
        {
          successToast: null,
          failureToast: "파일은 업로드되었지만 OCR 시작에는 실패했습니다.",
          failureToastVariant: "warning",
        },
      );
    });

    expect(toast.warning).toHaveBeenCalledWith(
      "파일은 업로드되었지만 OCR 시작에는 실패했습니다. (HTTP 500)",
    );
    expect(toast.error).not.toHaveBeenCalled();
    expect(result.current.activeReview).toBeNull();
  });
});
