import type { TransactionPhase, TransactionStatus } from "./transaction";

export interface PhaseConfig {
  phase: TransactionPhase;
  label: string;
  description: string;
  icon: string;
  order: number;
}

export interface PhasePrerequisite {
  field: string;
  label: string;
  satisfied: boolean;
  current_value?: string | null;
  target_value?: string | null;
  requires_acknowledgement?: boolean;
}

export interface PhaseCompletionStatus {
  current_phase: TransactionPhase;
  prerequisites: PhasePrerequisite[];
  all_met: boolean;
  can_advance: boolean;
  blocking_reasons: string[];
  next_phase: TransactionPhase | null;
  previous_phase: TransactionPhase | null;
  gate_summary?: string | null;
  pending_acknowledgements: string[];
  requires_user_acknowledgement: boolean;
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
