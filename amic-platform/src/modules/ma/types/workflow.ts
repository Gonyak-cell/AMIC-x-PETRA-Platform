import type { TransactionPhase, TransactionStatus } from "./transaction";

export interface PhaseConfig {
  phase: TransactionPhase;
  label: string;
  description: string;
  icon: string;
  order: number;
}

export type PrerequisiteLevel = "REQUIRED" | "RECOMMENDED";

export interface PhasePrerequisite {
  field: string;
  label: string;
  satisfied: boolean;
  level: PrerequisiteLevel;
}

export interface PhaseCompletionStatus {
  current_phase: TransactionPhase;
  prerequisites: PhasePrerequisite[];
  all_met: boolean;
  required_met: boolean;
  has_warnings: boolean;
  can_advance: boolean;
  next_phase: TransactionPhase | null;
  previous_phase: TransactionPhase | null;
}

export interface WorkflowTransition {
  from_phase: TransactionPhase;
  to_phase: TransactionPhase;
  transitioned_at: string;
  transitioned_by: string;
  notes: string | null;
}

export interface StatusChange {
  from_status: TransactionStatus;
  to_status: TransactionStatus;
  reason: string | null;
}
