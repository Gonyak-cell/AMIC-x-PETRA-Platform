// 녹음 변환 — Clova STT + LLM 자동 회의록

import type { MeetingPhase, BuyerReaction, ConditionMatchLevel } from "./meeting_log";

export type TranscriptionJobStatus =
  | "PENDING"
  | "TRANSCRIBING"
  | "ANALYZING"
  | "COMPLETED"
  | "APPROVED"
  | "FAILED";

export interface TranscriptionJob {
  id: string;
  transaction_id: string;
  title: string;
  meeting_date: string;
  meeting_phase: MeetingPhase;
  buyer_id: string | null;
  status: TranscriptionJobStatus;
  transcript: string | null;
  minutes_json: MeetingMinutesResult | null;
  meeting_log_id: string | null;
  stt_cost_krw: number;
  llm_cost_usd: number;
  error_message: string | null;
  created_at: string;
  updated_at: string;
}

export interface MeetingMinutesResult {
  minutes: string;
  summary: string;
  key_issues: { title: string; description: string; priority: string }[];
  action_items: ActionItemDraft[];
  condition_assessment: {
    match_level: ConditionMatchLevel;
    notes: string;
  } | null;
  buyer_reaction: BuyerReaction | null;
}

export interface ActionItemDraft {
  title: string;
  description: string | null;
  assignee_name: string | null;
  assignee_email: string | null;
  due_date: string | null;
  priority: string;
}

export interface TranscriptionStartPayload {
  audio: File;
  title: string;
  meeting_date: string;
  meeting_phase: MeetingPhase;
  buyer_id?: string;
  attendees_json: string; // JSON 직렬화된 참석자 배열
}

export interface TranscriptionApprovalPayload {
  minutes: string;
  summary?: string;
  action_items?: ActionItemDraft[];
  condition_match?: string;
  condition_notes?: string;
  buyer_reaction?: string;
}
