import { Badge, type BadgeVariant } from "@/components/ui";
import type { DocumentStatus } from "@/modules/im/types/document";

const STATUS_LABEL: Record<DocumentStatus, string> = {
  PENDING: "Pending",
  COLLECTING: "Collecting",
  ANALYZING: "Analyzing",
  GENERATING: "Generating",
  RENDERING: "Rendering",
  COMPLETED: "Completed",
  FAILED: "Failed",
};

const STATUS_VARIANT: Record<DocumentStatus, BadgeVariant> = {
  PENDING: "neutral",
  COLLECTING: "info",
  ANALYZING: "info",
  GENERATING: "warning",
  RENDERING: "warning",
  COMPLETED: "success",
  FAILED: "error",
};

interface DocumentStatusBadgeProps {
  status: DocumentStatus;
  className?: string;
}

export function DocumentStatusBadge({
  status,
  className,
}: DocumentStatusBadgeProps) {
  return (
    <Badge variant={STATUS_VARIANT[status]} className={className}>
      {STATUS_LABEL[status]}
    </Badge>
  );
}
