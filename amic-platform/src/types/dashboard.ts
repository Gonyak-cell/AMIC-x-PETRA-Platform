import type { LucideIcon } from "lucide-react";

export interface PortalKpis {
  watchlistAlerts: number;
  activeMaDeals: number;
}

export interface PortalKpiErrors {
  kiis: boolean;
  ma: boolean;
}

export interface QuickAction {
  label: string;
  to: string;
  icon: LucideIcon;
  description: string;
}

export interface ModuleHealth {
  module: "fdd" | "kiis" | "ma" | "im";
  label: string;
  healthy: boolean;
}

export interface AggregatedModuleHealth {
  id: "ma" | "docs" | "kiis";
  label: string;
  services: { name: string; healthy: boolean }[];
  overallHealthy: boolean;
  healthySummary: string;
}
