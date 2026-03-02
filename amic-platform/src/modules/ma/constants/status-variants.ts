import type { RFIStatus } from "../types/rfi";
import type { NegotiationIssueStatus } from "../types/negotiation_issue";
import type { MeetingStatus, ActionItemStatus } from "../types/meeting_log";

import type { BadgeVariant } from "@/components/ui";

export const TRANSACTION_STATUS_VARIANT: Record<string, BadgeVariant> = {
  DRAFT: "neutral",
  ACTIVE: "success",
  ON_HOLD: "warning",
  COMPLETED: "info",
  TERMINATED: "error",
  BID_SUBMITTED: "info",
  BID_NOT_SUBMITTED: "warning",
  BID_DROPPED: "error",
};

export const RFI_STATUS_VARIANT: Record<RFIStatus, BadgeVariant> = {
  DRAFT: "neutral",
  SENT: "info",
  PARTIALLY_RESPONDED: "warning",
  FULLY_RESPONDED: "success",
  CLOSED: "neutral",
  CANCELLED: "error",
};

export const NEGOTIATION_ISSUE_STATUS_VARIANT: Record<
  NegotiationIssueStatus,
  BadgeVariant
> = {
  OPEN: "neutral",
  IN_PROGRESS: "warning",
  AGREED: "success",
  DEFERRED: "info",
  DEADLOCKED: "error",
};

export const MEETING_STATUS_VARIANT: Record<MeetingStatus, BadgeVariant> = {
  SCHEDULED: "warning",
  COMPLETED: "success",
  CANCELLED: "error",
  POSTPONED: "neutral",
};

export const ACTION_ITEM_STATUS_VARIANT: Record<
  ActionItemStatus,
  BadgeVariant
> = {
  PENDING: "neutral",
  IN_PROGRESS: "warning",
  COMPLETED: "success",
  CANCELLED: "error",
};
