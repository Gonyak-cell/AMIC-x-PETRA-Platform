import { useMemo } from "react";
import type { TabItem } from "@/components/ui";
import {
  PHASE_TAB_MAP,
  PHASE_VISIBLE_TABS,
  RAIL_TOOL_IDS,
} from "@/modules/ma/constants";
import type { TransactionPhase } from "@/modules/ma/types/transaction";
import type { WorkspaceSummary } from "@/modules/ma/types/workspace";

// ── 상수 ───────────────────────────────────────
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
  "pmi",
  "earnout",
  "marketing-logs",
  "negotiation-logs",
  "rfi",
  // rail tools — URL 호환성 유지, primary tab bar에는 미표시
  "risks",
  "compliance",
  "notes-approvals",
  "timeline",
  "ai-quality",
];

// ── Hook ───────────────────────────────────────
interface UseWorkspaceTabsOptions {
  summary: WorkspaceSummary | undefined;
  txnPhase: string | undefined;
  viewedPhase: TransactionPhase | null;
  activeTab: string;
  /** rail tool URL 접근 시 primary content로 표시할 탭 (?baseTab= query) */
  baseTab?: string;
  isClient: boolean;
}

export function useWorkspaceTabs({
  summary,
  txnPhase,
  viewedPhase,
  activeTab,
  baseTab,
  isClient,
}: UseWorkspaceTabsOptions) {
  // primary tab bar에는 rail tools 미포함
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
      { id: "pmi", label: "PMI", badge: summary?.pmi_count },
      { id: "earnout", label: "어닝아웃", badge: summary?.earnout_count },
      { id: "marketing-logs", label: "활동 로그" },
      { id: "negotiation-logs", label: "활동 로그" },
      { id: "vdr", label: "VDR" },
      { id: "rfi", label: "RFI" },
    ],
    [summary],
  );

  const effectivePhase = (viewedPhase ?? txnPhase) as
    | TransactionPhase
    | undefined;

  const visibleTabIds = effectivePhase
    ? PHASE_VISIBLE_TABS[effectivePhase]
    : allTabs.map((t) => t.id);

  const tabs = isClient
    ? [{ id: "overview", label: "대시보드" }]
    : allTabs.filter((t) => visibleTabIds.includes(t.id));

  // rail tool URL 접근 시 baseTab 또는 phase 기본 탭을 primary content로 사용
  const isRailTool = (RAIL_TOOL_IDS as readonly string[]).includes(activeTab);
  const safeActiveTab = isRailTool
    ? baseTab && visibleTabIds.includes(baseTab)
      ? baseTab
      : effectivePhase
        ? (PHASE_TAB_MAP[effectivePhase] ?? "overview")
        : "overview"
    : activeTab === "overview" || visibleTabIds.includes(activeTab)
      ? activeTab
      : viewedPhase
        ? (PHASE_TAB_MAP[viewedPhase] ?? "overview")
        : "overview";

  return { tabs, safeActiveTab, visibleTabIds, isRailTool };
}
