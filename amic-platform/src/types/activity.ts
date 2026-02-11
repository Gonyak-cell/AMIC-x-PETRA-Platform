export type ActivityModule = "fdd" | "kiis" | "im" | "portal";

export type ActivityAction =
  | "create"
  | "update"
  | "delete"
  | "view"
  | "approve"
  | "reject"
  | "export"
  | "login"
  | "logout"
  | "lock"
  | "purge";

export interface ActivityLogItem {
  id: string;
  user_id: string;
  user_name: string;
  module: ActivityModule;
  action: ActivityAction;
  entity_type: string;
  entity_id: string | null;
  entity_name: string | null;
  description: string;
  metadata: Record<string, unknown> | null;
  created_at: string;
  ip_address: string | null;
}

export interface ActivityLogFilter {
  user_id?: string;
  module?: ActivityModule;
  action?: ActivityAction;
  date_from?: string;
  date_to?: string;
  page?: number;
  size?: number;
}

export interface PaginatedActivityLog {
  items: ActivityLogItem[];
  total: number;
  page: number;
  size: number;
}

/** 백엔드 AuditLogRead 미러 */
export interface RawAuditLogItem {
  id: string;
  deal_id: string | null;
  entity_type: string;
  entity_id: string;
  action: string;
  actor: string;
  old_value: Record<string, unknown> | null;
  new_value: Record<string, unknown> | null;
  user_id: string | null;
  user_email: string | null;
  user_role: string | null;
  ip_address: string | null;
  before_state: Record<string, unknown> | null;
  after_state: Record<string, unknown> | null;
  changed_fields: string[] | null;
  session_id: string | null;
  request_id: string | null;
  expires_at: string | null;
  created_at: string;
}

/** 백엔드 AuditLogListResponse 미러 */
export interface RawAuditLogListResponse {
  total: number;
  items: RawAuditLogItem[];
  limit: number;
  offset: number;
}
