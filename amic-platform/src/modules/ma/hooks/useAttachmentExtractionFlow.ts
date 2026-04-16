import { useCallback, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

import { extractApiError } from "@/api/errors";
import { maApi } from "@/api/maClient";
import type { Attachment } from "@/modules/ma/types/attachment";
import type {
  DocExtractionCategory,
  DocumentExtraction,
  ExtractionReviewContext,
} from "@/modules/ma/types/document_extraction";

interface StartExtractionFromUploadParams {
  attachment: Attachment;
  file: File;
  docCategoryHint: DocExtractionCategory;
  reviewContext: ExtractionReviewContext;
  targetModel?: "nda" | "marketing_material";
  targetId?: string;
  autoApplySignedAt?: boolean;
}

interface StartExtractionToastOptions {
  successToast?: string | null;
  failureToast?: string | null;
  failureToastVariant?: "error" | "warning" | "info";
}

export interface ActiveExtractionReview {
  extraction: DocumentExtraction;
  context: ExtractionReviewContext;
}

function isPdfUpload(attachment: Attachment, file: File) {
  return (
    attachment.mime_type === "application/pdf" ||
    file.type === "application/pdf" ||
    file.name.toLowerCase().endsWith(".pdf")
  );
}

export function canStartExtractionFromUpload(
  attachment: Attachment,
  file: File,
) {
  return (
    isPdfUpload(attachment, file) &&
    (attachment.processing_status === "SYNCED" ||
      attachment.processing_status === "PENDING" ||
      attachment.processing_status === "RUNNING")
  );
}

const SYNC_POLLABLE_ATTACHMENT_STATUSES = new Set(["PENDING", "RUNNING"]);
const ATTACHMENT_SYNC_POLL_INTERVAL_MS = 1500;
const ATTACHMENT_SYNC_TIMEOUT_MS = 2 * 60 * 1000;

const POLLABLE_EXTRACTION_STATUSES = new Set([
  "PENDING",
  "CLASSIFYING",
  "EXTRACTING",
]);

function delay(ms: number) {
  return new Promise((resolve) => window.setTimeout(resolve, ms));
}

async function waitForAttachmentSync(
  txnId: string,
  initialAttachment: Attachment,
): Promise<Attachment> {
  let latest = initialAttachment;
  if (!latest.processing_status && latest.vdr_sync?.vdr_document_id) {
    return latest;
  }
  const startedAt = Date.now();

  while (SYNC_POLLABLE_ATTACHMENT_STATUSES.has(latest.processing_status)) {
    if (Date.now() - startedAt > ATTACHMENT_SYNC_TIMEOUT_MS) {
      throw new Error("Attachment VDR sync timed out. Please retry processing.");
    }
    await delay(ATTACHMENT_SYNC_POLL_INTERVAL_MS);
    const { data } = await maApi.get<Attachment>(
      `/transactions/${txnId}/attachments/${initialAttachment.id}`,
    );
    latest = data;
  }

  if (latest.processing_status !== "SYNCED") {
    throw new Error(
      latest.processing_error ||
        `Attachment VDR sync ended with ${latest.processing_status}.`,
    );
  }
  if (!latest.vdr_sync?.vdr_document_id) {
    throw new Error("Attachment synced, but no VDR document id was returned.");
  }
  return latest;
}

export function useAttachmentExtractionFlow(txnId: string) {
  const queryClient = useQueryClient();
  const [activeReview, setActiveReview] = useState<ActiveExtractionReview | null>(
    null,
  );

  const closeReview = useCallback(() => {
    setActiveReview(null);
  }, []);

  const startExtractionFromUpload = useCallback(
    async (
      {
        attachment,
        file,
        docCategoryHint,
        reviewContext,
        targetModel,
        targetId,
        autoApplySignedAt,
      }: StartExtractionFromUploadParams,
      options: StartExtractionToastOptions = {},
    ) => {
      if (!isPdfUpload(attachment, file)) {
        toast.info("PDF 업로드만 OCR 자동 등록을 지원합니다.");
        return null;
      }

      let vdrDocumentId = attachment.vdr_sync?.vdr_document_id;
      if (!vdrDocumentId && attachment.processing_status === "SYNCED") {
        toast.info(
          "VDR 동기화가 완료된 파일만 OCR 자동 등록을 시작할 수 있습니다.",
        );
        return null;
      }

      try {
        const syncedAttachment = await waitForAttachmentSync(txnId, attachment);
        vdrDocumentId = syncedAttachment.vdr_sync?.vdr_document_id;
        if (!vdrDocumentId) {
          throw new Error(
            "Attachment synced, but no VDR document id was returned.",
          );
        }
        const { data: extraction } = await maApi.post<DocumentExtraction>(
          `/transactions/${txnId}/extractions`,
          {
            vdr_document_id: vdrDocumentId,
            doc_category_hint: docCategoryHint,
            target_model: targetModel,
            target_id: targetId,
            auto_apply_signed_at: autoApplySignedAt,
          },
        );
        await queryClient.invalidateQueries({
          queryKey: ["ma", "transactions", txnId, "extractions"],
        });
        if (targetModel === "nda" && targetId && autoApplySignedAt) {
          void (async () => {
            try {
              let latest = extraction;
              while (POLLABLE_EXTRACTION_STATUSES.has(latest.status)) {
                await delay(1500);
                const { data } = await maApi.get<DocumentExtraction>(
                  `/transactions/${txnId}/extractions/${extraction.id}`,
                );
                latest = data;
              }

              if (
                latest.status === "COMPLETED" ||
                latest.status === "CONFIRMED"
              ) {
                await Promise.all([
                  queryClient.invalidateQueries({
                    queryKey: ["ma", "transactions", txnId, "extractions"],
                  }),
                  queryClient.invalidateQueries({
                    queryKey: ["ma", "transactions", txnId, "ndas"],
                  }),
                  queryClient.invalidateQueries({
                    queryKey: ["ma", "transactions", txnId, "buyers"],
                  }),
                  queryClient.invalidateQueries({
                    queryKey: [
                      "ma",
                      "transactions",
                      txnId,
                      "short-list",
                      "overview",
                    ],
                  }),
                  queryClient.invalidateQueries({
                    queryKey: ["ma", "transactions", txnId, "workspace-summary"],
                  }),
                  queryClient.invalidateQueries({
                    queryKey: ["ma", "transactions", txnId, "buyers", "summary"],
                  }),
                ]);
              }
            } catch {
              // Keep the review UX working even if follow-up polling fails.
            }
          })();
        }
        if (options.successToast !== null) {
          toast.success(options.successToast ?? "AI 분석을 시작했습니다.");
        }
        setActiveReview({ extraction, context: reviewContext });
        return extraction;
      } catch (error) {
        if (options.failureToast === null) {
          return null;
        }

        const message = extractApiError(
          error,
          options.failureToast ?? "AI 분석 생성에 실패했습니다.",
        );

        if (options.failureToastVariant === "warning") {
          toast.warning(message);
          return null;
        }

        if (options.failureToastVariant === "info") {
          toast.info(message);
          return null;
        }

        toast.error(message);
        return null;
      }
    },
    [queryClient, txnId],
  );

  return {
    activeReview,
    closeReview,
    startExtractionFromUpload,
  };
}
