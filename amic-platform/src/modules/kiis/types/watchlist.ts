export type AlertType =
  | "sanction"
  | "news"
  | "disclosure"
  | "reputation"
  | "new_disclosure"
  | "reputation_change";

/** 워치리스트 아이템 (GET /watchlist → items[]) */
export interface WatchlistItem {
  id: number;
  user_id: number;
  company_id: number;
  company_name: string | null;
  alert_types: string[];
  is_active: boolean;
  created_at: string;
}

/** 워치리스트 목록 래퍼 응답 */
export interface WatchlistListResponse {
  total: number;
  items: WatchlistItem[];
}

/** 알림 이력 아이템 (GET /alerts → items[]) */
export interface Alert {
  id: number;
  alert_type: string;
  title: string;
  message: string | null;
  is_read: boolean;
  company_id: number;
  company_name: string | null;
  reference_id: number | null;
  reference_type: string | null;
  created_at: string;
}

/** 알림 목록 래퍼 응답 */
export interface AlertListResponse {
  total: number;
  page: number;
  size: number;
  items: Alert[];
}

/** 워치리스트 추가 요청 */
export interface WatchlistAddRequest {
  company_id: number;
  alert_types?: string[];
}

/** 미읽음 알림 수 응답 */
export interface UnreadCount {
  count: number;
}
