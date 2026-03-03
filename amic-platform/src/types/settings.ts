export interface UserPreferences {
  defaultModule: "/" | "/ma/transactions" | "/docs" | "/kiis";
  dateFormat: "short" | "long";
}

export interface PasswordChangeRequest {
  current_password: string;
  new_password: string;
  confirm_password: string;
}

// ── Sidebar Appearance ──

export type SidebarTheme = "AMIC_FOREST" | "AMIC_DEEP" | "AMIC_GLASS";
export type SidebarLayout = "COMPACT" | "EXPANDED";

export interface SidebarAppearance {
  sidebarTheme: SidebarTheme;
  sidebarAccentColor: string; // hex e.g. "#26C260"
  sidebarLayout: SidebarLayout;
}
