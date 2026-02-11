export type NotificationModule = "fdd" | "kiis" | "im" | "portal";

export interface NotificationItem {
  id: string;
  module: NotificationModule;
  type: string;
  title: string;
  message: string;
  is_read: boolean;
  created_at: string;
  link: string | null;
}
