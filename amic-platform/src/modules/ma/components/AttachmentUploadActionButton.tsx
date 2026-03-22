import { useCallback, useRef } from "react";
import { Upload } from "lucide-react";

import { Button, type ButtonProps } from "@/components/ui/Button";
import { useUploadAttachment } from "@/modules/ma/hooks/useAttachments";
import type {
  Attachment,
  AttachmentEntityType,
} from "@/modules/ma/types/attachment";
import { ATTACHMENT_CONSTRAINTS } from "@/modules/ma/types/attachment";

import {
  openAttachmentFilePicker,
  uploadAttachmentFiles,
} from "./attachmentUploadUtils";

interface AttachmentUploadActionButtonProps
  extends Omit<ButtonProps, "icon" | "loading" | "onClick"> {
  txnId: string;
  entityType: AttachmentEntityType;
  entityId?: string;
  label?: string;
  onUploaded?: (attachment: Attachment, file: File) => Promise<void> | void;
}

export default function AttachmentUploadActionButton({
  txnId,
  entityType,
  entityId,
  label = "파일 업로드",
  onUploaded,
  disabled,
  variant = "ghost",
  size = "sm",
  className,
  ...props
}: AttachmentUploadActionButtonProps) {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const uploadMutation = useUploadAttachment(txnId);

  const handlePick = useCallback(() => {
    openAttachmentFilePicker(fileInputRef);
  }, []);

  const handleFileSelect = useCallback(
    async (event: React.ChangeEvent<HTMLInputElement>) => {
      await uploadAttachmentFiles({
        files: Array.from(event.target.files ?? []),
        entityType,
        entityId,
        uploadMutation,
        onUploaded,
      });
      event.target.value = "";
    },
    [entityId, entityType, onUploaded, uploadMutation],
  );

  return (
    <>
      <input
        ref={fileInputRef}
        type="file"
        className="sr-only"
        multiple
        tabIndex={-1}
        accept={ATTACHMENT_CONSTRAINTS.ACCEPT_EXTENSIONS}
        onChange={handleFileSelect}
      />
      <Button
        type="button"
        icon={Upload}
        variant={variant}
        size={size}
        className={className}
        disabled={disabled || uploadMutation.isPending}
        loading={uploadMutation.isPending}
        onClick={handlePick}
        {...props}
      >
        {label}
      </Button>
    </>
  );
}
