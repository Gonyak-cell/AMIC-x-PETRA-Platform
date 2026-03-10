import { useMemo, useState } from "react";
import { PanelLeftClose, PanelLeftOpen, User } from "lucide-react";
import { EmptyState } from "@/components/ui";
import type { BuyerCandidate } from "@/modules/ma/types/buyer";
import type { BuyerStageSummary } from "@/modules/ma/types/marketing_log";
import type { ShortListViewMode } from "./ShortListViewToggle";
import { isShortListed, buildStageMap } from "@/modules/ma/constants";
import ShortListMasterList from "./ShortListMasterList";
import ShortListSummaryBar from "./ShortListSummaryBar";
import ShortListViewToggle from "./ShortListViewToggle";
import MarketingGridView from "./MarketingGridView";
import MarketingKanbanView from "./MarketingKanbanView";
import MarketingTimelineView from "./MarketingTimelineView";
import BuyerDetailPanel from "./BuyerDetailPanel";

export type KpiFilter =
  | "all"
  | "active"
  | "drop"
  | "nda"
  | "target_meeting"
  | "tier1";

interface ShortListOverviewProps {
  txnId: string;
  buyers: BuyerCandidate[];
  overviewData: BuyerStageSummary[];
  canWrite: boolean;
}

export default function ShortListOverview({
  txnId,
  buyers,
  overviewData,
  canWrite,
}: ShortListOverviewProps) {
  const [viewMode, setViewMode] = useState<ShortListViewMode>("grid");
  const [selectedBuyerId, setSelectedBuyerId] = useState<string | null>(null);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [activeFilter, setActiveFilter] = useState<KpiFilter>("all");

  const shortListBuyers = useMemo(() => buyers.filter(isShortListed), [buyers]);

  const filteredBuyers = useMemo(() => {
    if (activeFilter === "all") return shortListBuyers;
    if (activeFilter === "active")
      return shortListBuyers.filter((b) => b.status !== "BID_DROPPED");
    if (activeFilter === "drop")
      return shortListBuyers.filter((b) => b.status === "BID_DROPPED");
    if (activeFilter === "tier1")
      return shortListBuyers.filter((b) => b.tier === "TIER_1");
    if (activeFilter === "nda") {
      const ndaIds = new Set(
        overviewData.filter((s) => s.stages.NDA_SIGNED).map((s) => s.buyer_id),
      );
      return shortListBuyers.filter((b) => ndaIds.has(b.id));
    }
    if (activeFilter === "target_meeting") {
      const mtgIds = new Set(
        overviewData
          .filter((s) => s.stages.TARGET_MEETING)
          .map((s) => s.buyer_id),
      );
      return shortListBuyers.filter((b) => mtgIds.has(b.id));
    }
    return shortListBuyers;
  }, [shortListBuyers, overviewData, activeFilter]);

  const selectedBuyer = useMemo(
    () => shortListBuyers.find((b) => b.id === selectedBuyerId) ?? null,
    [shortListBuyers, selectedBuyerId],
  );

  const summaryMap = useMemo(
    () => new Map(overviewData.map((s) => [s.buyer_id, s])),
    [overviewData],
  );

  const stageMap = useMemo(() => buildStageMap(overviewData), [overviewData]);

  const viewProps = useMemo(() => ({
    buyers: filteredBuyers,
    stageMap,
    onSelectBuyer: setSelectedBuyerId,
    canWrite,
    txnId,
  }), [filteredBuyers, stageMap, canWrite, txnId]);

  if (!shortListBuyers.length) {
    return (
      <EmptyState
        icon={User}
        title="Short List 후보 없음"
        description="Long List에서 체크박스를 선택하면 여기에 표시됩니다."
      />
    );
  }

  return (
    <div className="flex gap-4">
      {/* Left sidebar — Master List */}
      <div
        className={
          sidebarOpen
            ? "w-64 flex-shrink-0 border-r border-gray-border pr-4 transition-all duration-200 visible"
            : "w-0 overflow-hidden border-r-0 pr-0 transition-all duration-200 invisible"
        }
      >
        <ShortListMasterList
          buyers={shortListBuyers}
          stageMap={stageMap}
          selectedBuyerId={selectedBuyerId}
          onSelectBuyer={setSelectedBuyerId}
          totalBuyerCount={buyers.length}
        />
      </div>

      {/* Main content */}
      <div className="flex-1 min-w-0 space-y-4">
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => setSidebarOpen(!sidebarOpen)}
            className="p-1.5 rounded-lg text-gray-500 hover:text-text-dark hover:bg-gray-100 transition-colors"
            aria-expanded={sidebarOpen}
            aria-label="사이드바 토글"
            data-testid="sidebar-toggle"
          >
            {sidebarOpen ? (
              <PanelLeftClose className="h-5 w-5" />
            ) : (
              <PanelLeftOpen className="h-5 w-5" />
            )}
          </button>
          <h2 className="text-lg font-semibold text-text-dark">
            마케팅 활동 추적
          </h2>
        </div>

        {/* KPI Summary Bar */}
        <ShortListSummaryBar
          buyers={shortListBuyers}
          overviewData={overviewData}
          stageMap={stageMap}
          activeFilter={activeFilter}
          onFilterChange={setActiveFilter}
        />

        {/* View Toggle */}
        <div className="flex items-center justify-between">
          {activeFilter !== "all" && (
            <button
              type="button"
              onClick={() => setActiveFilter("all")}
              className="text-xs text-accent hover:text-accent-hover transition-colors"
            >
              필터 초기화
            </button>
          )}
          <div className="ml-auto">
            <ShortListViewToggle
              viewMode={viewMode}
              onViewModeChange={setViewMode}
            />
          </div>
        </div>

        {/* View Content */}
        <div key={viewMode} className="view-fade-in" data-testid="view-content">
          {viewMode === "grid" && <MarketingGridView {...viewProps} />}
          {viewMode === "kanban" && <MarketingKanbanView {...viewProps} />}
          {viewMode === "timeline" && <MarketingTimelineView {...viewProps} />}
        </div>
      </div>

      {/* Right slide panel — Buyer Detail */}
      <BuyerDetailPanel
        txnId={txnId}
        buyer={selectedBuyer}
        stageSummary={summaryMap.get(selectedBuyerId ?? "")}
        onClose={() => setSelectedBuyerId(null)}
        canWrite={canWrite}
      />
    </div>
  );
}
