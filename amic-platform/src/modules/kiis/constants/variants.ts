import type { BadgeVariant } from "@/components/ui";

export const SEVERITY_VARIANT: Record<string, BadgeVariant> = {
  critical: "error",
  warning: "warning",
  caution: "info",
};

export const MOVEMENT_VARIANT: Record<string, BadgeVariant> = {
  transfer: "info",
  resignation: "warning",
  appointment: "success",
};

export const LISTING_STATUS_VARIANT: Record<string, BadgeVariant> = {
  상장: "success",
  비상장: "neutral",
  폐지: "warning",
};
