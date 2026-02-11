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
  | "logout";

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
