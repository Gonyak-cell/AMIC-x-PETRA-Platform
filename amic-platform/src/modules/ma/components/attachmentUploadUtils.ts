import type { RefObject } from "react";
import { toast } from "sonner";

import {
  ATTACHMENT_CONSTRAINTS,
  type Attachment,
  type AttachmentEntityType,
} from "@/modules/ma/types/attachment";
import { formatFileSize } from "@/modules/ma/utils/format";

interface UploadAttachmentMutation {
  mutateAsync: (args: {
    file: File;
    entityType: AttachmentEntityType;
    entityId?: string;
  }) => Promise<Attachment>;
}

export function validateAttachmentFile(file: File): string | null {
  if (file.size > ATTACHMENT_CONSTRAINTS.MAX_FILE_SIZE) {
    return `파일 크기(${formatFileSize(file.size)})가 최대 허용치(${ATTACHMENT_CONSTRAINTS.MAX_FILE_SIZE_LABEL})를 초과했습니다.`;
  }

  const ext = `.${file.name.split(".").pop()?.toLowerCase() ?? ""}`;
  if (!ATTACHMENT_CONSTRAINTS.ALLOWED_EXTENSIONS.has(ext)) {
    return `허용되지 않는 파일 형식입니다: ${ext}`;
  }

  return null;
}

export function openAttachmentFilePicker(
  input:
    | HTMLInputElement
    | RefObject<HTMLInputElement | null>
    | null
    | undefined,
) {
  const element =
    input && "current" in input ? input.current : (input ?? null);
  if (!element) {
    return;
  }

  const picker = element as HTMLInputElement & {
    showPicker?: () => void;
  };
  if (typeof picker.showPicker === "function") {
    try {
      picker.showPicker();
      return;
    } catch {
      // Some browsers reject showPicker() for hidden inputs or modal/top-layer contexts.
    }
  }

  element.click();
}

export async function uploadAttachmentFiles({
  files,
  entityType,
  entityId,
  uploadMutation,
  onUploaded,
}: {
  files: File[];
  entityType: AttachmentEntityType;
  entityId?: string;
  uploadMutation: UploadAttachmentMutation;
  onUploaded?: (attachment: Attachment, file: File) => Promise<void> | void;
}) {
  for (const file of files) {
    const error = validateAttachmentFile(file);
    if (error) {
      toast.error(error);
      continue;
    }

    try {
      const attachment = await uploadMutation.mutateAsync({
        file,
        entityType,
        entityId,
      });
      await onUploaded?.(attachment, file);
    } catch {
      // Upload/import hooks already surface error toasts.
    }
  }
}
