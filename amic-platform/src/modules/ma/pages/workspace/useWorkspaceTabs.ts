import { useMemo } from "react";

import type { TabItem } from "@/components/ui";
import {
  PHASE_TAB_MAP,
  PHASE_VISIBLE_TABS,
  RAIL_TOOL_IDS,
} from "@/modules/ma/constants";
import type { TransactionPhase } from "@/modules/ma/types/transaction";
import type { WorkspaceSummary } from "@/modules/ma/types/workspace";

export const VALID_TABS = [
  "engagement",
  "buyers",
  "marketing-materials",
  "models",
  "ndas",
  "vdr",
  "bids",
  "dd-checklist",
  "contracts",
  "closing",
  "marketing-logs",
  "negotiation-logs",
  "rfi",
  // Keep timeline route valid for deep links, but do not show it in the main tab bar.
  "timeline",
] as const;

interface UseWorkspaceTabsOptions {
  summary: WorkspaceSummary | undefined;
  txnPhase: string | undefined;
  viewedPhase: TransactionPhase | null;
  activeTab: string;
  baseTab?: string;
}

export function useWorkspaceTabs({
  summary,
  txnPhase,
  viewedPhase,
  activeTab,
  baseTab,
}: UseWorkspaceTabsOptions) {
  const allTabs: TabItem[] = useMemo(
    () => [
      { id: "overview", label: "Overview" },
      { id: "engagement", label: "수임", badge: summary?.engagement_count },
      { id: "buyers", label: "매수자", badge: summary?.buyer_count },
      {
        id: "marketing-materials",
        label: "마케팅 자료",
        badge: summary?.marketing_material_count,
      },
      {
        id: "models",
        label: "재무모델",
        badge: summary?.financial_model_count,
      },
      { id: "ndas", label: "NDA", badge: summary?.nda_count },
      { id: "bids", label: "입찰", badge: summary?.bid_count },
      {
        id: "dd-checklist",
        label: "DD/Checklist",
        badge: summary?.dd_item_count,
      },
      { id: "contracts", label: "계약/SPA", badge: summary?.contract_count },
      { id: "closing", label: "Closing", badge: summary?.closing_item_count },
      { id: "marketing-logs", label: "마케팅 로그" },
      { id: "negotiation-logs", label: "협상 로그" },
      { id: "rfi", label: "RFI" },
    ],
    [summary],
  );

  const effectivePhase = (viewedPhase ?? txnPhase) as
    | TransactionPhase
    | undefined;

  const visibleTabIds = effectivePhase
    ? PHASE_VISIBLE_TABS[effectivePhase]
    : allTabs.map((tab) => tab.id);

  const tabs = allTabs.filter((tab) => visibleTabIds.includes(tab.id));
  const isVdrRoute = activeTab === "vdr";
  const fallbackPrimaryTab =
    baseTab && visibleTabIds.includes(baseTab)
      ? baseTab
      : effectivePhase
        ? (PHASE_TAB_MAP[effectivePhase] ?? "overview")
        : "overview";

  const isRailTool = (RAIL_TOOL_IDS as readonly string[]).includes(activeTab);
  const safeActiveTab = isRailTool
    ? fallbackPrimaryTab
    : isVdrRoute
      ? "vdr"
      : activeTab === "overview" || visibleTabIds.includes(activeTab)
        ? activeTab
        : viewedPhase
          ? (PHASE_TAB_MAP[viewedPhase] ?? "overview")
          : "overview";

  const tabBarActiveTab =
    isRailTool || isVdrRoute ? fallbackPrimaryTab : safeActiveTab;

  return { tabs, safeActiveTab, tabBarActiveTab, visibleTabIds, isRailTool };
}
