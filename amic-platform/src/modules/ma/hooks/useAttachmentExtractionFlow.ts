import { useCallback, useState } from "react";
import { toast } from "sonner";

import { useCreateExtraction } from "@/modules/ma/hooks/useDocumentExtraction";
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

export function useAttachmentExtractionFlow(txnId: string) {
  const createExtraction = useCreateExtraction(txnId);
  const [activeReview, setActiveReview] = useState<ActiveExtractionReview | null>(
    null,
  );

  const closeReview = useCallback(() => {
    setActiveReview(null);
  }, []);

  const startExtractionFromUpload = useCallback(
    async ({
      attachment,
      file,
      docCategoryHint,
      reviewContext,
    }: StartExtractionFromUploadParams) => {
      if (!isPdfUpload(attachment, file)) {
        toast.info("PDF 업로드만 OCR 자동기재를 지원합니다.");
        return;
      }

      const vdrDocumentId = attachment.vdr_sync?.vdr_document_id;
      if (!vdrDocumentId) {
        toast.info("VDR 동기화가 완료된 파일만 OCR 자동기재를 실행할 수 있습니다.");
        return;
      }

      try {
        const extraction = await createExtraction.mutateAsync({
          vdrDocumentId,
          docCategoryHint,
        });
        setActiveReview({ extraction, context: reviewContext });
      } catch {
        // Mutation hook already surfaces the error.
      }
    },
    [createExtraction],
  );

  return {
    activeReview,
    closeReview,
    startExtractionFromUpload,
  };
}
