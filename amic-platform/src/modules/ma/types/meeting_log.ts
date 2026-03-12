// 미팅 로그 타입 — 마케팅/협상 공용

import type { MarketingStage } from "./marketing_log";

export type MeetingPhase = "MARKETING" | "NEGOTIATION";
export type MeetingChannel =
  | "IN_PERSON"
  | "EMAIL"
  | "PHONE"
  | "VIDEO"
  | "HYBRID";
export type MeetingType =
  | "MEETING"
  | "MEAL"
  | "TEA_TIME"
  | "CALL"
  | "SITE_VISIT"
  | "OTHER";
export type MeetingStatus =
  | "SCHEDULED"
  | "COMPLETED"
  | "CANCELLED"
  | "POSTPONED";
export type AttendeeRole =
  | "SELLER_ADVISOR"
  | "BUYER_ADVISOR"
  | "LEGAL_COUNSEL"
  | "CLIENT_REPRESENTATIVE"
  | "COUNTERPARTY"
  | "OBSERVER"
  | "OTHER";
export type BuyerReaction =
  | "VERY_POSITIVE"
  | "POSITIVE"
  | "NEUTRAL"
  | "NEGATIVE"
  | "VERY_NEGATIVE";
export type ConditionMatchLevel =
  | "FULL_MATCH"
  | "PARTIAL_MATCH"
  | "MISMATCH"
  | "NOT_ASSESSED";
export type ActionItemStatus =
  | "PENDING"
  | "IN_PROGRESS"
  | "COMPLETED"
  | "CANCELLED";

// ── 참석자 ────────────────────────────────────────────────
export interface MeetingAttendee {
  id: string;
  meeting_id: string;
  name: string;
  email: string | null;
  organization: string | null;
  role: AttendeeRole;
  reaction: BuyerReaction | null;
  comments: string | null;
  created_at: string;
  updated_at: string;
}

export interface MeetingAttendeeCreate {
  name: string;
  email?: string;
  organization?: string;
  role?: AttendeeRole;
  reaction?: BuyerReaction;
  comments?: string;
}

export interface MeetingAttendeeUpdate {
  name?: string;
  email?: string;
  organization?: string;
  role?: AttendeeRole;
  reaction?: BuyerReaction;
  comments?: string;
}

// ── 액션아이템 ────────────────────────────────────────────
export interface MeetingActionItem {
  id: string;
  meeting_id: string;
  title: string;
  description: string | null;
  assignee_email: string | null;
  assignee_name: string | null;
  due_date: string | null;
  status: ActionItemStatus;
  priority: string | null;
  created_at: string;
  updated_at: string;
}

export interface MeetingActionItemCreate {
  title: string;
  description?: string;
  assignee_email?: string;
  assignee_name?: string;
  due_date?: string;
  status?: ActionItemStatus;
  priority?: string;
}

// ── 미팅 로그 ────────────────────────────────────────────
export interface MeetingLog {
  id: string;
  transaction_id: string;
  meeting_phase: MeetingPhase;
  title: string;
  meeting_date: string;
  meeting_time: string | null;
  location: string | null;
  channel: MeetingChannel;
  meeting_type: MeetingType | null;
  status: MeetingStatus;
  minutes: string | null;
  summary: string | null;
  provided_materials:
    | { name: string; description?: string; url?: string }[]
    | null;
  attachments: { name: string; url: string; size: number }[] | null;
  buyer_id: string | null;
  marketing_stage: MarketingStage | null;
  condition_match: ConditionMatchLevel | null;
  condition_notes: string | null;
  contract_id: string | null;
  attendee_count: number;
  created_by_email: string | null;
  created_at: string;
  updated_at: string;
}

export interface MeetingLogDetail extends MeetingLog {
  attendees: MeetingAttendee[];
  action_items: MeetingActionItem[];
}

export interface MeetingLogCreate {
  meeting_phase: MeetingPhase;
  title: string;
  meeting_date: string;
  meeting_time?: string;
  location?: string;
  channel?: MeetingChannel;
  meeting_type?: MeetingType;
  status?: MeetingStatus;
  minutes?: string;
  summary?: string;
  provided_materials?: { name: string; description?: string }[];
  attachments?: { name: string; url: string; size: number }[];
  buyer_id?: string;
  marketing_stage?: MarketingStage;
  condition_match?: ConditionMatchLevel;
  condition_notes?: string;
  contract_id?: string;
  attendees?: MeetingAttendeeCreate[];
}

export interface MeetingLogUpdate {
  title?: string;
  meeting_date?: string;
  meeting_time?: string;
  location?: string;
  channel?: MeetingChannel;
  meeting_type?: MeetingType;
  status?: MeetingStatus;
  minutes?: string;
  summary?: string;
  provided_materials?: { name: string; description?: string }[];
  buyer_id?: string;
  marketing_stage?: MarketingStage;
  condition_match?: ConditionMatchLevel;
  condition_notes?: string;
  contract_id?: string;
}

export interface MeetingLogListResponse {
  items: MeetingLog[];
  total: number;
}

export interface MeetingLogSummary {
  total: number;
  by_status: Record<string, number>;
  by_channel: Record<string, number>;
}
