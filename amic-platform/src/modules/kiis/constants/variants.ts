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
