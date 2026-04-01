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
    attachment.processing_status === "SYNCED" &&
    isPdfUpload(attachment, file) &&
    Boolean(attachment.vdr_sync?.vdr_document_id)
  );
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
      }: StartExtractionFromUploadParams,
      options: StartExtractionToastOptions = {},
    ) => {
      if (!isPdfUpload(attachment, file)) {
        toast.info("PDF 업로드만 OCR 자동 등록을 지원합니다.");
        return null;
      }

      const vdrDocumentId = attachment.vdr_sync?.vdr_document_id;
      if (!vdrDocumentId) {
        toast.info(
          "VDR 동기화가 완료된 파일만 OCR 자동 등록을 시작할 수 있습니다.",
        );
        return null;
      }

      try {
        const { data: extraction } = await maApi.post<DocumentExtraction>(
          `/transactions/${txnId}/extractions`,
          {
            vdr_document_id: vdrDocumentId,
            doc_category_hint: docCategoryHint,
          },
        );
        await queryClient.invalidateQueries({
          queryKey: ["ma", "transactions", txnId, "extractions"],
        });
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
