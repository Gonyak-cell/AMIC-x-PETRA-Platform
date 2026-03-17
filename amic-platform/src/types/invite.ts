/** 초대(Invite) 관련 타입 정의. */

export interface InviteCreatePayload {
  email: string;
  display_name: string;
  title?: string;
  transaction_ids: string[];
  transaction_names?: string[];
}

export interface InviteCreateResult {
  user_id: string;
  email: string;
  display_name: string;
  is_new_user: boolean;
  assigned_deal_count: number;
  invite_sent: boolean;
  invite_error: string | null;
}

export interface InviteTokenInfo {
  valid: boolean;
  email: string | null;
  display_name: string | null;
  expired: boolean;
  already_used: boolean;
}

export interface InviteAcceptPayload {
  token: string;
  password: string;
}

export interface InviteAcceptResult {
  message: string;
  email: string;
}
