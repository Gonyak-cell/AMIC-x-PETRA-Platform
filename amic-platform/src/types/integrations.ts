export interface EmailNotificationPreference {
  deal_updates: boolean;
  watchlist_alerts: boolean;
  im_completion: boolean;
  weekly_digest: boolean;
}

export interface WebhookConfig {
  id: string;
  url: string;
  events: string[];
  is_active: boolean;
  secret: string | null;
  created_at: string;
  last_triggered_at: string | null;
}

export interface WebhookCreate {
  url: string;
  events: string[];
  secret?: string;
}

export interface WebhookUpdate {
  url?: string;
  events?: string[];
  is_active?: boolean;
  secret?: string;
}
