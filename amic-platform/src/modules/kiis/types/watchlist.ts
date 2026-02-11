export type AlertType = "sanction" | "news" | "disclosure" | "reputation";

export interface WatchlistItem {
  id: string;
  company_id: string;
  corp_code: string;
  corp_name: string;
  alert_types: AlertType[];
  added_at: string;
}

export interface Alert {
  id: string;
  type: AlertType;
  message: string;
  company_name: string;
  created_at: string;
  is_read: boolean;
}

export interface WatchlistAddRequest {
  company_id: string;
  corp_code: string;
  alert_types: AlertType[];
}

export interface UnreadCount {
  count: number;
}
