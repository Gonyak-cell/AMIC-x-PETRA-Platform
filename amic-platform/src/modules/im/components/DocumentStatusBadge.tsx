import { Badge, type BadgeVariant } from "@/components/ui";
import type {
  DocumentStatus,
  QualityStatus,
} from "@/modules/im/types/document";
import {
  IM_QUALITY_STATUS_LABELS,
  IM_QUALITY_STATUS_VARIANT,
} from "@/modules/im/types/document";

const STATUS_LABEL: Record<DocumentStatus, string> = {
  AWAITING_UPLOAD: "업로드 대기",
  PENDING: "Pending",
  COLLECTING: "Collecting",
  ANALYZING: "Analyzing",
  GENERATING: "Generating",
  RENDERING: "Rendering",
  COMPLETED: "Completed",
  FAILED: "Failed",
};

const STATUS_VARIANT: Record<DocumentStatus, BadgeVariant> = {
  AWAITING_UPLOAD: "warning",
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
  qualityStatus?: QualityStatus | null;
  className?: string;
}

export function DocumentStatusBadge({
  status,
  qualityStatus,
  className,
}: DocumentStatusBadgeProps) {
  return (
    <span className={`inline-flex items-center gap-1.5 ${className ?? ""}`}>
      <Badge variant={STATUS_VARIANT[status] ?? "neutral"}>
        {STATUS_LABEL[status] ?? status}
      </Badge>
      {qualityStatus && (
        <Badge
          variant={
            (IM_QUALITY_STATUS_VARIANT[qualityStatus] as BadgeVariant) ??
            "neutral"
          }
        >
          {IM_QUALITY_STATUS_LABELS[qualityStatus] ?? qualityStatus}
        </Badge>
      )}
    </span>
  );
}
