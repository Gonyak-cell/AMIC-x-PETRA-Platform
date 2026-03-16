import type { LucideIcon } from "lucide-react";

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
