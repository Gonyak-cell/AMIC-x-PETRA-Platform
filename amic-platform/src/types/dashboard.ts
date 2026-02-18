import type { LucideIcon } from "lucide-react";

export interface PortalKpis {
  activeDeals: number;
  watchlistAlerts: number;
  imInProgress: number;
  pendingIssues: number;
  activeMaDeals: number;
}

export interface PortalKpiErrors {
  fdd: boolean;
  kiis: boolean;
  im: boolean;
  ma: boolean;
}

export interface QuickAction {
  label: string;
  to: string;
  icon: LucideIcon;
  description: string;
}

export interface ModuleHealth {
  module: "fdd" | "kiis" | "im" | "ma";
  label: string;
  healthy: boolean;
}
